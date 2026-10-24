"""stall-break: the crossing helper, the formula with its resolution check, and the engine (fast tier)."""

import math
from collections.abc import Sequence
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.stall_break import RESOLUTION_TOLERANCE_DEG, stall_break
from aero_kernel.schema import ComputeRequest, FlowConditions, Polar, QuantityStatus
from aero_kernel.solvers.opti import ALPHA_MAX_DEG, ALPHA_STEP_DEG
from aero_kernel.solvers.stall_math import first_crossing_below
from aero_kernel.tests.formula_builders import StubAtmosphere, close, context_with, solvers_with
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, StubOpti, lift_curve, lift_curve_at
from aero_kernel.tests.test_formulas import stall_x
from aero_kernel.tests.test_stall_speed_engine import RHO, aircraft

pytestmark = pytest.mark.asyncio

ALPHA_S, CL_MAX = UPRIGHT_PEAK
FRACTION = 0.10
# Hand values of the stub curve (0.2 per degree down from the peak): C_L = 0.9 * 1.19 = 1.071 at
# 15.75 + (1.19 - 1.071) / 0.2 = 16.345 deg, a width of 0.595 deg.
ALPHA_BREAK, WIDTH = 16.345, 0.595
# The flow the stub polar was computed at (the stall_x air state and a stall speed of 10 m/s).
FLOW = FlowConditions(v_ms=10.0, density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)


def break_x(polar: Polar | None = None, **change: object) -> dict[str, Any]:
    """``x`` of stall-break: the stall-speed stub's polar at its peak, f = 0.10, the trainer wing."""
    given = polar or lift_curve(UPRIGHT_PEAK, upright=True)
    x: dict[str, Any] = {
        "airplane": stall_x()["airplane"],
        "polar_s": given if given.conditions else given.model_copy(update={"conditions": FLOW}),
        "alpha_s": ALPHA_S,
        "cl_max": CL_MAX,
        "f": FRACTION,
    }
    x.update(change)
    return x


def curve(points: Sequence[tuple[float, float]]) -> Polar:
    """A polar through the (alpha, C_L) points."""
    return Polar(
        alpha_deg=tuple(a for a, _ in points),
        cl=tuple(c for _, c in points),
        cd=(0.05,) * len(points),
        cm=(0.0,) * len(points),
    )


# --- the crossing helper ---------------------------------------------------------------------


async def test_the_crossing_is_interpolated_linearly_between_the_bracketing_samples() -> None:
    # 1.0 at 10 deg falls to 0.8 at 12 deg; the level 0.9 is crossed at 11 deg
    crossing = first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.95, 0.8], 10.0, 0.9)
    assert close(crossing, 11.0 + (0.95 - 0.9) / (0.95 - 0.8), 1e-12)


async def test_a_sample_exactly_on_the_level_is_the_crossing() -> None:
    assert close(first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.9, 0.8], 10.0, 0.9), 11.0, 1e-12)


async def test_the_first_crossing_wins_on_a_non_monotonic_branch() -> None:
    """The lift falls below the level, rebounds above it and falls again: the first fall counts."""
    alphas = [10.0, 11.0, 12.0, 13.0, 14.0]
    cl = [1.0, 0.95, 0.85, 0.95, 0.8]
    assert close(first_crossing_below(alphas, cl, 10.0, 0.9), 11.5, 1e-12)


async def test_the_scan_starts_at_the_sample_of_the_stall_angle() -> None:
    """A sample below the level before alpha_S (the other side of the peak) is not a crossing."""
    alphas = [8.0, 9.0, 10.0, 11.0, 12.0]
    cl = [0.5, 0.95, 1.0, 0.95, 0.8]
    assert close(first_crossing_below(alphas, cl, 10.0, 0.9), 11.0 + 0.05 / 0.15, 1e-12)


async def test_a_branch_that_never_falls_to_the_level_has_no_crossing() -> None:
    assert first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.99, 0.95], 10.0, 0.9) is None


async def test_an_alpha_s_that_is_no_sample_has_no_crossing() -> None:
    assert first_crossing_below([10.0, 11.0, 12.0], [1.0, 0.95, 0.8], 10.5, 0.9) is None


# --- the formula ------------------------------------------------------------------------------


async def test_the_break_is_where_the_lift_has_fallen_by_the_fraction() -> None:
    stub = StubOpti()
    result = await stall_break(break_x(), context_with(StubAtmosphere({}), opti=stub))
    assert set(result) == {"alpha_break", "width"}
    assert close(result["alpha_break"], ALPHA_BREAK, 1e-12)
    assert close(result["width"], WIDTH, 1e-12)


async def test_the_half_step_sweep_runs_from_alpha_s_to_the_end_of_the_range() -> None:
    stub = StubOpti()
    x = break_x()
    await stall_break(x, context_with(StubAtmosphere({}), opti=stub))
    ((plane, air, speed, alphas),) = stub.sweep_calls
    assert plane is x["airplane"]
    assert (air.density, air.dynamic_viscosity, air.speed_of_sound) == (1.225, 1.7894e-5, 340.294)
    assert speed == FLOW.v_ms
    assert alphas[0] == ALPHA_S
    assert alphas[-1] == ALPHA_MAX_DEG
    steps = {round(b - a, 9) for a, b in pairwise(alphas)}
    assert max(steps) <= ALPHA_STEP_DEG / 2 + 1e-9


async def test_a_non_monotonic_post_peak_curve_gives_the_first_crossing() -> None:
    points = [(10.0, 0.5), (14.0, 1.0), (15.0, 0.95), (16.0, 0.85), (17.0, 0.95), (25.0, 0.4)]
    polar = curve(points)
    stub = StubOpti()
    stub.sweep_answer = lambda alphas: _interpolated(polar, alphas)
    x = break_x(polar, alpha_s=14.0, cl_max=1.0)
    context = context_with(StubAtmosphere({}), opti=stub)
    result = await stall_break(x, context)
    assert close(result["alpha_break"], 15.5, 1e-12)
    assert close(result["width"], 1.5, 1e-12)
    assert context.warnings == ()


def _interpolated(polar: Polar, alphas: Sequence[float]) -> Polar:
    import numpy as np

    cl = [float(np.interp(a, polar.alpha_deg, polar.cl)) for a in alphas]
    return Polar(alpha_deg=tuple(alphas), cl=tuple(cl), cd=(0.05,) * len(cl), cm=(0.0,) * len(cl))


async def test_a_polar_that_never_falls_to_the_level_gives_no_value_and_runs_no_sweep() -> None:
    flat = lift_curve_at((ALPHA_S, CL_MAX), True, [14.0, 15.0, 15.75, 16.0, 25.0])
    flat = Polar(
        alpha_deg=flat.alpha_deg, cl=(1.0, 1.1, CL_MAX, 1.18, 1.17), cd=flat.cd, cm=flat.cm
    )
    stub = StubOpti()
    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(flat), context_with(StubAtmosphere({}), opti=stub))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail["alpha_s"] == ALPHA_S
    assert stub.sweep_calls == []


async def test_a_half_step_sweep_that_agrees_within_one_step_is_silent() -> None:
    """A shift of 0.2 deg is below the tolerance of one published step (0.25 deg)."""
    stub = StubOpti()
    stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S + 0.2, CL_MAX), True, alphas)
    context = context_with(StubAtmosphere({}), opti=stub)
    await stall_break(break_x(), context)
    assert context.warnings == ()


async def test_a_half_step_sweep_that_disagrees_is_a_declared_defect_with_both_values() -> None:
    stub = StubOpti()
    # the finer sweep puts the peak 0.4 deg further out, so its crossing is 0.4 deg further out
    stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S + 0.4, CL_MAX), True, alphas)
    context = context_with(StubAtmosphere({}), opti=stub, origin="alpha-break")
    result = await stall_break(break_x(), context)
    (warning,) = context.warnings
    assert warning.code == "stall_break_resolution"
    assert warning.severity.value == "defect"
    assert warning.origin == "alpha-break"
    assert close(float(str(warning.detail["alpha_break_published_deg"])), ALPHA_BREAK, 1e-12)
    assert close(float(str(warning.detail["alpha_break_half_step_deg"])), ALPHA_BREAK + 0.4, 1e-9)
    assert warning.detail["tolerance_deg"] == RESOLUTION_TOLERANCE_DEG
    assert close(result["alpha_break"], ALPHA_BREAK, 1e-12)  # the published sweep's value stands


async def test_the_tolerance_is_one_step_of_the_published_sweep() -> None:
    """Below the sample spacing the interpolation cannot be trusted; fixed before measuring."""
    assert RESOLUTION_TOLERANCE_DEG == ALPHA_STEP_DEG == 0.25


async def test_a_finer_sweep_that_does_not_bracket_the_break_is_not_converged() -> None:
    """The published sweep found a break, the finer one never falls to the level: an error."""
    stub = StubOpti()
    stub.sweep_answer = lambda alphas: lift_curve_at((ALPHA_S, CL_MAX), True, alphas).model_copy(
        update={"cl": (CL_MAX,) * len(alphas)}
    )
    context = context_with(StubAtmosphere({}), opti=stub)
    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(), context)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert close(float(str(raised.value.detail["alpha_break_published_deg"])), ALPHA_BREAK, 1e-12)
    assert context.warnings == ()


async def test_a_polar_without_flow_conditions_is_invalid_input() -> None:
    bare = lift_curve(UPRIGHT_PEAK, upright=True)
    x = break_x()
    x["polar_s"] = bare
    with pytest.raises(FormulaError) as raised:
        await stall_break(x, context_with(StubAtmosphere({}), opti=StubOpti()))
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_failed_half_step_sweep_is_passed_on_without_a_value() -> None:
    class Failing(StubOpti):
        async def sweep(self, *args: Any) -> Polar:  # type: ignore[override]
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "m", "h")

    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(), context_with(StubAtmosphere({}), opti=Failing()))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


@pytest.mark.parametrize("fraction", [0.0, 1.0, -0.1, 1.5, math.nan])
async def test_a_fraction_outside_zero_and_one_is_invalid_input(fraction: float) -> None:
    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(f=fraction), context_with(StubAtmosphere({}), opti=StubOpti()))
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_non_positive_peak_is_invalid_input() -> None:
    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(cl_max=0.0), context_with(StubAtmosphere({}), opti=StubOpti()))
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_an_alpha_s_that_is_no_sample_of_the_polar_is_invalid_input() -> None:
    with pytest.raises(FormulaError) as raised:
        await stall_break(break_x(alpha_s=15.8), context_with(StubAtmosphere({}), opti=StubOpti()))
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_polar_that_is_not_a_polar_is_a_type_error() -> None:
    with pytest.raises(TypeError, match="polar_s"):
        await stall_break(break_x(polar_s=1.0), context_with(StubAtmosphere({}), opti=StubOpti()))


# --- through the engine on the shipped canon --------------------------------------------------


async def run(stub: StubOpti | None = None) -> Any:
    opti = stub or StubOpti()
    solvers = solvers_with(atmosphere=StubAtmosphere({0.0: RHO}), opti=opti)
    request = ComputeRequest(quantities=("alpha-break", "stall-break-width"))
    return await evaluate(shipped_build(), aircraft(), request, solvers=solvers), opti


async def test_the_break_comes_out_of_the_shipped_canon() -> None:
    result, opti = await run()
    quantities = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in quantities.values()), result
    assert close(quantities["alpha-break"].value, ALPHA_BREAK, 1e-12)
    assert close(quantities["stall-break-width"].value, WIDTH, 1e-12)
    assert quantities["alpha-break"].unit == "deg"
    assert len(opti.calls) == 1  # the stall problem is solved once for all its outputs
    assert len(opti.sweep_calls) == 1


async def test_the_convention_f_is_a_default_of_the_provenance() -> None:
    result, _ = await run()
    used = {d.slug: d for d in result.provenance.defaults_used}
    assert used["stall-break-fraction"].value == FRACTION


async def test_a_failed_stall_leaves_the_break_without_a_value() -> None:
    class Failing(StubOpti):
        async def stall(self, *args: Any) -> Any:  # type: ignore[override]
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "m", "h")

    result, opti = await run(Failing())
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
    assert opti.sweep_calls == []
