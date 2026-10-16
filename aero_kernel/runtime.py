"""Executor of the kernel: process pool, concurrency limit, cancellation (ARCHITECTURE ch. 8.10).

A :class:`SolverRuntime` is owned by whoever creates it (one ``compute()`` call or one
``CachedKernel``) and closed by them. The module keeps no state of its own, creates no pool at
import and never calls ``asyncio.run``. The per-request time budget is the engine's: it wraps
solver calls in ``asyncio.timeout``, and the ``TimeoutError`` and ``CancelledError`` raised here
leave the pool and any subprocess in a clean state.
"""

import asyncio
import concurrent.futures
import contextlib
import logging
import multiprocessing
import os
import pickle
import time
from collections.abc import AsyncGenerator, Callable, Mapping, Sequence
from concurrent.futures import Executor, ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Self, TypeVar, cast

from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.solvers.process import ProcessRun, run_process
from pydantic import BaseModel, ConfigDict, Field, JsonValue

logger = logging.getLogger(__name__)

__all__ = [
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
        input_path: Path of the offending input value, if any.
        diagnostics: The worker's report.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: ErrorCategory
    code: str
    message: str
    hint: str
    detail: dict[str, JsonValue] = Field(default_factory=dict)
    input_path: str | None = None
    diagnostics: WorkerDiagnostics

    def to_formula_error(self) -> FormulaError:
        """Build the ``FormulaError`` the failure stands for."""
        return FormulaError(
            self.category,
            self.code,
            self.message,
            self.hint,
            self.detail,
            self.input_path,
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
            input_path=error.input_path,
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


class SolverRuntime:
    """Process pool and concurrency limit for the solver adapters (ch. 8.10).

    The pool is created lazily on the first :meth:`run_cpu`, with the ``spawn`` start method
    (CasADi/IPOPT and numpy do not reliably release the GIL, and ``spawn`` behaves the same on
    macOS and Linux). The limit counts concurrent solver calls: pool tasks and subprocesses.
    The semaphore is created on first use inside the running event loop, so a runtime is bound
    to one event loop. Use ``async with`` or :meth:`aclose`.
    """

    def __init__(
        self,
        *,
        max_workers: int | None = None,
        max_concurrency: int | None = None,
        executor: Executor | None = None,
    ) -> None:
        """Create the runtime; nothing starts yet.

        Args:
            max_workers: Pool size when the runtime creates the pool; default ``os.cpu_count()``.
            max_concurrency: Concurrent solver calls; default ``os.cpu_count()``.
            executor: A pool owned by the caller. It is used as it is and never shut down here.

        Raises:
            ValueError: If ``max_concurrency`` is below 1.
        """
        if max_concurrency is not None and max_concurrency < 1:
            msg = f"max_concurrency must be >= 1, got {max_concurrency}"
            raise ValueError(msg)
        self.max_concurrency = max_concurrency or os.cpu_count() or 1
        self._max_workers = max_workers
        self._pool: Executor | None = executor
        self._owns_pool = executor is None
        self._slots: asyncio.Semaphore | None = None
        self._worker_slots: asyncio.Semaphore | None = None
        self._closed = False
        # This runtime's own calls: pool jobs (cancelling the caller does not stop a running worker)
        # and subprocess tasks. ``aclose`` drains both, whoever owns the executor.
        self._pool_jobs: set[concurrent.futures.Future[object]] = set()
        self._process_tasks: set[asyncio.Task[ProcessRun]] = set()

    async def __aenter__(self) -> Self:
        """Enter the ``async with`` block."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the runtime when the block ends."""
        await self.aclose()

    async def aclose(self) -> None:
        """Wait for this runtime's own running calls, then close the pool it created; idempotent.

        When this returns, no work of this runtime is running, whoever owns the executor: pool
        jobs (also those whose caller was cancelled) and subprocess calls are waited for, off the
        event loop, and their callers get their results. A pool the runtime created is then shut
        down; an injected executor is never shut down. Calls that have not reached a worker
        (waiting for a slot or for a free worker) raise ``RuntimeError``. An owned pool is gated by
        its worker count, so nothing waits in its own queue; an injected one has no such gate, so
        up to one call queued in it before closing began still starts, and is waited for.
        """
        self._closed = True
        if self._process_tasks:
            await asyncio.wait(list(self._process_tasks))
        if self._pool_jobs:
            await asyncio.to_thread(concurrent.futures.wait, list(self._pool_jobs))
        pool, self._pool = self._pool, None
        if pool is not None and self._owns_pool:
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)

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

    @contextlib.asynccontextmanager
    async def _free_worker(self) -> AsyncGenerator[None]:
        """Hold one worker of an owned pool, so no submission waits in the pool's own queue.

        An injected executor has an unknown worker count and gets no gate (ch. 8.10).
        """
        if not self._owns_pool:
            yield
            return
        if self._worker_slots is None:
            self._worker_slots = asyncio.Semaphore(self._max_workers or os.cpu_count() or 1)
        async with self._worker_slots:
            yield

    def _executor(self) -> Executor:
        """Return the pool, creating it on first use; never after the runtime is closed."""
        self._check_open()
        if self._pool is None:
            self._pool = ProcessPoolExecutor(
                max_workers=self._max_workers,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=silence_worker_logging,
            )
        return self._pool

    def _discard_broken_pool(self) -> None:
        """Drop a pool whose worker died, so the next call creates a fresh one.

        An injected pool is the caller's: it stays and keeps reporting the failure.
        """
        if self._owns_pool and self._pool is not None:
            self._pool.shutdown(wait=False, cancel_futures=True)
            self._pool = None

    async def run_cpu(
        self,
        fn: Callable[..., WorkerOutcome[T] | WorkerFailure],
        *args: object,
    ) -> T:
        """Run ``fn(*args)`` in the process pool, off the event loop, within the limit.

        ``fn`` must be a picklable top-level function that returns a :class:`WorkerOutcome` or a
        :class:`WorkerFailure` and does not log. Cancelling the awaiting task frees the slot at
        once; a worker already running finishes and its result is discarded (ch. 8.10).

        Args:
            fn: The worker function.
            *args: Its picklable arguments.

        Returns:
            The value of the worker's outcome.

        Raises:
            FormulaError: If the worker returned a :class:`WorkerFailure`.
            TypeError: If the worker returned anything else (a programming error).
            BrokenProcessPool: If a worker process died; logged at ``WARNING``.
            RuntimeError: If the runtime is closed.
        """
        self._check_open()
        async with self._slot_limit(), self._free_worker():
            self._check_open()
            try:
                job = self._executor().submit(run_in_worker, fn, args)
                # Future is invariant; the set only waits on and discards jobs, never reads them.
                tracked = cast("concurrent.futures.Future[object]", job)
                self._pool_jobs.add(tracked)
                tracked.add_done_callback(self._pool_jobs.discard)
                result = cast(
                    "object",  # widened on purpose: the contract check below is a runtime guard
                    await asyncio.wrap_future(job),
                )
            except asyncio.CancelledError:
                # Only the injector can cancel a pool future behind our back (an owned pool never
                # queues, see ``_free_worker``). The caller did not cancel: a programming error.
                task = asyncio.current_task()
                if task is not None and task.cancelling() == 0:
                    msg = "the injected executor was shut down"
                    raise RuntimeError(msg) from None
                raise
            except BrokenProcessPool:
                logger.warning("a process-pool worker died while running %s", fn)
                self._discard_broken_pool()
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
                run_process(files, commands, executable=executable, args=args, collect=collect)
            )
            self._process_tasks.add(task)
            task.add_done_callback(self._process_tasks.discard)
            return await task
