"""Worker slots of the solver runtime: model-affinity routing and the worker-side model cache (ch. 8.10, #1336)."""

import asyncio
import logging

import pytest
from aero_kernel.runtime import RoutedRequest, SolverRuntime
from aero_kernel.solvers.aero_model import installed_model_cache
from aero_kernel.tests import runtime_workers as workers
from aero_kernel.tests.runtime_workers import KeyedJob

pytestmark = pytest.mark.asyncio(loop_scope="function")

BOUND_S = 30.0


async def pid(runtime: SolverRuntime, key: str | None, seconds: float = 0.0) -> int:
    async with asyncio.timeout(BOUND_S):
        return await runtime.run_cpu(workers.pid_of, KeyedJob(model_key=key, seconds=seconds))


async def test_a_request_with_a_model_key_is_a_routed_request() -> None:
    assert isinstance(KeyedJob(model_key="a"), RoutedRequest)
    assert not isinstance(object(), RoutedRequest)


async def test_a_repeated_key_goes_to_the_worker_that_holds_it() -> None:
    """One function per worker: A and B take two workers, and each comes back to its own."""
    async with SolverRuntime(max_workers=3, max_models_per_worker=1) as runtime:
        first_a, first_b = await pid(runtime, "A"), await pid(runtime, "B")
        assert first_a != first_b
        assert await pid(runtime, "A") == first_a
        assert await pid(runtime, "B") == first_b


async def test_a_new_key_takes_a_worker_with_room_before_a_new_one() -> None:
    """Two functions per worker: A and B share the running worker, nothing new is spawned."""
    async with SolverRuntime(max_workers=3, max_models_per_worker=2) as runtime:
        assert await pid(runtime, "A") == await pid(runtime, "B") == await pid(runtime, "A")


async def test_with_every_worker_full_a_miss_replaces_the_least_recently_used_worker() -> None:
    """A, B, C fill three one-function workers; D evicts the oldest (A's), so A then moves on."""
    async with SolverRuntime(max_workers=3, max_models_per_worker=1) as runtime:
        a, b, c = await pid(runtime, "A"), await pid(runtime, "B"), await pid(runtime, "C")
        assert len({a, b, c}) == 3
        assert await pid(runtime, "D") == a  # a's worker was used least recently
        assert await pid(runtime, "A") == b  # A is gone from a; b is now the least recent
        assert await pid(runtime, "D") == a  # D stayed where it was built
        assert await pid(runtime, "C") == c


async def test_a_job_without_a_key_takes_any_idle_worker() -> None:
    async with SolverRuntime(max_workers=2, max_models_per_worker=1) as runtime:
        holder = await pid(runtime, "A")
        busy = asyncio.create_task(pid(runtime, "A", seconds=1.0))
        await asyncio.sleep(0.2)
        assert await pid(runtime, None) != holder  # the holder is busy: no wait for it
        assert await busy == holder


async def test_a_key_whose_worker_is_busy_is_built_again_elsewhere_not_waited_for() -> None:
    """Routing is a guess: a busy holder costs a second build, never a wait or a value."""
    async with SolverRuntime(max_workers=2, max_models_per_worker=1) as runtime:
        holder = await pid(runtime, "A")
        busy = asyncio.create_task(pid(runtime, "A", seconds=1.0))
        await asyncio.sleep(0.2)
        assert await pid(runtime, "A") != holder
        await busy


async def test_the_worker_is_reused_after_a_cancelled_call() -> None:
    """Cancelling a caller discards its result; the worker finishes and then takes the next job.

    The worker is not replaced, so its model functions survive a cancelled call.
    """
    async with SolverRuntime(max_workers=1) as runtime:
        worker = await pid(runtime, "A")
        running = asyncio.create_task(pid(runtime, "A", seconds=0.6))
        await asyncio.sleep(0.2)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        assert await pid(runtime, "A") == worker


async def test_a_cancelled_call_keeps_its_worker_from_new_jobs_until_it_ends() -> None:
    """The next job waits for an idle worker instead of queuing behind the abandoned one."""
    async with SolverRuntime(max_workers=2, max_concurrency=1) as runtime:
        worker = await pid(runtime, "A")
        running = asyncio.create_task(pid(runtime, "A", seconds=6.0))
        await asyncio.sleep(0.3)
        running.cancel()
        with pytest.raises(asyncio.CancelledError):
            await running
        async with asyncio.timeout(4.0):  # less than the 5.7 s the abandoned job still runs
            assert await pid(runtime, "A") != worker


async def test_a_dead_worker_discards_only_its_own_slot(caplog: pytest.LogCaptureFixture) -> None:
    async with SolverRuntime(max_workers=2, max_models_per_worker=1) as runtime:
        a, b = await pid(runtime, "A"), await pid(runtime, "B")
        with (
            caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"),
            pytest.raises(Exception, match="terminated abruptly"),
        ):
            await runtime.run_cpu(workers.die_keyed, KeyedJob(model_key="B"))
        assert any(r.levelno == logging.WARNING for r in caplog.records)
        assert await pid(runtime, "A") == a  # the other worker and its functions stay
        assert await pid(runtime, "B") not in {a, b}  # a fresh worker for the dead one


def died_warnings(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.levelno == logging.WARNING and "died" in r.getMessage()]


async def test_a_worker_that_dies_after_its_caller_left_is_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A cancelled caller no longer awaits the job; the dead worker is still logged (ch. 8.10)."""
    async with SolverRuntime(max_workers=1, max_models_per_worker=1) as runtime:
        with caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"):
            running = asyncio.create_task(runtime.run_cpu(workers.die_after, 0.5))
            await asyncio.sleep(0.2)
            running.cancel()
            with pytest.raises(asyncio.CancelledError):
                await running
            async with asyncio.timeout(BOUND_S):
                assert await runtime.run_cpu(workers.square, 3) == 9  # waits for the dead slot
        assert len(died_warnings(caplog)) == 1


async def test_a_worker_that_dies_while_its_caller_waits_is_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async with SolverRuntime(max_workers=1, max_models_per_worker=1) as runtime:
        with (
            caplog.at_level(logging.WARNING, logger="aero_kernel.runtime"),
            pytest.raises(Exception, match="terminated abruptly"),
        ):
            await runtime.run_cpu(workers.die)
        assert len(died_warnings(caplog)) == 1


async def test_the_worker_installs_a_bounded_model_cache_and_the_parent_none() -> None:
    async with SolverRuntime(max_workers=1, max_models_per_worker=2) as runtime:
        held: list[tuple[int, bool, tuple[str, ...]]] = []
        for key in ("A", "B", "A", "C"):
            held.append(await runtime.run_cpu(workers.touch_model, KeyedJob(model_key=key)))
    assert [hit for _, hit, _ in held] == [False, False, True, False]
    assert held[-1][2] == ("A", "C")  # B was the least recently used
    assert len({worker for worker, _, _ in held}) == 1
    assert installed_model_cache() is None


@pytest.mark.parametrize("keyword", ["max_models_per_worker", "max_workers", "max_concurrency"])
async def test_a_bound_below_one_is_refused(keyword: str) -> None:
    with pytest.raises(ValueError, match=keyword):
        SolverRuntime(**{keyword: 0})


async def test_closing_shuts_every_worker_down_and_refuses_work() -> None:
    import multiprocessing

    before = multiprocessing.active_children()
    runtime = SolverRuntime(max_workers=2, max_models_per_worker=1)
    await asyncio.gather(pid(runtime, "A", 0.3), pid(runtime, "B", 0.3))
    assert len(multiprocessing.active_children()) >= len(before) + 2
    await runtime.aclose()
    assert multiprocessing.active_children() == before
    with pytest.raises(RuntimeError, match="closed"):
        await pid(runtime, "A")
