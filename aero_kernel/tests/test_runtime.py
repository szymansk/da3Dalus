"""The solver runtime: process pool, concurrency limit, cancellation (ch. 8.10; Q16, Q17, Q19)."""

import asyncio
import concurrent.futures
import gc
import logging
import multiprocessing
import sys
import textwrap
import threading
import time
import traceback
import weakref
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from multiprocessing.context import BaseContext
from pathlib import Path
from typing import ParamSpec, TypeVar

import aero_kernel.runtime as runtime_module
import pytest
import pytest_asyncio
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import (
    SolverRuntime,
    WorkerFailure,
    WorkerOutcome,
    run_in_worker,
    silence_worker_logging,
)
from aero_kernel.solvers.process import ProcessRun
from aero_kernel.tests import runtime_workers as workers

pytestmark = pytest.mark.asyncio(loop_scope="module")

T = TypeVar("T")
CALL_BOUND_S = 15.0

STAMP_SCRIPT = textwrap.dedent(
    """
    import sys, time
    start = time.time()
    time.sleep(0.3)
    print(start, time.time())
    """
)


class BoundedRuntime(SolverRuntime):
    """A runtime whose every call is bounded, so a leaked gate slot fails a test, never hangs it.

    The bound is an ``asyncio.timeout`` (a signal-based pytest timeout can fire while pytest
    formats a traceback and abort the run); pytest-timeout stays as the global backstop.
    """

    async def run_cpu(
        self, fn: Callable[..., WorkerOutcome[T] | WorkerFailure], *args: object
    ) -> T:
        """Run ``SolverRuntime.run_cpu`` within the bound."""
        async with asyncio.timeout(CALL_BOUND_S):
            return await super().run_cpu(fn, *args)

    async def run_process(
        self,
        files: Mapping[str, str | bytes],
        commands: str,
        *,
        executable: str | Path,
        args: Sequence[str] = (),
        collect: Sequence[str] = (),
    ) -> ProcessRun:
        """Run ``SolverRuntime.run_process`` within the bound."""
        async with asyncio.timeout(CALL_BOUND_S):
            return await super().run_process(
                files, commands, executable=executable, args=args, collect=collect
            )

    async def assert_gates_full(self) -> None:
        """Fail unless every slot of the concurrency limit and of the worker gate is free again.

        A call that ended without releasing its slot leaves a gate short; it is found by taking
        every slot with a short wait.
        """
        for gate, size in ((self._slots, self.max_concurrency), (self._worker_slots, None)):
            if gate is None:
                continue
            taken = 0
            try:
                for _ in range(size or self._max_workers or 1):
                    await asyncio.wait_for(gate.acquire(), timeout=0.5)
                    taken += 1
            except TimeoutError:
                pytest.fail(f"a gate lost a slot: only {taken} of its slots are free")
            finally:
                for _ in range(taken):
                    gate.release()


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def shared_pool() -> AsyncIterator[BoundedRuntime]:
    """One runtime (one spawned pool) for the tests that need no special configuration."""
    async with BoundedRuntime(max_workers=2) as runtime:
        yield runtime


@pytest_asyncio.fixture(loop_scope="module")
async def shared_runtime(shared_pool: BoundedRuntime) -> AsyncIterator[BoundedRuntime]:
    """The shared runtime; after each test its gates must be whole, so a leak fails that test."""
    yield shared_pool
    await shared_pool.assert_gates_full()


P = ParamSpec("P")
R = TypeVar("R")


class LaggingPool(ProcessPoolExecutor):
    """A pool that takes each job 0.3 s after ``submit`` returned: submitted, not yet queued.

    That is the window in which ``shutdown(cancel_futures=True)`` would cancel an accepted job.
    """

    def submit(
        self, fn: Callable[P, R], /, *args: P.args, **kwargs: P.kwargs
    ) -> concurrent.futures.Future[R]:
        """Return a stand-in future at once and hand the job to the real pool later."""
        stand_in: concurrent.futures.Future[R] = concurrent.futures.Future()

        def hand_over() -> None:
            time.sleep(0.3)
            try:
                real = super(LaggingPool, self).submit(fn, *args, **kwargs)
            except RuntimeError as error:  # the pool was shut down first
                stand_in.set_exception(error)
                return

            def copy(done: concurrent.futures.Future[R]) -> None:
                error = done.exception()
                if error is not None:
                    stand_in.set_exception(error)
                else:
                    stand_in.set_result(done.result())

            real.add_done_callback(copy)

        threading.Thread(target=hand_over, daemon=True).start()
        return stand_in


def max_overlap(intervals: Sequence[tuple[float, float]]) -> int:
    """Largest number of intervals that are open at the same time."""
    events = sorted([(start, 1) for start, _ in intervals] + [(end, -1) for _, end in intervals])
    open_now = peak = 0
    for _, delta in events:
        open_now += delta
        peak = max(peak, open_now)
    return peak


class TestRunCpu:
    async def test_returns_the_value_of_the_worker(self, shared_runtime: SolverRuntime) -> None:
        assert await shared_runtime.run_cpu(workers.square, 7) == 49

    async def test_parent_logs_the_worker_diagnostics(
        self, shared_runtime: SolverRuntime, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="aero_kernel.runtime"):
            await shared_runtime.run_cpu(workers.square, 2)
        (record,) = [r for r in caplog.records if r.name == "aero_kernel.runtime"]
        message = record.getMessage()
        assert record.levelno == logging.DEBUG
        assert "square" in message
        assert "0.250" in message
        assert "ok" in message
        assert "iterations=3" in message
        assert "first" in message

    async def test_an_expected_failure_becomes_a_formula_error(
        self, shared_runtime: SolverRuntime, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            caplog.at_level(logging.DEBUG, logger="aero_kernel.runtime"),
            pytest.raises(FormulaError) as caught,
        ):
            await shared_runtime.run_cpu(workers.expected_failure)
        error = caught.value
        assert error.category is ErrorCategory.NOT_CONVERGED
        assert error.code == "not_converged"
        assert error.hint == "relax the tolerance"
        assert error.detail == {"iterations": 50}
        assert any("max_iter" in r.getMessage() for r in caplog.records)

    async def test_a_bare_return_value_is_a_type_error(self, shared_runtime: SolverRuntime) -> None:
        with pytest.raises(TypeError, match="WorkerOutcome"):
            await shared_runtime.run_cpu(workers.plain, 1)  # pyright: ignore[reportArgumentType]  # contract violation under test

    async def test_an_unexpected_exception_propagates(self, shared_runtime: SolverRuntime) -> None:
        with pytest.raises(ValueError, match="worker exploded"):
            await shared_runtime.run_cpu(workers.boom)

    async def test_a_worker_raising_formula_error_neither_breaks_the_pool_nor_its_siblings(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        async with BoundedRuntime(max_workers=2, max_concurrency=2) as runtime:
            sibling = asyncio.create_task(runtime.run_cpu(workers.nap, 0.8))
            await asyncio.sleep(0.5)
            with (
                caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"),
                pytest.raises(FormulaError) as caught,
            ):
                await runtime.run_cpu(workers.raise_formula)
            start, end = await sibling
            assert await runtime.run_cpu(workers.square, 2) == 4
        assert caught.value.code == "missing_input"
        assert caught.value.category is ErrorCategory.INVALID_INPUT
        assert end > start
        assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []

    async def test_an_exception_that_cannot_be_unpickled_still_reaches_the_caller(
        self, shared_runtime: SolverRuntime
    ) -> None:
        with pytest.raises(RuntimeError, match="UnpicklableError: odd"):
            await shared_runtime.run_cpu(workers.raise_unpicklable)
        assert await shared_runtime.run_cpu(workers.square, 3) == 9

    async def test_the_worker_side_traceback_of_a_replaced_exception_survives(
        self, shared_runtime: SolverRuntime
    ) -> None:
        with pytest.raises(RuntimeError) as caught:
            await shared_runtime.run_cpu(workers.raise_unpicklable)
        text = "".join(traceback.format_exception(caught.value))
        assert "failure_site" in text

    async def test_parameter_survives_the_process_boundary(
        self, shared_runtime: SolverRuntime
    ) -> None:
        with pytest.raises(FormulaError) as caught:
            await shared_runtime.run_cpu(workers.raise_formula_with_path)
        assert caught.value.parameter == "geometry.wings[0].span"

    async def test_workers_are_spawned_not_forked(self, shared_runtime: SolverRuntime) -> None:
        # a forked worker inherits the parent's test module; a spawned one starts clean
        assert await shared_runtime.run_cpu(workers.parent_test_module_is_loaded) is False

    async def test_workers_have_logging_switched_off(self, shared_runtime: SolverRuntime) -> None:
        """Pool workers do not log (ch. 8.14): the pool initializer guarantees it."""
        assert await shared_runtime.run_cpu(workers.logging_is_disabled) is True

    async def test_the_initializer_disables_logging(self) -> None:
        try:
            silence_worker_logging()
            assert not logging.getLogger("aero_kernel.x").isEnabledFor(logging.CRITICAL)
        finally:
            logging.disable(logging.NOTSET)

    async def test_the_loop_stays_responsive_during_pool_work(
        self, shared_runtime: SolverRuntime
    ) -> None:
        """Q16: a concurrent ``asyncio.sleep(0.01)`` is delayed by less than 50 ms."""
        await shared_runtime.run_cpu(workers.square, 1)  # pool is warm: only the loop is measured
        worst_delay = 0.0
        stop = asyncio.Event()

        async def ticker() -> None:
            nonlocal worst_delay
            while not stop.is_set():
                before = time.perf_counter()
                await asyncio.sleep(0.01)
                worst_delay = max(worst_delay, time.perf_counter() - before - 0.01)

        ticking = asyncio.create_task(ticker())
        await asyncio.sleep(0)  # let the ticker start, or a blocking run_cpu would hide behind it
        await shared_runtime.run_cpu(workers.nap, 0.6)
        stop.set()
        await ticking
        assert worst_delay < 0.05

    async def test_an_in_loop_sleep_would_fail_the_responsiveness_probe(self) -> None:
        """The Q16 probe discriminates: blocking the loop for 0.2 s shows as a delay > 50 ms."""
        delays: list[float] = []

        async def ticker() -> None:
            before = time.perf_counter()
            await asyncio.sleep(0.01)
            delays.append(time.perf_counter() - before - 0.01)

        ticking = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        time.sleep(0.2)  # noqa: ASYNC251  # blocks the loop on purpose
        await ticking
        assert delays[0] > 0.05


class TestConcurrencyLimit:
    async def test_at_most_max_concurrency_calls_run_at_once(self) -> None:
        async with BoundedRuntime(max_workers=4, max_concurrency=2) as runtime:
            results = await asyncio.gather(*(runtime.run_cpu(workers.nap, 0.3) for _ in range(5)))
        assert max_overlap(results) == 2

    async def test_the_limit_defaults_to_the_cpu_count(self) -> None:
        runtime = BoundedRuntime()
        assert runtime.max_concurrency >= 1

    @pytest.mark.parametrize("bad", [0, -1])
    async def test_rejects_a_limit_below_one(self, bad: int) -> None:
        with pytest.raises(ValueError, match="max_concurrency"):
            BoundedRuntime(max_concurrency=bad)

    async def test_subprocesses_share_the_limit(self, tmp_path: Path) -> None:
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        async with BoundedRuntime(max_workers=1, max_concurrency=1) as runtime:
            runs = await asyncio.gather(
                *(
                    runtime.run_process({}, "", executable=sys.executable, args=[str(script)])
                    for _ in range(3)
                )
            )
        spans = [tuple(float(x) for x in run.stdout.split()) for run in runs]
        assert max_overlap([(a, b) for a, b in spans]) == 1  # pyright: ignore[reportUnknownVariableType]

    async def test_a_subprocess_takes_no_worker_gate_slot(self, tmp_path: Path) -> None:
        """The worker gate belongs to pool submissions; a subprocess counts only against the limit."""
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        async with BoundedRuntime(max_workers=1, max_concurrency=2) as runtime:
            await runtime.run_cpu(workers.square, 1)  # warm: the pool is up
            process, outcome = await asyncio.gather(
                runtime.run_process({}, "", executable=sys.executable, args=[str(script)]),
                runtime.run_cpu(workers.nap, 0.5),
            )
        start, end = (float(x) for x in process.stdout.split())
        assert max_overlap([(start, end), outcome]) == 2
        # not just touching: they ran side by side for a clear stretch
        assert min(end, outcome[1]) - max(start, outcome[0]) > 0.15

    async def test_pool_work_and_subprocesses_count_together(self, tmp_path: Path) -> None:
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        async with BoundedRuntime(max_workers=2, max_concurrency=1) as runtime:
            process, outcome = await asyncio.gather(
                runtime.run_process({}, "", executable=sys.executable, args=[str(script)]),
                runtime.run_cpu(workers.nap, 0.3),
            )
        start, end = (float(x) for x in process.stdout.split())
        assert max_overlap([(start, end), outcome]) == 1


class TestCancellationAndBudget:
    async def test_cancel_propagates_and_frees_the_slot(self) -> None:
        async with BoundedRuntime(max_workers=2, max_concurrency=1) as runtime:
            running = asyncio.create_task(runtime.run_cpu(workers.nap, 1.5))
            await asyncio.sleep(0.3)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            # the abandoned worker still runs, but the slot is free at once
            async with asyncio.timeout(1.0):
                assert await runtime.run_cpu(workers.square, 3) == 9

    async def test_an_exceeded_budget_times_out_the_open_work(self) -> None:
        """Q19: the budget expires on the open call; a finished call keeps its result."""
        async with BoundedRuntime(max_workers=2) as runtime:
            finished = await runtime.run_cpu(workers.square, 4)
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.3):
                    await runtime.run_cpu(workers.nap, 1.5)
        assert finished == 16

    async def test_an_exceeded_budget_kills_the_subprocess_and_cleans_up(
        self, tmp_path: Path
    ) -> None:
        sleeper = tmp_path / "sleeper.py"
        sleeper.write_text("import time\ntime.sleep(60)\n")
        async with BoundedRuntime(max_workers=1) as runtime:
            started = time.perf_counter()
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.5):
                    await runtime.run_process(
                        {}, "", executable=sys.executable, args=[str(sleeper)]
                    )
        assert time.perf_counter() - started < 5

    async def test_cancel_through_the_runtime_kills_the_subprocess(self, tmp_path: Path) -> None:
        """Q17 through the runtime: the slot of a killed process is free again."""
        sleeper = tmp_path / "sleeper.py"
        sleeper.write_text("import time\ntime.sleep(60)\n")
        async with BoundedRuntime(max_workers=1, max_concurrency=1) as runtime:
            running = asyncio.create_task(
                runtime.run_process({}, "", executable=sys.executable, args=[str(sleeper)])
            )
            await asyncio.sleep(0.5)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            async with asyncio.timeout(5):
                assert await runtime.run_cpu(workers.square, 2) == 4


class TestPoolLifetime:
    async def test_nothing_starts_before_the_first_call(self) -> None:
        before = multiprocessing.active_children()
        runtime = BoundedRuntime()
        assert multiprocessing.active_children() == before
        await runtime.aclose()

    async def test_aclose_waits_for_the_workers_and_leaves_no_process(self) -> None:
        before = multiprocessing.active_children()
        runtime = BoundedRuntime(max_workers=2)
        await runtime.run_cpu(workers.square, 1)
        assert len(multiprocessing.active_children()) > len(before)
        await runtime.aclose()
        assert multiprocessing.active_children() == before

    async def test_close_refuses_a_call_waiting_for_a_slot_and_creates_no_pool(self) -> None:
        before = multiprocessing.active_children()
        runtime = BoundedRuntime(max_workers=1, max_concurrency=1)
        await runtime.run_cpu(workers.square, 1)  # warm: the pool exists
        running = asyncio.create_task(runtime.run_cpu(workers.nap, 0.6))
        await asyncio.sleep(0.2)
        waiting = asyncio.create_task(runtime.run_cpu(workers.nap, 0.1))
        await asyncio.sleep(0.1)
        await runtime.aclose()
        assert multiprocessing.active_children() == before
        results = await asyncio.gather(running, waiting, return_exceptions=True)
        assert isinstance(results[0], tuple)  # the call already running finished
        assert isinstance(results[1], RuntimeError)
        assert "closed" in str(results[1])
        assert multiprocessing.active_children() == before

    async def test_close_turns_queued_pool_calls_into_closed_errors_not_cancellation(
        self,
    ) -> None:
        runtime = BoundedRuntime(max_workers=1, max_concurrency=8)
        await runtime.run_cpu(workers.square, 1)
        calls = [asyncio.create_task(runtime.run_cpu(workers.nap, 0.5)) for _ in range(6)]
        await asyncio.sleep(0.3)
        await runtime.aclose()
        results = await asyncio.gather(*calls, return_exceptions=True)
        # an owned pool is gated by its worker count: exactly the running call finishes
        assert isinstance(results[0], tuple)
        refused = results[1:]
        assert all(isinstance(r, RuntimeError) for r in refused)
        assert len(refused) == 5
        assert all("closed" in str(r) for r in refused)
        assert not any(call.cancelled() for call in calls)

    async def test_a_real_cancellation_of_a_queued_call_still_raises_cancelled_error(
        self,
    ) -> None:
        async with BoundedRuntime(max_workers=1, max_concurrency=8) as runtime:
            await runtime.run_cpu(workers.square, 1)
            running = asyncio.create_task(runtime.run_cpu(workers.nap, 0.5))
            queued = asyncio.create_task(runtime.run_cpu(workers.nap, 0.5))
            await asyncio.sleep(0.2)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            await running

    async def test_the_loop_stays_free_while_aclose_waits_for_a_worker(self) -> None:
        runtime = BoundedRuntime(max_workers=1)
        await runtime.run_cpu(workers.square, 1)
        running = asyncio.create_task(runtime.run_cpu(workers.nap, 0.8))
        await asyncio.sleep(0.2)
        worst_delay = 0.0
        stop = asyncio.Event()

        async def ticker() -> None:
            nonlocal worst_delay
            while not stop.is_set():
                before = time.perf_counter()
                await asyncio.sleep(0.01)
                worst_delay = max(worst_delay, time.perf_counter() - before - 0.01)

        ticking = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        await runtime.aclose()  # waits for the nap
        stop.set()
        await ticking
        await running
        assert worst_delay < 0.05

    async def test_run_process_after_close_raises(self, tmp_path: Path) -> None:
        runtime = BoundedRuntime(max_workers=1)
        await runtime.aclose()
        with pytest.raises(RuntimeError, match="closed"):
            await runtime.run_process({}, "", executable=sys.executable, args=["-c", "pass"])

    async def test_close_refuses_a_process_call_waiting_for_a_slot(self) -> None:
        runtime = BoundedRuntime(max_workers=1, max_concurrency=1)
        await runtime.run_cpu(workers.square, 1)
        running = asyncio.create_task(runtime.run_cpu(workers.nap, 0.6))
        await asyncio.sleep(0.2)
        waiting = asyncio.create_task(
            runtime.run_process({}, "", executable=sys.executable, args=["-c", "pass"])
        )
        await asyncio.sleep(0.1)
        await runtime.aclose()
        await running
        with pytest.raises(RuntimeError, match="closed"):
            await waiting

    async def test_no_pool_is_built_before_the_first_call(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        created: list[dict[str, object]] = []
        real = ProcessPoolExecutor

        def recording(
            max_workers: int | None,
            mp_context: BaseContext,
            initializer: Callable[[], None],
        ) -> ProcessPoolExecutor:
            created.append(
                {"mp_context": mp_context, "initializer": initializer, "max_workers": max_workers}
            )
            return real(max_workers=max_workers, mp_context=mp_context, initializer=initializer)

        monkeypatch.setattr(runtime_module, "ProcessPoolExecutor", recording)
        runtime = BoundedRuntime(max_workers=1)
        assert created == []
        await runtime.aclose()
        assert created == []
        async with BoundedRuntime(max_workers=1) as used:
            assert created == []
            await used.run_cpu(workers.square, 1)
            await used.run_cpu(workers.square, 2)
        (kwargs,) = created
        context = kwargs["mp_context"]
        assert isinstance(context, BaseContext)
        assert context.get_start_method() == "spawn"
        assert kwargs["initializer"] is silence_worker_logging

    async def test_the_worker_gate_is_released_on_every_path(self) -> None:
        """One worker, one gate slot: a leaked slot would hang the next call."""
        async with BoundedRuntime(max_workers=1, max_concurrency=8) as runtime, asyncio.timeout(30):
            assert await runtime.run_cpu(workers.square, 1) == 1
            with pytest.raises(FormulaError):
                await runtime.run_cpu(workers.expected_failure)
            with pytest.raises(ValueError, match="worker exploded"):
                await runtime.run_cpu(workers.boom)
            with pytest.raises(TypeError):
                await runtime.run_cpu(workers.plain, 1)  # pyright: ignore[reportArgumentType]  # contract violation under test
            running = asyncio.create_task(runtime.run_cpu(workers.nap, 0.4))
            await asyncio.sleep(0.2)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            async with asyncio.timeout(10):
                assert await runtime.run_cpu(workers.square, 2) == 4
                with pytest.raises(BrokenProcessPool):
                    await runtime.run_cpu(workers.die)
                assert await runtime.run_cpu(workers.square, 3) == 9

    async def test_the_gate_follows_the_given_worker_count_not_the_concurrency_limit(
        self,
    ) -> None:
        """With 2 workers and a limit of 8, two calls run at once and a third waits."""
        async with BoundedRuntime(max_workers=2, max_concurrency=8) as runtime:
            await asyncio.gather(
                runtime.run_cpu(workers.square, 1), runtime.run_cpu(workers.square, 2)
            )
            results = await asyncio.gather(*(runtime.run_cpu(workers.nap, 0.3) for _ in range(4)))
        assert max_overlap(results) == 2

    async def test_a_caller_cancelling_a_queued_call_while_close_runs_still_sees_cancellation(
        self,
    ) -> None:
        """CancelledError is always re-raised (ch. 8.10), also for a call waiting at the gate."""
        runtime = BoundedRuntime(max_workers=1, max_concurrency=8)
        await runtime.run_cpu(workers.square, 1)
        calls = [asyncio.create_task(runtime.run_cpu(workers.nap, 0.5)) for _ in range(5)]
        await asyncio.sleep(0.3)
        closing = asyncio.create_task(runtime.aclose())
        await asyncio.sleep(0)  # aclose has begun
        victim = calls[-1]
        victim.cancel()
        results = await asyncio.gather(*calls, return_exceptions=True)
        await closing
        assert victim.cancelled()
        assert isinstance(results[-1], asyncio.CancelledError)
        assert isinstance(results[0], tuple)  # the running call finished
        assert all(isinstance(r, RuntimeError) and "closed" in str(r) for r in results[1:-1])

    async def test_aclose_waits_for_running_calls_and_their_callers_get_results(self) -> None:
        runtime = BoundedRuntime(max_workers=1)
        await runtime.run_cpu(workers.square, 1)
        call = asyncio.create_task(runtime.run_cpu(workers.nap, 0.6))
        await asyncio.sleep(0.2)
        await runtime.aclose()
        closed_at = time.time()
        _, end = await call  # the caller got its result
        assert end <= closed_at

    async def test_aclose_also_waits_for_a_worker_whose_caller_was_cancelled(self) -> None:
        runtime = BoundedRuntime(max_workers=1)
        await runtime.run_cpu(workers.square, 1)
        started = time.perf_counter()
        call = asyncio.create_task(runtime.run_cpu(workers.nap, 0.8))
        await asyncio.sleep(0.2)
        call.cancel()
        with pytest.raises(asyncio.CancelledError):
            await call
        await runtime.aclose()
        assert time.perf_counter() - started >= 0.75  # the worker was still running

    async def test_the_executor_keyword_is_gone(self) -> None:
        with pytest.raises(TypeError, match="executor"):
            SolverRuntime(executor=object())  # pyright: ignore[reportCallIssue]  # removed parameter under test

    async def test_aclose_waits_for_a_running_subprocess_call(self, tmp_path: Path) -> None:
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        runtime = BoundedRuntime(max_workers=1)
        call = asyncio.create_task(
            runtime.run_process({}, "", executable=sys.executable, args=[str(script)])
        )
        await asyncio.sleep(0.15)
        await runtime.aclose()
        closed_at = time.time()
        run = await call  # not killed: it finished
        assert run.returncode == 0
        assert float(run.stdout.split()[1]) <= closed_at

    async def test_a_call_after_close_began_does_not_wait_for_a_slot(self) -> None:
        runtime = BoundedRuntime(max_workers=1, max_concurrency=1)
        holder = asyncio.create_task(runtime.run_cpu(workers.nap, 1.0))
        await asyncio.sleep(0.5)  # the holder owns the only slot
        closing = asyncio.create_task(runtime.aclose())
        await asyncio.sleep(0)  # aclose has begun and waits for the holder
        with pytest.raises(RuntimeError, match="closed"):
            await asyncio.wait_for(runtime.run_cpu(workers.square, 1), timeout=0.3)
        await holder
        await closing

    async def test_finished_pool_calls_are_not_kept_alive(self) -> None:
        async with BoundedRuntime(max_workers=1) as runtime:
            refs: list[weakref.ref[workers.Payload]] = []
            for _ in range(3):
                payload = await runtime.run_cpu(workers.make_payload)
                refs.append(weakref.ref(payload))
                del payload
            await asyncio.sleep(0.05)
            gc.collect()
            assert [ref() for ref in refs] == [None, None, None]

    async def test_finished_subprocess_calls_are_not_kept_alive(self) -> None:
        async with BoundedRuntime(max_workers=1) as runtime:
            refs: list[weakref.ref[ProcessRun]] = []
            for _ in range(3):
                run = await runtime.run_process(
                    {}, "", executable=sys.executable, args=["-c", "pass"]
                )
                refs.append(weakref.ref(run))
                del run
            await asyncio.sleep(0.05)
            gc.collect()
            assert [ref() for ref in refs] == [None, None, None]

    async def test_aclose_of_an_idle_owned_pool_keeps_the_loop_free(self) -> None:
        """Shutting down several workers joins their processes: that must happen off the loop."""
        runtime = BoundedRuntime(max_workers=6, max_concurrency=6)
        await asyncio.gather(*(runtime.run_cpu(workers.nap, 0.3) for _ in range(6)))
        worst_delay = 0.0
        stop = asyncio.Event()

        async def ticker() -> None:
            nonlocal worst_delay
            while not stop.is_set():
                before = time.perf_counter()
                await asyncio.sleep(0.01)
                worst_delay = max(worst_delay, time.perf_counter() - before - 0.01)

        ticking = asyncio.create_task(ticker())
        await asyncio.sleep(0)
        await runtime.aclose()
        stop.set()
        await ticking
        assert worst_delay < 0.05

    async def test_aclose_waits_for_a_submitted_job_before_it_shuts_the_pool_down(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A job accepted but not yet queued in the pool must not be cancelled by the shutdown."""
        monkeypatch.setattr(runtime_module, "ProcessPoolExecutor", LaggingPool)
        runtime = BoundedRuntime(max_workers=1)
        call = asyncio.create_task(runtime.run_cpu(workers.square, 6))
        await asyncio.sleep(0)  # the call has submitted; the pool has not got the job yet
        await runtime.aclose()
        assert await call == 36

    async def test_aclose_is_idempotent_and_blocks_further_use(self) -> None:
        runtime = BoundedRuntime(max_workers=1)
        await runtime.aclose()
        await runtime.aclose()
        with pytest.raises(RuntimeError, match="closed"):
            await runtime.run_cpu(workers.square, 1)

    async def test_a_dead_worker_warns_and_the_next_call_gets_a_fresh_pool(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        async with BoundedRuntime(max_workers=1) as runtime:
            with (
                caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"),
                pytest.raises(BrokenProcessPool),
            ):
                await runtime.run_cpu(workers.die)
            assert any(r.levelno == logging.WARNING for r in caplog.records)
            assert await runtime.run_cpu(workers.square, 8) == 64


class TestTrampoline:
    """Direct (in-process) tests: coverage cannot see the code that runs in a spawned worker."""

    async def test_passes_an_outcome_through(self) -> None:
        outcome = run_in_worker(workers.square, (3,))
        assert isinstance(outcome, WorkerOutcome)
        assert outcome.value == 9

    async def test_turns_a_formula_error_into_a_failure(self) -> None:
        failure = run_in_worker(workers.raise_formula, ())
        assert isinstance(failure, WorkerFailure)
        assert failure.code == "missing_input"
        assert failure.diagnostics.duration_s >= 0

    async def test_reraises_a_picklable_exception_as_it_is(self) -> None:
        with pytest.raises(ValueError, match="worker exploded"):
            run_in_worker(workers.boom, ())

    async def test_replaces_an_unpicklable_exception_chaining_the_original(self) -> None:
        with pytest.raises(RuntimeError, match="UnpicklableError: odd") as caught:
            run_in_worker(workers.raise_unpicklable, ())
        assert isinstance(caught.value.__cause__, workers.UnpicklableError)

    async def test_a_failure_keeps_every_field_of_the_formula_error(self) -> None:
        failure = run_in_worker(workers.raise_formula_with_path, ())
        assert isinstance(failure, WorkerFailure)
        assert failure.category is ErrorCategory.INVALID_INPUT
        assert failure.code == "missing_input"
        assert failure.message == "worker lacks an input"
        assert failure.hint == "pass it"
        assert failure.detail == {"span_mm": 0}
        assert failure.parameter == "geometry.wings[0].span"
        error = failure.to_formula_error()
        assert (error.message, error.hint, error.detail) == (
            "worker lacks an input",
            "pass it",
            {"span_mm": 0},
        )

    async def test_a_failure_reports_the_measured_duration(self) -> None:
        failure = run_in_worker(workers.slow_formula_failure, (0.02,))
        assert isinstance(failure, WorkerFailure)
        assert 0.02 <= failure.diagnostics.duration_s < 5

    async def test_a_failure_keeps_the_parameter(self) -> None:
        failure = run_in_worker(workers.raise_formula_with_path, ())
        assert isinstance(failure, WorkerFailure)
        assert failure.parameter == "geometry.wings[0].span"
        assert failure.to_formula_error().parameter == "geometry.wings[0].span"
