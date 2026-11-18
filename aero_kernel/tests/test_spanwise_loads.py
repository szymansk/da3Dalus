"""spanwise-loads and max-mass-structure: the formulas against hand values, stub adapters (fast tier)."""

import math

import pytest
from aero_kernel.context import Context, Value
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.max_mass_structure import max_mass_structure
from aero_kernel.formulas.spanwise_loads import spanwise_loads
from aero_kernel.schema import Curve, KernelWarning
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


@pytest.mark.parametrize(("name", "value"), [("v", 0.0), ("v", -3.0), ("rho", 0.0)])
async def test_a_speed_or_density_that_is_not_positive_is_refused(name: str, value: float) -> None:
    with pytest.raises(FormulaError) as caught:
        await spanwise_loads(inputs(**{name: value}), context(StubAvl()))
    assert caught.value.category is ErrorCategory.INVALID_INPUT
    assert caught.value.parameter == name


async def test_an_adapter_error_passes_through_unchanged() -> None:
    avl = StubAvl()
    refusal = FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "unsupported_configuration", "m", "h"
    )
    avl.loads_failure = refusal
    with pytest.raises(FormulaError) as caught:
        await spanwise_loads(inputs(), context(avl))
    assert caught.value is refusal


async def test_the_mass_at_which_the_spar_breaks_at_one_g_is_the_break_load_factor_times_the_mass() -> (
    None
):
    """Hand value: n_break = 41 at 0.151 kg -> 6.191 kg (BRYAN's recorded figure, STAND.md)."""
    ctx = context(StubAvl())
    out = await max_mass_structure({"n_break_pos": 41.0, "m": 0.151}, ctx)
    assert math.isclose(out["m_max_struct"], 41.0 * 0.151, rel_tol=1e-15)


async def test_a_break_load_factor_that_is_not_a_number_is_a_defect_of_the_caller() -> None:
    with pytest.raises(TypeError):
        await max_mass_structure({"n_break_pos": None, "m": 1.0}, context(StubAvl()))
