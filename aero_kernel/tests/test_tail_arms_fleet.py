"""l_H,CG and l_V,CG of BRYAN and JAGUAR through the public compute(), real AVL and real AeroSandbox.

Aero tier. The goldens are **regression, not validation** (aero_kernel/CLAUDE.md): they pin what this
build computes. The positions of the tails are AeroSandbox's quarter-chord MAC; the CG is the design CG
of each neutral-point world, so every arm is an interval over the three worlds.
"""

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.solvers.asb_airplane import AC_FRACTION, quarter_chord_mac_x, surface_properties
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero]

SM_TARGET = 0.10
WORLDS = ("textbook", "pappas", "avl")
ABS_M = 1e-4  # the regression tolerance of the AVL world
# Regression goldens (m), per world textbook / Pappas / AVL: the design CG at SM_target = 0.10 and the
# arms l_H,CG and l_V,CG from it.
GOLDEN_CG = {
    FleetMember.BRYAN: (0.1266041726, 0.1269010159, 0.1307588397),
    FleetMember.JAGUAR: (0.1075391889, 0.1133476263, 0.1158455146),
}
GOLDEN_L_H = {
    FleetMember.BRYAN: (0.2972459914, 0.2969491481, 0.2930913242),
    FleetMember.JAGUAR: (0.2447503047, 0.2389418673, 0.2364439791),
}
GOLDEN_L_V = {
    FleetMember.BRYAN: (0.3157883688, 0.3154915255, 0.3116337017),
    FleetMember.JAGUAR: (0.2320591484, 0.2262507110, 0.2237528227),
}


async def run(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                "static-margin-target": SM_TARGET,
            },
        }
    )
    return await compute(
        aircraft, request("centre-of-gravity-design", "horizontal-tail-arm", "vertical-tail-arm")
    )


def key_of(member: FleetMember, surface_type: str) -> tuple[AirplaneGeometry, str]:
    plane = AirplaneGeometry.model_validate(reference_document(member))
    (key,) = [k for k, w in (plane.wings or {}).items() if w.surface_type == surface_type]
    return plane, key


@pytest.mark.parametrize("member", list(FleetMember))
@pytest.mark.asyncio
async def test_the_arms_per_world_are_the_regression_goldens(member: FleetMember) -> None:
    result = await run(member)
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    cg, l_h, l_v = result.quantities
    print(
        member.name,
        [cg.interval.worlds[f"neutral-point={w}"] for w in WORLDS],
        [l_h.interval.worlds[f"neutral-point={w}"] for w in WORLDS],
        [l_v.interval.worlds[f"neutral-point={w}"] for w in WORLDS],
    )
    for quantity, golden in ((cg, GOLDEN_CG), (l_h, GOLDEN_L_H), (l_v, GOLDEN_L_V)):
        assert quantity.interval is not None
        worlds = quantity.interval.worlds
        assert set(worlds) == {f"neutral-point={w}" for w in WORLDS}
        for name, value in zip(WORLDS, golden[member], strict=True):
            assert abs(worlds[f"neutral-point={name}"] - value) < ABS_M, (quantity.slug, name)
        assert quantity.interval.min == min(worlds.values())
        assert quantity.interval.max == max(worlds.values())


@pytest.mark.parametrize("member", list(FleetMember))
@pytest.mark.asyncio
async def test_each_arm_is_asbs_quarter_chord_mac_less_the_design_cg_in_every_world(
    member: FleetMember,
) -> None:
    result = await run(member)
    cg, l_h, l_v = result.quantities
    assert cg.interval is not None
    assert l_h.interval is not None
    assert l_v.interval is not None
    plane, tail_key = key_of(member, "horizontal_tail")
    _, fin_key = key_of(member, "vertical_tail")
    x_tail = quarter_chord_mac_x(plane, tail_key)
    x_fin = quarter_chord_mac_x(plane, fin_key)
    for world, x_cg in cg.interval.worlds.items():
        assert abs(l_h.interval.worlds[world] - (x_tail - x_cg)) < 1e-9, world
        assert abs(l_v.interval.worlds[world] - (x_fin - x_cg)) < 1e-9, world


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_tail_position_is_the_one_the_neutral_point_uses(member: FleetMember) -> None:
    """One authority (ADR 0022): x_le,MAC + 0.25 c_MAC of the planform values is the aerodynamic centre."""
    plane, tail_key = key_of(member, "horizontal_tail")
    surface = surface_properties(plane, tail_key)
    x_neutral_point_uses = surface.x_le_mac + AC_FRACTION * surface.c_mac
    assert abs(quarter_chord_mac_x(plane, tail_key) - x_neutral_point_uses) < 1e-12
