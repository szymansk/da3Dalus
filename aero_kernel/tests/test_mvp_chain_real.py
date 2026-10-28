"""The MVP-chain adapters against real AeroSandbox and AVL (aero tier).

The fin area and the V-tail share are compared with the fast tier's stand-in, the lateral derivatives
with their physical signs and with the airplane without its fuselage, and the moment slope with the
transfer of the moment reference.
"""

import math

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.asb_airplane import fin_area, horizontal_tail_area, surface_properties
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.opti import OptiAdapter
from aero_kernel.tests.asb_fakes import (
    stand_in_fin_area,
    stand_in_horizontal_tail_area,
    stand_in_v_tail_surface,
)
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_v_tail_neutral_point import (
    CHORD,
    RISES,
    ROOT_Y,
    developed_half_length,
    v_tail_airplane,
)

pytestmark = [pytest.mark.aero]

AIR = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)


def plane(member: FleetMember) -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(reference_document(member))


def tail_key(airplane: AirplaneGeometry, *types: str) -> str:
    (key,) = [k for k, w in (airplane.wings or {}).items() if w.surface_type in types]
    return key


@pytest.mark.parametrize("member", [FleetMember.BRYAN, FleetMember.JAGUAR, FleetMember.RV7])
def test_the_fin_area_is_the_planform_area_of_the_lofted_fin(member: FleetMember) -> None:
    airplane = plane(member)
    key = tail_key(airplane, "vertical_tail")
    wing = (airplane.wings or {})[key]
    assert close(fin_area(airplane, key), stand_in_fin_area(wing), 5e-3)


@pytest.mark.parametrize(
    "member", [FleetMember.BRYAN, FleetMember.JAGUAR, FleetMember.RV7, FleetMember.CHEKKER]
)
def test_the_horizontal_tail_area_is_the_gross_planform_area_of_the_lofted_tail(
    member: FleetMember,
) -> None:
    airplane = plane(member)
    key = tail_key(airplane, "horizontal_tail")
    wing = (airplane.wings or {})[key]
    assert close(horizontal_tail_area(airplane, key), stand_in_horizontal_tail_area(wing), 5e-3)


def test_the_v_tail_share_is_the_planform_area_times_sin_squared_of_the_panel_angle() -> None:
    airplane = plane(FleetMember.BELEMNITOS)
    key = tail_key(airplane, "v_tail")
    wing = (airplane.wings or {})[key]
    share = fin_area(airplane, key)
    assert share > 0.0
    assert close(share, stand_in_fin_area(wing), 5e-3)


def test_the_v_tail_horizontal_share_is_the_planform_area_times_cos_squared_of_the_panel_angle() -> (
    None
):
    airplane = plane(FleetMember.BELEMNITOS)
    key = tail_key(airplane, "v_tail")
    wing = (airplane.wings or {})[key]
    effective = horizontal_tail_area(airplane, key)
    assert effective > 0.0
    assert close(effective, stand_in_horizontal_tail_area(wing), 5e-3)
    # the two shares are the panels' true area between them
    assert close(
        effective + fin_area(airplane, key),
        stand_in_v_tail_surface(wing).area + stand_in_fin_area(wing),
        5e-3,
    )


def test_the_v_tail_surface_has_the_stand_ins_true_panel_aspect_ratio() -> None:
    airplane = plane(FleetMember.BELEMNITOS)
    key = tail_key(airplane, "v_tail")
    real = surface_properties(airplane, key)
    stand_in = stand_in_v_tail_surface((airplane.wings or {})[key])
    assert close(real.area, stand_in.area, 5e-3)
    assert close(real.aspect_ratio, stand_in.aspect_ratio, 5e-3)
    assert close(real.c_mac, stand_in.c_mac, 5e-3)


@pytest.mark.asyncio
async def test_the_lateral_derivatives_of_bryan_have_their_physical_signs() -> None:
    airplane = plane(FleetMember.BRYAN)
    async with SolverRuntime() as runtime:
        found = await AvlAdapter(runtime).lateral_derivatives(airplane, 0.6, 0.13)
    assert found.c_l_beta < 0.0  # dihedral effect rights the aircraft
    assert found.c_n_beta > 0.0  # weathercock stability
    assert found.c_l_p < 0.0  # roll damping
    assert found.c_n_r < 0.0  # yaw damping
    assert found.c_l_r > 0.0
    assert [w.code for w in found.warnings] == ["avl_body_equivalent_round"]


@pytest.mark.asyncio
async def test_the_fuselage_changes_the_weathercock_stability() -> None:
    airplane = plane(FleetMember.BRYAN)
    bare = airplane.model_copy(update={"fuselages": None})
    async with SolverRuntime() as runtime:
        adapter = AvlAdapter(runtime)
        with_body = await adapter.lateral_derivatives(airplane, 0.6, 0.13)
        without = await adapter.lateral_derivatives(bare, 0.6, 0.13)
    assert without.warnings == ()
    assert with_body.c_n_beta != without.c_n_beta


@pytest.mark.asyncio
async def test_the_moment_slope_moves_with_the_reference_by_the_arm_in_chords() -> None:
    """SM(x_ref) is linear in the reference: moving it aft by d lowers the margin by d / c_MAC."""
    airplane = plane(FleetMember.BRYAN)
    c_mac = FleetMember.BRYAN.reference.c_mac
    async with SolverRuntime() as runtime:
        adapter = OptiAdapter(runtime)
        near = await adapter.moment_slope(airplane, 0.151, 9.80665, AIR, 8.0, 0.13)
        far = await adapter.moment_slope(airplane, 0.151, 9.80665, AIR, 8.0, 0.14)
    first, second = near.solution, far.solution
    assert close(first.cl_alpha, second.cl_alpha, 1e-9)
    margin_near = -first.cm_alpha / first.cl_alpha
    margin_far = -second.cm_alpha / second.cl_alpha
    assert abs((margin_near - margin_far) - 0.01 / c_mac) < 5e-3
    assert math.isfinite(margin_near)


@pytest.mark.parametrize("rise", RISES[1:])  # a flat V-tail has no fin share to add
def test_the_v_tail_shares_add_up_to_the_true_area_in_asb(rise: float) -> None:
    """Trace test against real ASB: S_h,eff + S_v,eff = S_tot over both halves and the root extension."""
    airplane = v_tail_airplane(rise, ROOT_Y)
    total = horizontal_tail_area(airplane, "vee") + fin_area(airplane, "vee")
    assert close(total, 2.0 * CHORD * developed_half_length(rise), 1e-9)


def test_a_flat_v_tail_is_the_horizontal_tail_in_asb_with_the_root_carried_to_the_centreline() -> (
    None
):
    """nu -> 0: area, span, aspect ratio, MAC and its leading edge equal those of the horizontal tail."""
    flat = v_tail_airplane(0.0, ROOT_Y)
    plain = v_tail_airplane(0.0, ROOT_Y, "horizontal_tail")
    assert close(horizontal_tail_area(flat, "vee"), horizontal_tail_area(plain, "vee"), 1e-9)
    a, b = surface_properties(flat, "vee"), surface_properties(plain, "vee")
    for got, want in (
        (a.area, b.area),
        (a.span, b.span),
        (a.aspect_ratio, b.aspect_ratio),
        (a.c_mac, b.c_mac),
        (a.x_le_mac, b.x_le_mac),
    ):
        assert close(got, want, 1e-9)
