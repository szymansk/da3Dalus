"""lift-to-drag-ratio: E = L / D, with the precondition drag_positive (on_violation: error).

Fast tier: hand values, the precondition on its own, and the chain through the engine on the shipped
canon with the stub optimiser's AeroBuildup forces.
"""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import ErrorCategory
from aero_kernel.formulas.lift_to_drag_ratio import drag_positive, lift_to_drag_ratio
from aero_kernel.schema import QuantityStatus
from aero_kernel.solvers.opti import Forces
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.stall_stubs import DRAG_N, LIFT_N, StubOpti
from aero_kernel.tests.test_aerobuildup_evaluation import POINT
from aero_kernel.tests.test_stall_speed_engine import run

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model


async def test_the_ratio_is_lift_over_drag() -> None:
    """Hand value: E = 14.7 N / 0.98 N = 15.0."""
    x = inputs_from_model(MODEL, "lift-to-drag-ratio", {"lift-force": 14.7, "drag-force": 0.98})
    result = await lift_to_drag_ratio(x, context_with(StubAtmosphere({})))
    assert set(result) == {"e"}
    assert close(result["e"], 15.0, 1e-12)


@pytest.mark.parametrize(
    ("drag", "state"),
    [
        (0.98, "held"),
        (1e-12, "held"),
        (0.0, "violated"),
        (-0.2, "violated"),
        (math.nan, "violated"),
    ],
)
async def test_the_drag_must_be_greater_than_zero(drag: float, state: str) -> None:
    result = drag_positive({"l": 14.7, "d": drag})
    assert result.state == state
    assert "drag" in result.message


async def test_the_glide_ratio_of_the_callers_point_through_the_engine() -> None:
    result, opti = await run("lift-to-drag-ratio", values=POINT)
    (quantity,) = result.quantities
    assert quantity.status is QuantityStatus.OK, result
    assert close(quantity.value, LIFT_N / DRAG_N, 1e-12)
    assert (quantity.unit, quantity.tool) == ("1", "APP")
    assert len(opti.evaluate_calls) == 1


@pytest.mark.parametrize("drag", [0.0, -0.05], ids=["zero", "negative"])
async def test_a_drag_not_above_zero_is_the_declared_error_never_a_value(drag: float) -> None:
    """ADR 0020: an infinite or negative glide ratio is never returned or substituted."""
    stub = StubOpti()
    stub.forces = Forces(lift_n=LIFT_N, drag_n=drag)
    result, _ = await run("lift-to-drag-ratio", stub=stub, values=POINT)
    (quantity,) = result.quantities
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.value is None
    assert quantity.error is not None
    assert quantity.error.code == "precondition_violated"
    assert quantity.error.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert quantity.error.formula == "lift-to-drag-ratio"
    assert quantity.error.detail["precondition"] == "drag_positive"
