"""The stateful facade ``CachedKernel`` (ARCHITECTURE ch. 8.4, #1332) on a fixture build with stubs."""

import asyncio
import struct
from collections import Counter
from collections.abc import Mapping

import pytest
from aero_kernel import CachedKernel, compute
from aero_kernel import api as api_module
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityResult
from aero_kernel.tests.engine_builders import Impl, aircraft, make_build, num, registry_with

pytestmark = pytest.mark.asyncio

RUN_S = 0.05


class Calls:
    """Counts the calls of the stub formulas by slug."""

    def __init__(self) -> None:
        self.count: Counter[str] = Counter()

    def counted(self, slug: str, impl: Impl) -> Impl:
        async def stub(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.count[slug] += 1
            return await impl(x, ctx)

        return stub


async def _weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
    await asyncio.sleep(RUN_S)
    return {"w": num(x, "m") * num(x, "g")}


async def _gravity(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"r": num(x, "g")}


async def _warns(x: Inputs, ctx: Context) -> Mapping[str, object]:
    ctx.warn("hinge_line_averaged", "averaged", {"n": 1.0})
    return {"r": num(x, "m")}


async def _fails_slowly(x: Inputs, ctx: Context) -> Mapping[str, object]:
    await asyncio.sleep(RUN_S)
    raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "no convergence", "retry")


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Calls:
    """Make the fixture build with counting stubs the shipped one."""
    counter = Calls()
    stubs = {
        "weight": _weight,
        "gravity-only": _gravity,
        "independent": _warns,
        "fail-density": _fails_slowly,
    }
    build = make_build(
        registry_with({slug: counter.counted(slug, impl) for slug, impl in stubs.items()})
    )
    monkeypatch.setattr(api_module, "shipped_build", lambda: build)
    return counter


def only(result: ComputeResult) -> QuantityResult:
    (quantity,) = result.quantities
    return quantity


def bits(value: float | None) -> bytes:
    assert value is not None
    return struct.pack("<d", value)


async def call(kernel: CachedKernel, slug: str) -> QuantityResult:
    return only(await kernel.compute(aircraft(), ComputeRequest(quantities=(slug,))))


async def test_the_second_identical_call_is_served_from_the_cache(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=16)
    first, second = await call(kernel, "weight"), await call(kernel, "weight")
    assert (first.from_cache, second.from_cache) == (False, True)
    assert bits(second.value) == bits(first.value)
    assert calls.count["weight"] == 1


async def test_the_stateless_compute_beside_it_never_uses_the_cache(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=16)
    await call(kernel, "weight")
    fresh = only(await compute(aircraft(), ComputeRequest(quantities=("weight",))))
    assert not fresh.from_cache
    assert calls.count["weight"] == 2


async def test_two_concurrent_identical_calls_run_the_node_once(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=16)
    first, second = await asyncio.gather(call(kernel, "weight"), call(kernel, "weight"))
    assert calls.count["weight"] == 1
    assert bits(first.value) == bits(second.value)
    assert sorted([first.from_cache, second.from_cache]) == [False, True]


async def test_waiters_of_a_failed_run_compute_it_themselves(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=16)
    first, second = await asyncio.gather(
        call(kernel, "fail-density-q"), call(kernel, "fail-density-q")
    )
    assert calls.count["fail-density"] == 2
    for quantity in (first, second):
        assert quantity.error is not None
        assert quantity.error.code == "not_converged"
        assert not quantity.from_cache


async def test_a_hit_is_a_fresh_object(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=16)
    await call(kernel, "independent-q")
    hit = await call(kernel, "independent-q")
    hit.warnings[0].detail["n"] = 99.0  # frozen stops assignment, not a dict's mutation
    again = await call(kernel, "independent-q")
    assert again.from_cache
    assert again.warnings[0].model_dump_json() != hit.warnings[0].model_dump_json()
    assert again.warnings[0].detail == {"n": 1.0}


async def test_the_least_recently_used_node_is_evicted(calls: Calls) -> None:
    kernel = CachedKernel(max_entries=1)
    await call(kernel, "weight")
    await call(kernel, "gravity-only-q")  # the one entry is now gravity-only
    again = await call(kernel, "weight")
    assert not again.from_cache
    assert calls.count["weight"] == 2
    assert (await call(kernel, "weight")).from_cache


async def test_the_size_is_given_at_construction_and_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        CachedKernel(max_entries=0)
