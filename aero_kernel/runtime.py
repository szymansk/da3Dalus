"""Executor of the kernel: worker processes, concurrency limit, cancellation (ARCHITECTURE ch. 8.10).

A :class:`SolverRuntime` is owned by whoever creates it (one ``compute()`` call or one
``CachedKernel``) and closed by them. The module keeps no state of its own, creates no pool at
import and never calls ``asyncio.run``. The per-request time budget is the engine's: it wraps
solver calls in ``asyncio.timeout``, and the ``TimeoutError`` and ``CancelledError`` raised here
leave the pool and any subprocess in a clean state.
"""

import asyncio
import concurrent.futures
import functools
import logging
import multiprocessing
import os
import pickle
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, Protocol, Self, TypeVar, cast, runtime_checkable

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.solvers.aero_model import MAX_MODELS_PER_WORKER, install_model_cache
from aero_kernel.solvers.process import ProcessRun, run_process
from pydantic import BaseModel, ConfigDict, Field, JsonValue

logger = logging.getLogger(__name__)

__all__ = [
    "RoutedRequest",
    "SolverRuntime",
    "WorkerDiagnostics",
    "WorkerFailure",
    "WorkerOutcome",
    "run_in_worker",
    "silence_worker_logging",
]

T = TypeVar("T")


class WorkerDiagnostics(BaseModel):
    """What a pool worker reports about its run; the parent logs it (ch. 8.14).

    Attributes:
        duration_s: Wall-clock time of the work in seconds.
        solver_status: The solver's own status word, if it has one.
        iterations: Iteration count, if the solver has one.
        notes: Further observations, one short English sentence each.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    duration_s: float = Field(ge=0)
    solver_status: str | None = None
    iterations: int | None = Field(default=None, ge=0)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkerOutcome(Generic[T]):  # a dataclass, not a Pydantic model: T is any picklable value
    """What a successful pool worker returns: its value and its diagnostics.

    Attributes:
        value: The result; must be picklable.
        diagnostics: The worker's report.
    """

    value: T
    diagnostics: WorkerDiagnostics


class WorkerFailure(BaseModel):
    """An expected failure a pool worker returns instead of raising (ch. 8.12).

    ``FormulaError`` does not survive a process boundary, so a worker returns this and
    :meth:`SolverRuntime.run_cpu` raises the ``FormulaError`` in the parent.

    Attributes:
        category: One of the categories a formula may raise.
        code: Catalogued error code.
        message: The cause, in natural language.
        hint: What to do.
        detail: Structured data about the failure.
        parameter: Name of the formula parameter at fault, if any.
        diagnostics: The worker's report.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: ErrorCategory
    code: str
    message: str
    hint: str
    detail: dict[str, JsonValue] = Field(default_factory=dict)
    parameter: str | None = None
    diagnostics: WorkerDiagnostics

    def to_formula_error(self) -> FormulaError:
        """Build the ``FormulaError`` the failure stands for."""
        return FormulaError(
            self.category,
            self.code,
            self.message,
            self.hint,
            self.detail,
            self.parameter,
        )


def run_in_worker(
    fn: Callable[..., WorkerOutcome[T] | WorkerFailure], args: tuple[object, ...]
) -> WorkerOutcome[T] | WorkerFailure:
    """Run ``fn`` in the worker so that no exception can break the pool or its siblings.

    ``FormulaError`` cannot be unpickled (its constructor validates), and an exception that fails
    to unpickle kills the pool's result channel. So ``FormulaError`` becomes a
    :class:`WorkerFailure`, an exception that does not survive a pickle round trip becomes a
    ``RuntimeError`` with its type and text, and any other exception is re-raised as it is.

    Args:
        fn: The worker function.
        args: Its arguments.

    Returns:
        What ``fn`` returned, or the failure it raised as a ``FormulaError``.
    """
    started = time.perf_counter()
    try:
        return fn(*args)
    except FormulaError as error:
        return WorkerFailure(
            category=error.category,
            code=error.code,
            message=error.message,
            hint=error.hint,
            detail=error.detail,
            parameter=error.parameter,
            diagnostics=WorkerDiagnostics(duration_s=time.perf_counter() - started),
        )
    except Exception as error:
        try:
            pickle.loads(pickle.dumps(error))  # our own exception, same process
        except Exception:  # any failure to round-trip means it must be replaced
            msg = f"{type(error).__name__}: {error}"
            raise RuntimeError(msg) from error  # the pool ships the original traceback as text
        raise


def silence_worker_logging() -> None:
    """Pool initializer: switch logging off in the worker process (ch. 8.14).

    Workers return diagnostics and the parent logs them, so a worker never logs. A pool the
    caller injects brings its own initializer, if it wants this guarantee.
    """
    logging.disable(logging.CRITICAL)


def _log_diagnostics(fn: Callable[..., object], diagnostics: WorkerDiagnostics) -> None:
    """Log what a worker reported; workers never log themselves (ch. 8.14)."""
    logger.debug(
        "worker finished: fn=%s duration=%.3fs status=%s iterations=%s notes=%s",
        getattr(fn, "__qualname__", repr(fn)),
        diagnostics.duration_s,
        diagnostics.solver_status,
        diagnostics.iterations,
        "; ".join(diagnostics.notes),
    )


@runtime_checkable
class RoutedRequest(Protocol):
    """A worker request that names the model function its job uses (ch. 8.10).

    The adapter computes the key (``solvers.aero_model.model_key``) in the parent and puts it in
    the request, so :meth:`SolverRuntime.run_cpu` can route the job to a worker that holds the
    function. ``None`` routes like a job without a model.

    Attributes:
        model_key: The model key, or ``None``.
    """

    model_key: str | None


def _routing_key(args: Sequence[object]) -> str | None:
    """The model key of the first argument that names one, ``None`` if none does."""
    for arg in args:
        if isinstance(arg, RoutedRequest) and arg.model_key is not None:
            return arg.model_key
    return None


def _shut_down(pools: Sequence[ProcessPoolExecutor]) -> None:
    """Shut the worker pools down, waiting for each process; run off the event loop."""
    for pool in pools:
        pool.shutdown(wait=True, cancel_futures=True)


def _run_in_slot(
    max_models: int,
    fn: Callable[..., WorkerOutcome[T] | WorkerFailure],
    args: tuple[object, ...],
) -> WorkerOutcome[T] | WorkerFailure:
    """What a worker slot runs: install the worker's model cache, then :func:`run_in_worker`.

    The cache is installed here, in the worker process, on its first job (idempotent), so the
    parent process never holds one. The pool initializer stays :func:`silence_worker_logging`.

    Args:
        max_models: The bound of the worker's model cache.
        fn: The worker function.
        args: Its arguments.

    Returns:
        As :func:`run_in_worker`.
    """
    install_model_cache(max_models)
    return run_in_worker(fn, args)


@dataclass(eq=False)
class _WorkerSlot:
    """One worker process (a single-process pool) and the parent's mirror of its model cache.

    The mirror is a guess at what the worker holds, updated as jobs are routed; a wrong guess costs
    a build in the worker, never a value.

    Attributes:
        index: Position of the slot, for the log.
        pool: The pool, created on the slot's first job; ``None`` before and after a dead worker.
        busy: Whether a job of this slot is still running in the worker (also one whose caller
            was cancelled).
        models: The model keys the worker is believed to hold, least recently used first.
        last_used: Sequence number of the slot's last job; 0 if never used.
    """

    index: int
    pool: ProcessPoolExecutor | None = None
    busy: bool = False
    models: OrderedDict[str, None] = field(default_factory=lambda: OrderedDict[str, None]())
    last_used: int = 0


class SolverRuntime:
    """Worker processes and concurrency limit for the solver adapters (ch. 8.10).

    The runtime has ``max_workers`` worker slots, each one process (a single-process pool with the
    ``spawn`` start method: CasADi/IPOPT and numpy do not reliably release the GIL, and ``spawn``
    behaves the same on macOS and Linux), created lazily on the slot's first job. Each worker keeps
    a bounded cache of AeroBuildup model functions (``solvers.aero_model``); a job that names a
    ``model_key`` is routed to a free slot believed to hold it (affinity), so a repeated geometry
    is not built again in another worker. The limit counts concurrent solver calls: pool tasks and
    subprocesses. The semaphores are created on first use inside the running event loop, so a
    runtime is bound to one event loop. Use ``async with`` or :meth:`aclose`.
    """

    def __init__(
        self,
        *,
        max_workers: int | None = None,
        max_concurrency: int | None = None,
        max_models_per_worker: int = MAX_MODELS_PER_WORKER,
    ) -> None:
        """Create the runtime; nothing starts yet.

        Args:
            max_workers: Worker processes; default ``os.cpu_count()``.
            max_concurrency: Concurrent solver calls; default ``os.cpu_count()``.
            max_models_per_worker: Model functions each worker keeps (about 280 MB each).

        Raises:
            ValueError: If ``max_concurrency``, ``max_workers`` or ``max_models_per_worker`` is
                below 1.
        """
        for name, value in (("max_concurrency", max_concurrency), ("max_workers", max_workers)):
            if value is not None and value < 1:
                msg = f"{name} must be >= 1, got {value}"
                raise ValueError(msg)
        if max_models_per_worker < 1:
            msg = f"max_models_per_worker must be >= 1, got {max_models_per_worker}"
            raise ValueError(msg)
        self.max_concurrency = max_concurrency or os.cpu_count() or 1
        self._max_workers = max_workers
        self._max_models = max_models_per_worker
        self._workers = [
            _WorkerSlot(index=index) for index in range(max_workers or os.cpu_count() or 1)
        ]
        self._uses = 0
        # The threads that run ``Popen.communicate`` (one per concurrent subprocess, so the limit
        # above is also their size). Owned like the worker processes, never asyncio's default
        # executor; threads start on first use.
        self._threads = ThreadPoolExecutor(
            max_workers=self.max_concurrency, thread_name_prefix="aero_kernel_process"
        )
        self._slots: asyncio.Semaphore | None = None
        self._worker_slots: asyncio.Semaphore | None = None
        self._closed = False
        # This runtime's own calls: pool jobs (cancelling the caller does not stop a running worker)
        # and subprocess tasks. ``aclose`` drains both.
        self._pool_jobs: set[concurrent.futures.Future[object]] = set()
        self._process_tasks: set[asyncio.Task[ProcessRun]] = set()

    async def __aenter__(self) -> Self:
        """Enter the ``async with`` block."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the runtime when the block ends."""
        await self.aclose()

    async def aclose(self) -> None:
        """Wait for this runtime's own running calls, then shut every worker down; idempotent.

        When this returns, no work of this runtime is running: pool jobs (also those whose caller
        was cancelled) and subprocess calls are waited for, off the event loop, and their callers
        get their results. The workers are then shut down, off the loop. Calls that have not
        reached a worker (waiting for a slot or for a free worker) raise ``RuntimeError``. A job is
        submitted only to an idle worker, so nothing waits in a pool's queue and no call starts
        after closing began.
        """
        self._closed = True
        if self._process_tasks:
            await asyncio.wait(list(self._process_tasks))
        if self._pool_jobs:
            await asyncio.to_thread(concurrent.futures.wait, list(self._pool_jobs))
        pools: list[ProcessPoolExecutor] = []
        for slot in self._workers:
            if slot.pool is not None:
                pools.append(slot.pool)
                slot.pool = None
            slot.models.clear()
        if pools:
            await asyncio.to_thread(_shut_down, pools)
        # Every subprocess call has ended above and reaped its thread (or said it could not).
        # wait=False: a thread stuck in ``communicate`` on a descendant that left the process
        # group does not block closing. It does block interpreter exit, though (concurrent.futures
        # joins its threads in an atexit hook) until that descendant exits.
        self._threads.shutdown(wait=False, cancel_futures=True)

    def _check_open(self) -> None:
        """Raise ``RuntimeError`` once the runtime is closed."""
        if self._closed:
            msg = "the solver runtime is closed"
            raise RuntimeError(msg)

    def _slot_limit(self) -> asyncio.Semaphore:
        """Return the semaphore, creating it inside the running loop on first use."""
        if self._slots is None:
            self._slots = asyncio.Semaphore(self.max_concurrency)
        return self._slots

    def _worker_gate(self) -> asyncio.Semaphore:
        """The gate of idle workers: one permit per worker not running a job (ch. 8.10)."""
        if self._worker_slots is None:
            self._worker_slots = asyncio.Semaphore(len(self._workers))
        return self._worker_slots

    def _choose(self, model_key: str | None) -> _WorkerSlot:
        """Pick an idle worker for a job; called right after a permit of the gate was taken.

        A job with a key takes an idle worker believed to hold it; else an idle one with room in
        its cache (a running one before a new one); else the idle one used least recently, whose
        oldest function makes room. A job without a key takes the idle running worker used least
        recently, or a new one. Routing is a guess: a miss costs a build, never a value.
        """
        idle = [slot for slot in self._workers if not slot.busy]
        started = [slot for slot in idle if slot.pool is not None]
        if model_key is None:
            return min(started or idle, key=lambda slot: slot.last_used)
        holding = [slot for slot in idle if model_key in slot.models]
        if holding:
            chosen, hit = holding[0], True
        else:
            roomy = [slot for slot in idle if len(slot.models) < self._max_models]
            roomy_started = [slot for slot in roomy if slot.pool is not None]
            candidates = roomy_started or roomy or idle
            chosen, hit = min(candidates, key=lambda slot: slot.last_used), False
        chosen.models[model_key] = None
        chosen.models.move_to_end(model_key)
        while len(chosen.models) > self._max_models:
            chosen.models.popitem(last=False)
        logger.debug(
            "model %s routed to worker %d (%s)",
            model_key[:15],
            chosen.index,
            "held" if hit else "to be built",
        )
        return chosen

    def _submit(
        self,
        slot: _WorkerSlot,
        fn: Callable[..., WorkerOutcome[T] | WorkerFailure],
        args: tuple[object, ...],
    ) -> concurrent.futures.Future[WorkerOutcome[T] | WorkerFailure]:
        """Submit a job to a slot's worker, creating the worker on first use; never after closing."""
        self._check_open()
        if slot.pool is None:
            slot.pool = ProcessPoolExecutor(
                max_workers=1,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=silence_worker_logging,
            )
        job = slot.pool.submit(_run_in_slot, self._max_models, fn, args)
        self._uses += 1
        slot.busy, slot.last_used = True, self._uses
        return job

    def _discard_worker(self, slot: _WorkerSlot) -> None:
        """Drop a slot whose worker died, so its next job starts a fresh one; the others stay."""
        if slot.pool is not None:
            slot.pool.shutdown(wait=False, cancel_futures=True)
            slot.pool = None
        slot.models.clear()

    def _job_ended(
        self,
        slot: _WorkerSlot,
        gate: asyncio.Semaphore,
        job: asyncio.Future[WorkerOutcome[T] | WorkerFailure],
    ) -> None:
        """Free a slot when its job has really ended in the worker, also after its caller left.

        A dead worker is discarded here, before the slot is free again, so no other call is
        handed to it.
        """
        if not job.cancelled() and isinstance(job.exception(), BrokenProcessPool):
            self._discard_worker(slot)
        slot.busy = False
        gate.release()

    async def run_cpu(
        self,
        fn: Callable[..., WorkerOutcome[T] | WorkerFailure],
        *args: object,
    ) -> T:
        """Run ``fn(*args)`` in a worker process, off the event loop, within the limit.

        ``fn`` must be a picklable top-level function that returns a :class:`WorkerOutcome` or a
        :class:`WorkerFailure` and does not log. Cancelling the awaiting task frees its slot of
        the concurrency limit at once; a worker already running finishes, its result is discarded
        and the worker takes no other job before (ch. 8.10). An argument that is a
        :class:`RoutedRequest` names the model function the job uses; the job is routed by it.

        Args:
            fn: The worker function.
            *args: Its picklable arguments.

        Returns:
            The value of the worker's outcome.

        Raises:
            FormulaError: If the worker returned a :class:`WorkerFailure`.
            TypeError: If the worker returned anything else (a programming error).
            BrokenProcessPool: If the worker process died; logged at ``WARNING``.
            RuntimeError: If the runtime is closed.
        """
        self._check_open()
        model_key = _routing_key(args)
        async with self._slot_limit():
            gate = self._worker_gate()
            await gate.acquire()
            try:
                self._check_open()
                slot = self._choose(model_key)
            except BaseException:
                gate.release()
                raise
            try:
                job = self._submit(slot, fn, args)
            except BrokenProcessPool:
                logger.warning("a process-pool worker died before running %s", fn)
                self._discard_worker(slot)
                gate.release()
                raise
            except BaseException:
                gate.release()
                raise
            # Future is invariant; the set only waits on and discards jobs, never reads them.
            tracked = cast("concurrent.futures.Future[object]", job)
            self._pool_jobs.add(tracked)
            tracked.add_done_callback(self._pool_jobs.discard)
            waiting = asyncio.wrap_future(job)
            # Registered before the caller awaits, so the slot is free before the caller resumes.
            waiting.add_done_callback(functools.partial(self._job_ended, slot, gate))
            try:
                result = cast(
                    "object",  # widened on purpose: the contract check below is a runtime guard
                    await asyncio.shield(waiting),
                )
            except BrokenProcessPool:
                logger.warning("a process-pool worker died while running %s", fn)
                raise
        if isinstance(result, WorkerFailure):
            _log_diagnostics(fn, result.diagnostics)
            raise result.to_formula_error()
        if not isinstance(result, WorkerOutcome):
            msg = f"worker {fn} must return a WorkerOutcome or WorkerFailure, got {type(result)}"
            raise TypeError(msg)
        # The isinstance check erases the type parameter; ``fn`` is declared to return T.
        outcome = cast("WorkerOutcome[T]", result)
        _log_diagnostics(fn, outcome.diagnostics)
        return outcome.value

    async def run_process(
        self,
        files: Mapping[str, str | bytes],
        commands: str,
        *,
        executable: str | Path,
        args: Sequence[str] = (),
        collect: Sequence[str] = (),
    ) -> ProcessRun:
        """Run an external binary within the limit; see :func:`solvers.process.run_process`.

        Cancelling or timing out kills the process and removes its directory (Q17).

        Args:
            files: Input files by plain file name.
            commands: Text written to stdin.
            executable: The binary to start.
            args: Its command-line arguments.
            collect: Names of output files to read back.

        Returns:
            The exit code, the output streams and the collected files.

        Raises:
            RuntimeError: If the runtime is closed.
        """
        self._check_open()
        async with self._slot_limit():
            self._check_open()
            task = asyncio.ensure_future(
                run_process(
                    files,
                    commands,
                    executable=executable,
                    args=args,
                    collect=collect,
                    executor=self._threads,
                )
            )
            self._process_tasks.add(task)
            task.add_done_callback(self._process_tasks.discard)
            return await task
