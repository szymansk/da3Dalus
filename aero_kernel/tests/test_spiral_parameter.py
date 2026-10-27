"""spiral-parameter: B = l_V,CG Gamma_eq / (b_ref C_L) at V_md and V_mp, per neutral-point world (fast tier)."""

import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.spiral_parameter import spiral_parameter
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import QuantityStatus
from aero_kernel.solvers.air import AirState
from aero_kernel.tests.chain_builders import C_MAC, SM_TARGET, WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    close,
    context_with,
)
from aero_kernel.tests.np_builders import surface
from aero_kernel.tests.stall_stubs import consistent_glide, consistent_min_sink
from aero_kernel.tests.test_neutral_point import MASS, RHO
from aero_kernel.tests.test_tail_arms import X_FIN_QC

pytestmark = pytest.mark.asyncio

GRAVITY = 9.80665
AIR = AirState(density=RHO, dynamic_viscosity=STUB_VISCOSITY, speed_of_sound=STUB_SPEED_OF_SOUND)
# The main wing: flat to 60 % of the half span 0.7 m, then 10 deg up; constant chord 0.2 m. The entry's
# check: Gamma_eq = 10 * 0.32 / 0.5 = 6.4 deg. S_ref = 0.28 m^2 (planform), b_ref = 1.4 m.
GAMMA_EQ = 6.4
S_REF, B_REF = 0.28, 1.4


def polyhedral_main() -> dict[str, Any]:
    rise = 0.28 * math.tan(math.radians(10.0))
    sections = [
        {"xyz_le": [0.05, y, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca0012"}
        for y, z in ((0.0, 0.0), (0.42, 0.0), (0.7, rise))
    ]
    return {"name": "main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}


def polyhedral_airplane() -> AirplaneGeometry:
    wings = {
        "main": polyhedral_main(),
        "htail": surface("htail", "horizontal_tail", 0.2, 0.1, 0.60),
        "fin": fin(),
    }
    return AirplaneGeometry.model_validate({"name": "polyhedral", "wings": wings})


def spiral(arm: float, speed: float) -> float:
    cl = MASS * GRAVITY / (0.5 * RHO * speed**2 * S_REF)
    return arm * GAMMA_EQ / (B_REF * cl)


async def test_b_at_both_speeds_is_the_arm_times_the_equivalent_dihedral_over_span_and_cl() -> None:
    plane = polyhedral_airplane()
    run = await run_chain("spiral-parameter-md", "spiral-parameter-mp", airplane=plane)
    v_md = consistent_glide(plane, MASS, GRAVITY, 1.0, AIR).v_md
    v_mp = consistent_min_sink(plane, MASS, GRAVITY, 1.0, AIR).v_mp
    for slug, speed in (("spiral-parameter-md", v_md), ("spiral-parameter-mp", v_mp)):
        quantity = run.quantity(slug)
        assert quantity.status is QuantityStatus.OK, quantity
        assert quantity.interval is not None
        assert set(quantity.interval.worlds) == set(WORLD_X_NP)
        for world, x_np in WORLD_X_NP.items():
            arm = X_FIN_QC - (x_np - SM_TARGET * C_MAC)
            assert close(quantity.interval.worlds[world], spiral(arm, speed), 1e-9), (slug, world)


async def test_the_mp_value_is_smaller_by_the_ratio_of_the_lift_coefficients() -> None:
    """B ~ 1/C_L and C_L(V_mp) = sqrt(3) C_L(V_md) on a parabolic polar: B_mp = B_md / sqrt(3)."""
    run = await run_chain(
        "spiral-parameter-md", "spiral-parameter-mp", airplane=polyhedral_airplane()
    )
    md, mp = run.quantity("spiral-parameter-md"), run.quantity("spiral-parameter-mp")
    assert md.interval is not None
    assert mp.interval is not None
    for world in WORLD_X_NP:
        assert close(mp.interval.worlds[world], md.interval.worlds[world] / math.sqrt(3.0), 1e-9)


async def test_a_flat_wing_has_no_equivalent_dihedral_and_b_is_zero() -> None:
    run = await run_chain("spiral-parameter-md")
    quantity = run.quantity("spiral-parameter-md")
    assert quantity.interval is not None
    assert all(value == 0.0 for value in quantity.interval.worlds.values())


async def test_without_a_vertical_tail_the_parameter_does_not_apply() -> None:
    quantity = (await run_chain("spiral-parameter-md", airplane=document())).quantity(
        "spiral-parameter-md"
    )
    assert quantity.status is not QuantityStatus.OK
    assert quantity.interval is None


def inputs(plane: AirplaneGeometry, **overrides: float) -> dict[str, Any]:
    given: dict[str, Any] = {
        "airplane": plane,
        "s_ref": S_REF,
        "b_ref": B_REF,
        "l_v_cg": 0.4,
        "m": MASS,
        "g": GRAVITY,
        "rho": RHO,
        "v_md": 12.0,
        "v_mp": 9.0,
    }
    given.update(overrides)
    return given


async def test_the_formula_is_the_closed_form_for_given_speeds() -> None:
    found = await spiral_parameter(inputs(polyhedral_airplane()), context_with(StubAtmosphere({})))
    assert close(found["b_spiral_md"], spiral(0.4, 12.0), 1e-9)
    assert close(found["b_spiral_mp"], spiral(0.4, 9.0), 1e-9)


@pytest.mark.parametrize("override", [{"m": 0.0}, {"v_md": math.inf}, {"g": -1.0}])
async def test_a_lift_coefficient_that_is_not_positive_is_invalid_input(
    override: dict[str, float],
) -> None:
    with pytest.raises(FormulaError) as raised:
        await spiral_parameter(
            inputs(polyhedral_airplane(), **override), context_with(StubAtmosphere({}))
        )
    assert raised.value.category is ErrorCategory.INVALID_INPUT
