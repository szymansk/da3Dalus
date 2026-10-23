"""neutral-point and static-margin of BRYAN and JAGUAR through the public compute(), real AVL.

Aero tier. Except for the BRYAN reference test the goldens are **regression, not validation**
(aero_kernel/CLAUDE.md): they pin what this build computes (AVL 3.40 from the avl-binary wheel,
NeuralFoil xlarge for the minimum-drag speed that sets the lift coefficient) so that a change of code
or tool is noticed. The AVL world has no fuselage, so the numbers are neutral points of the wing and
tail, not of the airplane.

The CG of BRYAN is the plan value (136.8 mm, 31.4 % MAC). JAGUAR's is the maintainer's (2026-10-23,
#1203): 40.41 mm aft of the main wing's root leading edge, derived from the geometry below.
"""

import pytest
from aero_kernel import compute
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.solvers.avl import AvlAdapter, contour_worker
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = [pytest.mark.aero]

JAGUAR_CG_AFT_OF_ROOT_LE = 0.04041  # maintainer 2026-10-23, #1203


def main_wing_root_le_x(member: FleetMember) -> float:
    """x of the main wing's root leading edge in the geometry frame."""
    wings = reference_document(member)["wings"].values()
    (main,) = [w for w in wings if w["surface_type"] == "main_wing"]
    return float(main["x_secs"][0]["xyz_le"][0])


CG = {
    FleetMember.BRYAN: 0.1368,
    FleetMember.JAGUAR: main_wing_root_le_x(FleetMember.JAGUAR) + JAGUAR_CG_AFT_OF_ROOT_LE,
}
WORLDS = ("textbook", "pappas", "avl")
# Regression goldens (m): x_NP per world; SM per world follows as (x_NP - CG) / c_MAC.
GOLDEN_NP = {
    FleetMember.BRYAN: (0.1441142600, 0.1401394435, 0.144036),
    FleetMember.JAGUAR: (0.1233721388, 0.1238206059, 0.132416),
}
C_MAC = {FleetMember.BRYAN: 0.13277219166316895, FleetMember.JAGUAR: 0.10504546518699101}
# BRYAN's C_L at the minimum-drag speed (test_minimum_drag_speed_fleet.GOLDEN) and the AVL neutral
# point of the template's own aligned mesh under the kernel's conditions at that C_L:
# scripts/sim_export/crrcsim/avl_kernel_reference.py, AVL_CONVERGENCE.md "Kernel conditions".
BRYAN_CL_MD = 0.6240228
BRYAN_TEMPLATE_X_NP = 0.144021
ABS_M = 1e-4  # the regression tolerance of the AVL world


async def run(member: FleetMember) -> ComputeResult:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                "centre-of-gravity": CG[member],
            },
        }
    )
    return await compute(aircraft, request("neutral-point", "static-margin"))


@pytest.mark.parametrize("member", list(FleetMember))
@pytest.mark.asyncio
async def test_the_np_and_sm_intervals_per_world_are_the_regression_goldens(
    member: FleetMember,
) -> None:
    result = await run(member)
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    neutral, margin = result.quantities
    golden_sm = tuple((x - CG[member]) / C_MAC[member] for x in GOLDEN_NP[member])
    for quantity, golden, tolerance in (
        (neutral, GOLDEN_NP[member], ABS_M),
        (margin, golden_sm, ABS_M / C_MAC[member]),
    ):
        assert quantity.interval is not None
        worlds = quantity.interval.worlds
        assert set(worlds) == {f"neutral-point={w}" for w in WORLDS}
        for name, value in zip(WORLDS, golden, strict=True):
            assert abs(worlds[f"neutral-point={name}"] - value) < tolerance, (quantity.slug, name)
        assert quantity.interval.min == min(worlds.values())
        assert quantity.interval.max == max(worlds.values())
    assert result.provenance.solver_settings["avl_nspan"] == 24
    assert result.provenance.solver_settings["avl_core_ratio"] == 0.25
    assert set(result.provenance.tool_versions) >= {"avl-binary", "aerosandbox"}


@pytest.mark.asyncio
async def test_bryan_declares_the_missing_fuselage_in_every_world_and_converges() -> None:
    result = await run(FleetMember.BRYAN)
    for quantity in result.quantities:
        fuselage = [w for w in quantity.warnings if w.code == "fuselage_not_modelled"]
        assert len(fuselage) == len(WORLDS)
        assert "avl_mesh_not_converged" not in {w.code for w in quantity.warnings}


@pytest.mark.asyncio
async def test_jaguar_declares_its_span_sensitivity_in_the_avl_world() -> None:
    """JAGUAR's AVL neutral point moves by 1.8 % MAC when the span mesh doubles (10/24 against
    10/48: 0.1325 against 0.1346 m), above the 0.5 % tolerance: a defect warning, in the AVL world."""
    result = await run(FleetMember.JAGUAR)
    for quantity in result.quantities:
        (warning,) = [w for w in quantity.warnings if w.code == "avl_mesh_not_converged"]
        assert warning.world == "neutral-point=avl"
        assert 0.005 < float(warning.detail["delta_mac"]) < 0.03  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_bryan_avl_world_equals_the_template_under_the_kernels_conditions() -> None:
    """The reference value of the prototype's own mesh, to 0.1 % MAC. A miss means looking at the
    writer, never at the tolerance."""
    plane = AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN))
    async with SolverRuntime() as runtime:
        found = await AvlAdapter(runtime).neutral_point(plane, BRYAN_CL_MD)
    assert abs(found.x_np - BRYAN_TEMPLATE_X_NP) < 1e-3 * C_MAC[FleetMember.BRYAN]
    assert found.warnings == ()


def test_claf_follows_the_thickness_rule_of_the_airfoil() -> None:
    """CLAF = 1 + 0.77 t/c with t/c from AeroSandbox: NACA 0012 is 12 % thick."""
    (contour,) = contour_worker(("naca0012",)).value
    assert close(contour.claf, 1.0 + 0.77 * 0.12, 5e-3)
    xs = [x for x, _ in contour.coordinates]
    assert min(xs) >= -1e-9
    assert max(xs) <= 1.0 + 1e-9
