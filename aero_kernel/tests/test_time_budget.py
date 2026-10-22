"""The per-request time budget (ARCHITECTURE ch. 8.10, 8.1)."""

import asyncio
import time
from collections.abc import Mapping

import pytest
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import (
    NO_SOLVERS,
    aircraft,
    make_build,
    registry_with,
)

pytestmark = pytest.mark.asyncio


class Slow:
    """A stub `weight` that waits, records that it started and whether it was cancelled."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.started = False
        self.cancelled = False

    async def implementation(self, x: Inputs, ctx: Context) -> Mapping[str, object]:
        self.started = True
        try:
            await asyncio.sleep(self.seconds)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return {"w": 1.0}


async def run(slow: Slow, *slugs: str, budget: float | None) -> ComputeResult:
    request = ComputeRequest(quantities=slugs, time_budget_s=budget)
    build = make_build(registry_with({"weight": slow.implementation}))
    return await evaluate(build, aircraft(), request, solvers=NO_SOLVERS)


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


async def test_the_budget_is_optional_and_defaults_to_none() -> None:
    assert ComputeRequest(quantities=("weight",)).time_budget_s is None
    assert ComputeRequest(quantities=("weight",), time_budget_s=2.5).time_budget_s == 2.5


async def test_without_a_budget_a_slow_node_finishes() -> None:
    result = await run(Slow(0.05), "weight", "independent-q", budget=None)
    assert all(q.status is QuantityStatus.OK for q in result.quantities)


async def test_a_budget_that_is_enough_changes_nothing() -> None:
    result = await run(Slow(0.01), "weight", "double-weight", budget=5.0)
    assert all(q.status is QuantityStatus.OK for q in result.quantities)


async def test_an_expired_budget_gives_timeout_for_the_open_quantity_and_returns_the_finished() -> (
    None
):
    slow = Slow(30.0)
    started = time.perf_counter()
    result = await run(slow, "weight", "independent-q", budget=0.1)
    assert time.perf_counter() - started < 5.0
    quantities = by_slug(result)
    assert quantities["independent-q"].status is QuantityStatus.OK
    error = quantities["weight"].error
    assert quantities["weight"].status is QuantityStatus.ERROR
    assert error is not None
    assert (error.category, error.code) == (ErrorCategory.TIMEOUT, "timeout")
    assert (error.quantity, error.retryable) == ("weight", True)
    assert "0.1" in error.message
    assert slow.started
    assert slow.cancelled


async def test_a_quantity_that_waits_for_the_open_one_is_open_too() -> None:
    result = await run(Slow(30.0), "weight", "double-weight", budget=0.1)
    quantities = by_slug(result)
    for slug in ("weight", "double-weight"):
        error = quantities[slug].error
        assert error is not None
        assert (error.category, error.quantity) == (ErrorCategory.TIMEOUT, slug)


async def test_a_finished_layer_before_the_expiry_keeps_its_values() -> None:
    """`independent-q` has no predecessor; `double-weight` waits for the slow `weight`."""
    result = await run(Slow(30.0), "independent-q", "double-weight", budget=0.1)
    quantities = by_slug(result)
    assert quantities["independent-q"].status is QuantityStatus.OK
    assert quantities["independent-q"].value is not None
    assert quantities["double-weight"].status is QuantityStatus.ERROR


@pytest.mark.parametrize("budget", [0.0, -1.0, float("nan"), float("inf")])
async def test_an_inadmissible_budget_is_an_input_error(budget: float) -> None:
    result = await run(Slow(0.0), "weight", budget=budget)
    assert result.quantities == ()
    (error,) = result.input_errors
    assert error.category is ErrorCategory.INVALID_INPUT
    assert error.input_path == "request.time_budget_s"
