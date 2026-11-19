"""spanwise-loads: the formula against hand values, stub adapters (fast tier)."""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Context, Value
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.spanwise_loads import (
    air_density_positive,
    flight_speed_positive,
    spanwise_loads,
)
from aero_kernel.schema import AircraftInput, ComputeRequest, Curve, KernelWarning, QuantityStatus
from aero_kernel.solvers.avl import AvlLoads
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, close, solvers_with
from aero_kernel.tests.np_builders import CONVENTIONAL, StubAvl, airplane_with

pytestmark = pytest.mark.asyncio

MASS, GRAVITY, RHO, SPEED = 1.5, 9.80665, 1.225, 12.0
Q = 0.5 * RHO * SPEED**2


def inputs(**overrides: Value) -> dict[str, Value | None]:
    given: dict[str, Value | None] = {
        "airplane": airplane_with(*CONVENTIONAL),
        "m": MASS,
        "g": GRAVITY,
        "n_load": 1.0,
        "rho": RHO,
        "v": SPEED,
    }
    given.update(overrides)
    return given


def context(avl: StubAvl) -> Context:
    return Context(
        origin="t",
        solvers=solvers_with(atmosphere=StubAtmosphere({}), avl=avl, geometry=StubGeometry()),
    )


async def test_the_curves_are_the_adapters_loads_scaled_by_the_dynamic_pressure() -> None:
    """Hand values: l = q c_cl, V = q Vz/q, M = q Mx/q at the rows the stub gives."""
    out = await spanwise_loads(inputs(), context(StubAvl()))
    assert out["l_y"].x == (0.175, 0.525)
    assert all(close(a, Q * b, 1e-12) for a, b in zip(out["l_y"].y, (0.14, 0.10), strict=True))
    assert out["v_y"].x == out["m_y"].x == (0.0, 0.175, 0.525, 0.7)
    assert all(
        close(a, Q * b, 1e-12) for a, b in zip(out["v_y"].y[:3], (0.05, 0.04, 0.01), strict=True)
    )
    assert out["v_y"].y[3] == 0.0
    assert close(out["m_y"].y[0], Q * 0.012, 1e-12)
    assert all(isinstance(curve, Curve) for curve in out.values())


@pytest.mark.parametrize("n_load", [1.0, -1.0, 2.5, 0.0])
async def test_the_lift_coefficient_is_the_load_over_the_dynamic_pressure_and_the_reference_area(
    n_load: float,
) -> None:
    avl = StubAvl()
    plane = airplane_with(*CONVENTIONAL)
    await spanwise_loads(inputs(n_load=n_load, airplane=plane), context(avl))
    ((asked, cl),) = avl.loads_calls
    assert asked == plane
    area = stand_in_main_wing_properties(plane).s_ref
    assert math.isclose(cl, n_load * MASS * GRAVITY / (Q * area), rel_tol=1e-12, abs_tol=1e-15)


async def test_the_scope_is_declared_and_the_adapters_caveats_are_forwarded() -> None:
    caveat = KernelWarning.of("avl_mesh_not_converged", "mesh", detail={})
    ctx = context(StubAvl(warnings=(caveat,)))
    await spanwise_loads(inputs(), ctx)
    codes = [w.code for w in ctx.warnings]
    assert codes == ["avl_mesh_not_converged", "spanwise_loads_scope"]
    scope = ctx.warnings[1]
    assert scope.severity.value == "notice"
    assert scope.detail["q_pa"] == Q


async def test_an_adapter_error_passes_through_unchanged() -> None:
    avl = StubAvl()
    refusal = FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "unsupported_configuration", "m", "h"
    )
    avl.loads_failure = refusal
    with pytest.raises(FormulaError) as caught:
        await spanwise_loads(inputs(), context(avl))
    assert caught.value is refusal


# --- the preconditions the canon declares ---------------------------------------------------------


@pytest.mark.parametrize("speed", [12.0, 0.5])
async def test_a_positive_speed_and_density_hold_their_preconditions(speed: float) -> None:
    assert flight_speed_positive(inputs(v=speed)).state == "held"
    assert air_density_positive(inputs()).state == "held"


@pytest.mark.parametrize("speed", [0.0, -3.0, math.nan])
async def test_a_speed_that_is_not_positive_violates_its_precondition(speed: float) -> None:
    assert flight_speed_positive(inputs(v=speed)).state == "violated"


@pytest.mark.parametrize("rho", [0.0, -1.0, math.nan])
async def test_a_density_that_is_not_positive_violates_its_precondition(rho: float) -> None:
    assert air_density_positive(inputs(rho=rho)).state == "violated"


# --- the curves are results (gh-1424) ---------------------------------------------------------------

CURVES = {
    "spanwise-lift-distribution": ("N/m", (0.175, 0.525)),
    "spanwise-shear-force": ("N", (0.0, 0.175, 0.525, 0.7)),
    "spanwise-bending-moment": ("N*m", (0.0, 0.175, 0.525, 0.7)),
}


async def curves(avl: StubAvl | None = None, **change: float) -> Any:
    solvers = solvers_with(
        atmosphere=StubAtmosphere({0.0: RHO}), avl=avl or StubAvl(), geometry=StubGeometry()
    )
    values = {"aircraft-mass": MASS, "flight-speed": SPEED, "altitude": 0.0, **change}
    given = AircraftInput(airplane=airplane_with(*CONVENTIONAL), values=values)
    request = ComputeRequest(quantities=tuple(CURVES))
    return await evaluate(shipped_build(), given, request, solvers=solvers)


async def test_each_curve_is_requestable_with_the_canon_abscissa_and_unit() -> None:
    result = await curves()
    assert [q.status for q in result.quantities] == [QuantityStatus.OK] * 3, result
    for quantity in result.quantities:
        unit, stations = CURVES[quantity.slug]
        assert quantity.unit == unit
        assert quantity.curve is not None
        assert (quantity.curve.x_quantity, quantity.curve.x_unit) == ("wing-station", "m")
        assert quantity.curve.x == stations
        assert (quantity.value, quantity.interval) == (None, None)
        assert quantity.tool == "AVL"
        assert [w.code for w in quantity.warnings] == ["spanwise_loads_scope"]


async def test_the_requested_curves_are_the_adapters_rows_scaled_by_the_dynamic_pressure() -> None:
    lift, shear, moment = (await curves()).quantities
    assert lift.curve is not None
    assert shear.curve is not None
    assert moment.curve is not None
    assert all(close(a, Q * b, 1e-12) for a, b in zip(lift.curve.y, (0.14, 0.10), strict=True))
    assert close(shear.curve.y[0], Q * 0.05, 1e-12)
    assert close(moment.curve.y[0], Q * 0.012, 1e-12)
    assert shear.curve.y[-1] == moment.curve.y[-1] == 0.0


async def test_the_load_factor_is_the_callers_and_reaches_the_lift_coefficient() -> None:
    avl = StubAvl()
    await curves(avl, **{"load-factor": 2.5})
    ((_, cl),) = avl.loads_calls
    area = stand_in_main_wing_properties(airplane_with(*CONVENTIONAL)).s_ref
    assert math.isclose(cl, 2.5 * MASS * GRAVITY / (Q * area), rel_tol=1e-9)


async def test_a_speed_of_zero_is_refused_before_any_solve() -> None:
    avl = StubAvl()
    result = await curves(avl, **{"flight-speed": 0.0})
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "precondition_violated"
    assert quantity.error.detail == {"precondition": "flight_speed_positive"}
    assert avl.loads_calls == []


# --- the integration relations, by hand --------------------------------------------------------------


def integral_from_tip(y: tuple[float, ...], f: tuple[float, ...]) -> tuple[float, ...]:
    """Trapezoidal integral of ``f`` from the tip inward, at every ``y`` (hand integration)."""
    out = [0.0]
    for i in range(len(y) - 1, 0, -1):
        out.append(out[-1] + (y[i] - y[i - 1]) * (f[i] + f[i - 1]) / 2.0)
    return tuple(out[::-1])


async def test_scaling_by_the_dynamic_pressure_keeps_shear_as_the_integral_of_the_lift() -> None:
    """A consistent hand set of rows (V and M by hand integration of l): the relations survive the
    scaling of the formula, and a positive load gives a positive shear and moment at the root."""
    y = (0.0, 0.2, 0.5, 0.7)
    lift = (3.8, 3.4, 2.6, 2.0)
    shear = integral_from_tip(y, lift)
    moment = integral_from_tip(y, shear)
    avl = StubAvl()
    avl.loads = AvlLoads(y_strip=y, c_cl=lift, y_station=y, shear=shear, moment=moment)
    out = await spanwise_loads(inputs(), context(avl))
    by_hand = integral_from_tip(y, out["l_y"].y)
    assert all(close(a, b, 1e-12) for a, b in zip(out["v_y"].y, by_hand, strict=True))
    by_hand = integral_from_tip(y, out["v_y"].y)
    assert all(close(a, b, 1e-12) for a, b in zip(out["m_y"].y, by_hand, strict=True))
    assert out["v_y"].y[0] > 0.0
    assert out["m_y"].y[0] > 0.0
