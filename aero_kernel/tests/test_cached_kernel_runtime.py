"""``CachedKernel`` owns one solver runtime for its lifetime; ``compute`` one per call (ch. 8.10, #1336)."""

from collections.abc import Mapping

import pytest
from aero_kernel import CachedKernel, compute
from aero_kernel import api as api_module
from aero_kernel.context import Context, Inputs
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import ComputeRequest
from aero_kernel.tests.engine_builders import aircraft, make_build, num, registry_with

pytestmark = pytest.mark.asyncio

REQUEST = ComputeRequest(quantities=("weight",))


class RecordingRuntime(SolverRuntime):
    """A runtime that records its settings and whether it was closed."""

    made: list["RecordingRuntime"]

    def __init__(
        self,
        *,
        max_workers: int | None = None,
        max_concurrency: int | None = None,
        max_models_per_worker: int = 2,
    ) -> None:
        super().__init__(
            max_workers=max_workers,
            max_concurrency=max_concurrency,
            max_models_per_worker=max_models_per_worker,
        )
        self.settings = (max_workers, max_concurrency, max_models_per_worker)
        self.closed = False
        RecordingRuntime.made.append(self)

    async def aclose(self) -> None:
        self.closed = True
        await super().aclose()


async def _weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"w": num(x, "m") * num(x, "g")}


@pytest.fixture
def runtimes(monkeypatch: pytest.MonkeyPatch) -> list[RecordingRuntime]:
    """Record every runtime the API creates, on a fixture build with a stub formula."""
    build = make_build(registry_with({"weight": _weight}))
    monkeypatch.setattr(api_module, "shipped_build", lambda: build)
    made: list[RecordingRuntime] = []
    monkeypatch.setattr(RecordingRuntime, "made", made, raising=False)
    monkeypatch.setattr(api_module, "SolverRuntime", RecordingRuntime)
    return made


async def test_the_facade_reuses_one_runtime_across_calls(runtimes: list[RecordingRuntime]) -> None:
    kernel = CachedKernel(max_entries=4)
    await kernel.compute(aircraft(), REQUEST)
    await kernel.compute(aircraft(), ComputeRequest(quantities=("weight",), include_long_runs=True))
    (runtime,) = runtimes
    assert not runtime.closed
    await kernel.aclose()
    assert runtime.closed


async def test_no_runtime_is_made_before_the_first_compute(
    runtimes: list[RecordingRuntime],
) -> None:
    kernel = CachedKernel(max_entries=4)
    assert runtimes == []
    await kernel.aclose()
    assert runtimes == []


async def test_the_settings_are_passed_to_the_runtime(runtimes: list[RecordingRuntime]) -> None:
    async with CachedKernel(
        max_entries=4, max_models_per_worker=3, max_workers=2, max_concurrency=5
    ) as kernel:
        await kernel.compute(aircraft(), REQUEST)
    (runtime,) = runtimes
    assert runtime.settings == (2, 5, 3)
    assert runtime.closed


async def test_a_closed_facade_refuses_work(runtimes: list[RecordingRuntime]) -> None:
    kernel = CachedKernel(max_entries=4)
    await kernel.compute(aircraft(), REQUEST)
    await kernel.aclose()
    await kernel.aclose()  # idempotent
    plane = aircraft()
    with pytest.raises(RuntimeError, match="closed"):
        await kernel.compute(plane, REQUEST)
    assert len(runtimes) == 1


async def test_the_stateless_compute_owns_and_closes_one_runtime_per_call(
    runtimes: list[RecordingRuntime],
) -> None:
    await compute(aircraft(), REQUEST)
    await compute(aircraft(), REQUEST)
    assert len(runtimes) == 2
    assert all(runtime.closed for runtime in runtimes)


async def test_the_default_keeps_two_model_functions_per_worker(
    runtimes: list[RecordingRuntime],
) -> None:
    async with CachedKernel(max_entries=4) as kernel:
        await kernel.compute(aircraft(), REQUEST)
    (runtime,) = runtimes
    assert runtime.settings == (None, None, 2)


@pytest.mark.parametrize("keyword", ["max_models_per_worker", "max_workers", "max_concurrency"])
async def test_a_bound_below_one_is_refused_at_construction(keyword: str) -> None:
    with pytest.raises(ValueError, match=keyword):
        CachedKernel(max_entries=4, **{keyword: 0})
