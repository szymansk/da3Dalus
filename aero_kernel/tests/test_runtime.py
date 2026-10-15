"""The solver runtime: process pool, concurrency limit, cancellation (ch. 8.10; Q16, Q17, Q19)."""

import asyncio
import logging
import multiprocessing
import sys
import textwrap
import time
from collections.abc import AsyncIterator, Sequence
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest
import pytest_asyncio
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import SolverRuntime, WorkerFailure, WorkerOutcome, run_in_worker
from aero_kernel.tests import runtime_workers as workers

pytestmark = pytest.mark.asyncio(loop_scope="module")

STAMP_SCRIPT = textwrap.dedent(
    """
    import sys, time
    start = time.time()
    time.sleep(0.3)
    print(start, time.time())
    """
)


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def shared_runtime() -> AsyncIterator[SolverRuntime]:
    """One runtime (one spawned pool) for the tests that need no special configuration."""
    async with SolverRuntime(max_workers=2) as runtime:
        yield runtime


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
        async with SolverRuntime(max_workers=2, max_concurrency=2) as runtime:
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
        async with SolverRuntime(max_workers=4, max_concurrency=2) as runtime:
            results = await asyncio.gather(*(runtime.run_cpu(workers.nap, 0.3) for _ in range(5)))
        assert max_overlap(results) == 2

    async def test_the_limit_defaults_to_the_cpu_count(self) -> None:
        runtime = SolverRuntime()
        assert runtime.max_concurrency >= 1

    @pytest.mark.parametrize("bad", [0, -1])
    async def test_rejects_a_limit_below_one(self, bad: int) -> None:
        with pytest.raises(ValueError, match="max_concurrency"):
            SolverRuntime(max_concurrency=bad)

    async def test_subprocesses_share_the_limit(self, tmp_path: Path) -> None:
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        async with SolverRuntime(max_workers=1, max_concurrency=1) as runtime:
            runs = await asyncio.gather(
                *(
                    runtime.run_process({}, "", executable=sys.executable, args=[str(script)])
                    for _ in range(3)
                )
            )
        spans = [tuple(float(x) for x in run.stdout.split()) for run in runs]
        assert max_overlap([(a, b) for a, b in spans]) == 1  # pyright: ignore[reportUnknownVariableType]

    async def test_pool_work_and_subprocesses_count_together(self, tmp_path: Path) -> None:
        script = tmp_path / "stamp.py"
        script.write_text(STAMP_SCRIPT)
        async with SolverRuntime(max_workers=2, max_concurrency=1) as runtime:
            process, outcome = await asyncio.gather(
                runtime.run_process({}, "", executable=sys.executable, args=[str(script)]),
                runtime.run_cpu(workers.nap, 0.3),
            )
        start, end = (float(x) for x in process.stdout.split())
        assert max_overlap([(start, end), outcome]) == 1


class TestCancellationAndBudget:
    async def test_cancel_propagates_and_frees_the_slot(self) -> None:
        async with SolverRuntime(max_workers=2, max_concurrency=1) as runtime:
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
        async with SolverRuntime(max_workers=2) as runtime:
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
        async with SolverRuntime(max_workers=1) as runtime:
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
        async with SolverRuntime(max_workers=1, max_concurrency=1) as runtime:
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
        runtime = SolverRuntime()
        assert multiprocessing.active_children() == before
        await runtime.aclose()

    async def test_aclose_waits_for_the_workers_and_leaves_no_process(self) -> None:
        before = multiprocessing.active_children()
        runtime = SolverRuntime(max_workers=2)
        await runtime.run_cpu(workers.square, 1)
        assert len(multiprocessing.active_children()) > len(before)
        await runtime.aclose()
        assert multiprocessing.active_children() == before

    async def test_aclose_is_idempotent_and_blocks_further_use(self) -> None:
        runtime = SolverRuntime(max_workers=1)
        await runtime.aclose()
        await runtime.aclose()
        with pytest.raises(RuntimeError, match="closed"):
            await runtime.run_cpu(workers.square, 1)

    async def test_an_injected_executor_is_never_shut_down(self) -> None:
        executor = ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn")
        )
        try:
            async with SolverRuntime(executor=executor) as runtime:
                assert await runtime.run_cpu(workers.square, 5) == 25
            # still usable by its owner after the runtime closed
            assert executor.submit(workers.square, 6).result(timeout=30).value == 36
        finally:
            executor.shutdown(wait=True)

    async def test_a_dead_worker_warns_and_the_next_call_gets_a_fresh_pool(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        async with SolverRuntime(max_workers=1) as runtime:
            with (
                caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"),
                pytest.raises(BrokenProcessPool),
            ):
                await runtime.run_cpu(workers.die)
            assert any(r.levelno == logging.WARNING for r in caplog.records)
            assert await runtime.run_cpu(workers.square, 8) == 64

    async def test_a_dead_worker_in_an_injected_executor_is_reported_not_replaced(self) -> None:
        executor = ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn")
        )
        try:
            async with SolverRuntime(executor=executor) as runtime:
                with pytest.raises(BrokenProcessPool):
                    await runtime.run_cpu(workers.die)
                with pytest.raises(BrokenProcessPool):
                    await runtime.run_cpu(workers.square, 1)
        finally:
            executor.shutdown(wait=True)


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

    async def test_replaces_an_unpicklable_exception(self) -> None:
        with pytest.raises(RuntimeError, match="UnpicklableError: odd"):
            run_in_worker(workers.raise_unpicklable, ())
