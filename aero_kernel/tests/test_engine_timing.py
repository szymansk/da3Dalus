"""The measured run time of every quantity in the engine result (ARCHITECTURE ch. 8.3, 8.13).

The stub formulas sleep, so a measured time is never below what they slept: the tests assert those
floors and the exact relations between the quantities of one call, never an upper wall-clock limit.
"""

import asyncio
import math
from collections.abc import Mapping

import pytest
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.schema import ComputeRequest, ComputeResult, QuantityResult, QuantityStatus, Timing
from aero_kernel.tests.engine_builders import (
    NO_SOLVERS,
    Impl,
    aircraft,
    make_build,
    num,
    registry_with,
)

pytestmark = [pytest.mark.asyncio, pytest.mark.usefixtures("pending_horizontal_tail")]

WEIGHT_S = 0.03
DOUBLE_S = 0.02


def close(actual: float | tuple[float, ...], expected: float | tuple[float, ...]) -> bool:
    """Whether two times or tuples of times agree up to rounding."""
    a = actual if isinstance(actual, tuple) else (actual,)
    e = expected if isinstance(expected, tuple) else (expected,)
    return len(a) == len(e) and all(
        math.isclose(x, y, abs_tol=1e-12) for x, y in zip(a, e, strict=True)
    )


def sleeping(seconds: float, impl: Impl) -> Impl:
    async def slow(x: Inputs, ctx: Context) -> Mapping[str, object]:
        await asyncio.sleep(seconds)
        return await impl(x, ctx)

    return slow


async def _weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"w": num(x, "m") * num(x, "g")}


async def _double(x: Inputs, ctx: Context) -> Mapping[str, object]:
    return {"d": 2 * num(x, "w")}


SLOW = {"weight": sleeping(WEIGHT_S, _weight), "double": sleeping(DOUBLE_S, _double)}


async def run(*slugs: str, budget: float | None = None) -> dict[str, QuantityResult]:
    result: ComputeResult = await evaluate(
        make_build(registry_with(SLOW)),
        aircraft(),
        ComputeRequest(quantities=slugs, time_budget_s=budget),
        solvers=NO_SOLVERS,
    )
    return {q.slug: q for q in result.quantities}


def timing_of(quantity: QuantityResult) -> Timing:
    assert quantity.timing is not None
    return quantity.timing


async def test_a_quantity_without_predecessors_has_only_its_own_time() -> None:
    timing = timing_of((await run("weight"))["weight"])
    assert timing.own_s.lower >= WEIGHT_S
    assert close(timing.own_s.lower, timing.own_s.upper)
    assert close((timing.before_s.lower, timing.before_s.upper), (0.0, 0.0))
    assert close(timing.total_s.upper, timing.own_s.upper)


async def test_the_time_before_a_quantity_is_the_own_time_of_its_upstream_nodes() -> None:
    quantities = await run("weight", "double-weight")
    weight, double = timing_of(quantities["weight"]), timing_of(quantities["double-weight"])
    assert double.own_s.lower >= DOUBLE_S
    assert close(double.before_s.lower, weight.own_s.lower)
    assert close(double.before_s.upper, weight.own_s.upper)
    assert close(double.total_s.lower, weight.own_s.lower + double.own_s.lower)


async def test_a_quantity_that_did_not_compute_its_formula_has_no_timing() -> None:
    quantities = await run("roll-q", "unknown-q")  # roll-q: condition not met
    assert quantities["roll-q"].status is QuantityStatus.NOT_APPLICABLE
    assert quantities["roll-q"].timing is None
    assert quantities["unknown-q"].status is QuantityStatus.ERROR
    assert quantities["unknown-q"].timing is None  # rejected by the graph, nothing ran


async def test_a_failed_quantity_reports_the_time_spent_until_it_failed() -> None:
    quantity = (await run("err-missing-q"))["err-missing-q"]
    assert quantity.status is QuantityStatus.ERROR
    assert timing_of(quantity).before_s.lower >= WEIGHT_S


async def test_a_quantity_open_when_the_budget_expired_has_no_timing() -> None:
    quantities = await run("weight", "double-weight", budget=WEIGHT_S + DOUBLE_S / 4)
    assert quantities["weight"].timing is not None
    double = quantities["double-weight"]
    assert double.error is not None
    assert double.error.code == "timeout"
    assert double.timing is None
