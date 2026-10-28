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
from aero_kernel.formulas.cg_for_target_margin import cg_for_target_margin
from aero_kernel.geometry import AirplaneGeometry, InlineAirfoil
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.solvers.asb_airplane import load_aerosandbox
from aero_kernel.solvers.avl import AIRFOIL_POINTS_PER_SIDE, AvlAdapter, contour_worker
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import StubAtmosphere, close, context_with
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
    # the design CG of the canon (cg-for-target-margin, SM_target 0.10) in the AVL world, from the
    # kernel's centre-of-gravity-design; test_cg_for_target_margin... checks it. Never a hand-chosen
    # position (maintainer 2026-10-26).
    FleetMember.RV7: 0.241646,
    # CHEKKER and WIESEL likewise: the design CG of the AVL world (the geometry format has no CG)
    FleetMember.CHEKKER: 0.18469116469928673,
    FleetMember.WIESEL: 0.1804036813580844,
    # BELEMNITOS (V-tail, #1208): the design CG of the AVL world at SM_target 0.10
    FleetMember.BELEMNITOS: 0.06118300890616699,
}
DESIGN_CG_MEMBERS = (
    FleetMember.RV7,
    FleetMember.CHEKKER,
    FleetMember.WIESEL,
    FleetMember.BELEMNITOS,
)
WORLDS = ("textbook", "pappas", "avl")
# Regression goldens (m): x_NP per world; SM per world follows as (x_NP - CG) / c_MAC.
# The textbook world takes the default tail efficiency 0.65 (#1205); it was 0.9 before:
# BRYAN 0.1441142600 -> 0.1398911924 m, JAGUAR 0.1233721388 -> 0.1180210991 m.
# Since #1253 the surfaces are AeroSandbox's (area, AR = b^2/S, MAC, x_AC - 0.25 MAC): textbook/Pappas
# BRYAN 0.1398911924/0.1401394435 -> 0.1398961691/0.1402057906 m, JAGUAR 0.1180210991/0.1238206059 ->
# 0.1181103705/0.1239713559 m; the eta = 0.9 values below moved from 0.1441142600/0.1233721388.
GOLDEN_NP = {
    FleetMember.BRYAN: (0.1398843329, 0.1401811762, 0.144039),
    FleetMember.JAGUAR: (0.1180376743, 0.1238461117, 0.126344),
    FleetMember.RV7: (0.2561507, 0.2581105, 0.259946),
    FleetMember.CHEKKER: (0.1906369, 0.1960934, 0.200839),
    FleetMember.WIESEL: (0.1919482, 0.2003031, 0.196669),
    # V-tail (#1208): S_h,eff = sum S_i cos^2(nu_i) with the root carried to the centreline, the lift slope from the
    # developed panel aspect ratio;
    # recorded from the kernel (regression). The AVL mesh is declared not converged (1.27 % MAC).
    FleetMember.BELEMNITOS: (0.07140062263587507, 0.08524524177346318, 0.07517),
}
# Since #1262 the area includes the centreline gap: textbook/Pappas BRYAN 0.1398961691/0.1402057906 ->
# 0.1398843329/0.1401811762 m, JAGUAR 0.1181103705/0.1239713559 -> 0.1180376743/0.1238461117 m.
# The textbook world with the former constant given explicitly as tail-efficiency (continuity).
GOLDEN_TEXTBOOK_ETA_09 = {
    FleetMember.BRYAN: 0.1441059605,
    FleetMember.JAGUAR: 0.1233923918,
    FleetMember.RV7: 0.2627406,
    FleetMember.CHEKKER: 0.1965633,
    FleetMember.WIESEL: 0.1997806,
    FleetMember.BELEMNITOS: 0.08083035102212023,
}
# AeroSandbox's c_MAC of the main wing (gh-1240); it was the kernel's projected 0.13277219 / 0.10504547.
C_MAC = {member: member.asb_reference[2] for member in FleetMember}
# BRYAN's C_L at the minimum-drag speed (test_minimum_drag_speed_fleet.GOLDEN) and the AVL neutral
# point of the template's own aligned mesh under the kernel's conditions at that C_L:
# scripts/sim_export/crrcsim/avl_kernel_reference.py, AVL_CONVERGENCE.md "Kernel conditions".
BRYAN_CL_MD = 0.6225775
BRYAN_TEMPLATE_X_NP = 0.144023
SM_TARGET = 0.10
ABS_M = 1e-4  # the regression tolerance of the AVL world


async def run(member: FleetMember, eta: float | None = None) -> ComputeResult:
    extra = {} if eta is None else {"tail-efficiency": eta}
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                "centre-of-gravity-measured": CG[member],
                **extra,
            },
        }
    )
    return await compute(aircraft, request("neutral-point", "static-margin-measured"))


@pytest.mark.parametrize("member", list(GOLDEN_NP))
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


@pytest.mark.parametrize("member", list(GOLDEN_NP))
@pytest.mark.asyncio
async def test_the_textbook_world_with_eta_09_given_reproduces_the_former_golden(
    member: FleetMember,
) -> None:
    """Regression continuity across #1205: eta = 0.9 as an input gives the value of the old constant,
    and the other two worlds do not move."""
    result = await run(member, eta=0.9)
    neutral = result.quantities[0]
    assert neutral.interval is not None
    worlds = neutral.interval.worlds
    assert abs(worlds["neutral-point=textbook"] - GOLDEN_TEXTBOOK_ETA_09[member]) < ABS_M
    for name, golden in zip(WORLDS[1:], GOLDEN_NP[member][1:], strict=True):
        assert abs(worlds[f"neutral-point={name}"] - golden) < ABS_M, name
    assert "tail-efficiency" not in [d.slug for d in result.provenance.defaults_used]


@pytest.mark.asyncio
async def test_bryan_declares_the_missing_fuselage_in_every_world_and_converges() -> None:
    result = await run(FleetMember.BRYAN)
    for quantity in result.quantities:
        fuselage = [w for w in quantity.warnings if w.code == "fuselage_not_modelled"]
        assert len(fuselage) == len(WORLDS)
        assert "avl_mesh_not_converged" not in {w.code for w in quantity.warnings}


@pytest.mark.asyncio
async def test_chekker_declares_the_avl_mesh_as_not_converged_and_wiesel_converges() -> None:
    """CHEKKER's AVL neutral point moves by 0.55 % MAC under the refined mesh, above the 0.5 %
    tolerance: a declared defect (ADR 0020), the value is still returned. WIESEL's agrees."""
    chekker = await run(FleetMember.CHEKKER)
    for quantity in chekker.quantities:
        (not_converged,) = [w for w in quantity.warnings if w.code == "avl_mesh_not_converged"]
        assert not_converged.world == "neutral-point=avl"
        assert 0.005 < float(not_converged.detail["delta_mac"]) < 0.006  # pyright: ignore[reportArgumentType]
    for quantity in (await run(FleetMember.WIESEL)).quantities:
        assert "avl_mesh_not_converged" not in {w.code for w in quantity.warnings}


@pytest.mark.asyncio
async def test_the_substituted_fuselage_is_declared_on_the_neutral_point() -> None:
    """The equivalent fuselage section (#1307) is declared on the result, once per substituted
    section, next to the missing fuselage of the three neutral-point worlds."""
    for member, sections in ((FleetMember.CHEKKER, 37), (FleetMember.WIESEL, 46)):
        neutral = (await run(member)).quantities[0]
        found = [w for w in neutral.warnings if w.code == "fuselage_section_equivalent"]
        assert len(found) == sections, member
        assert {w.origin for w in found} == {"airplane"}


@pytest.mark.asyncio
async def test_jaguar_converges_once_its_root_is_on_the_centreline() -> None:
    """JAGUAR's root section is stored at y = +1.1 mm. Held there, the mirrored halves left a slit and
    the neutral point drifted by 1.9 % MAC per span doubling; on the centreline 10/24 against its
    refinement agrees to 0.2 % MAC, below the 0.5 % tolerance, so no warning."""
    result = await run(FleetMember.JAGUAR)
    for quantity in result.quantities:
        assert "avl_mesh_not_converged" not in {w.code for w in quantity.warnings}


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


@pytest.mark.asyncio
async def test_the_neutral_point_does_not_depend_on_how_the_surfaces_are_stored() -> None:
    """BRYAN's wing and tail stored on -y and tip first give the same AVL neutral point (the
    same wing stored on -y once gave 8.6 % MAC less, tip first made AVL spin)."""
    document = reference_document(FleetMember.BRYAN)
    flipped = reference_document(FleetMember.BRYAN)
    for wing in flipped["wings"].values():
        if wing["symmetric"]:
            for section in wing["x_secs"]:
                section["xyz_le"][1] = -section["xyz_le"][1]
            wing["x_secs"].reverse()
    async with SolverRuntime() as runtime:
        adapter = AvlAdapter(runtime)
        want = await adapter.neutral_point(AirplaneGeometry.model_validate(document), BRYAN_CL_MD)
        got = await adapter.neutral_point(AirplaneGeometry.model_validate(flipped), BRYAN_CL_MD)
    assert abs(got.x_np - want.x_np) < 1e-6


def test_every_contour_is_repanelled_to_the_declared_point_count() -> None:
    """AVL stops at 399 contour points (IBX): a NACA 2412 from AeroSandbox has 399 and failed. Every
    airfoil is repanelled, never only the ones that are too large (ADR 0020)."""
    naca, thin = contour_worker(("naca2412", "naca0012")).value
    expected = 2 * AIRFOIL_POINTS_PER_SIDE - 1
    assert len(naca.coordinates) == len(thin.coordinates) == expected
    asb = load_aerosandbox()
    dense = asb.Airfoil("naca0012").repanel(n_points_per_side=500).coordinates
    points = tuple((float(x), float(y)) for x, y in dense)
    (inline,) = contour_worker((InlineAirfoil(coordinates=points),)).value
    assert len(inline.coordinates) == expected


@pytest.mark.asyncio
async def test_a_naca_2412_wing_and_tail_runs_through_avl() -> None:
    """NACA airfoils of AeroSandbox exceed AVL's contour limit unless repanelled."""
    document = reference_document(FleetMember.BRYAN)
    for wing in document["wings"].values():
        for section in wing["x_secs"]:
            section["airfoil"] = "naca2412"
    plane = AirplaneGeometry.model_validate(document)
    async with SolverRuntime() as runtime:
        found = await AvlAdapter(runtime).neutral_point(plane, BRYAN_CL_MD)
    assert 0.10 < found.x_np < 0.17


@pytest.mark.asyncio
async def test_a_ventral_fin_gives_the_same_neutral_point() -> None:
    """BRYAN's fin mirrored below the wing plane (z -> -z): the fin does not enter the longitudinal
    neutral point, whichever way it points."""
    document = reference_document(FleetMember.BRYAN)
    ventral = reference_document(FleetMember.BRYAN)
    for wing in ventral["wings"].values():
        if wing["surface_type"] == "vertical_tail":
            for section in wing["x_secs"]:
                section["xyz_le"][2] = -section["xyz_le"][2]
    async with SolverRuntime() as runtime:
        adapter = AvlAdapter(runtime)
        want = await adapter.neutral_point(AirplaneGeometry.model_validate(document), BRYAN_CL_MD)
        got = await adapter.neutral_point(AirplaneGeometry.model_validate(ventral), BRYAN_CL_MD)
    assert abs(got.x_np - want.x_np) < 1e-4


@pytest.mark.parametrize("member", list(GOLDEN_NP))
@pytest.mark.asyncio
async def test_cg_for_target_margin_is_the_neutral_point_less_the_target_per_world(
    member: FleetMember,
) -> None:
    """One compute: x_cg,design = x_NP - SM_target c_MAC per world, and its margin is the target."""
    aircraft = AircraftInput.model_validate(
        {
            "airplane": reference_document(member),
            "values": {
                "aircraft-mass": member.mass_kg,
                "altitude": 0.0,
                "centre-of-gravity-measured": CG[member],
                "static-margin-target": SM_TARGET,
            },
        }
    )
    result = await compute(
        aircraft, request("neutral-point", "static-margin-measured", "centre-of-gravity-design")
    )
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result
    neutral, margin, target_cg = result.quantities
    assert neutral.interval is not None
    assert margin.interval is not None
    assert target_cg.interval is not None
    assert set(target_cg.interval.worlds) == set(neutral.interval.worlds)
    for world, x_np in neutral.interval.worlds.items():
        x_cg_sm = target_cg.interval.worlds[world]
        assert abs(x_cg_sm - (x_np - SM_TARGET * C_MAC[member])) < 1e-9, (member, world)
        assert abs((x_np - x_cg_sm) / C_MAC[member] - SM_TARGET) < 1e-9, (member, world)
        # Round trip: the target is the margin this world computes for the plan CG
        x = {"x_np": x_np, "sm_target": margin.interval.worlds[world], "c_mac": C_MAC[member]}
        back = await cg_for_target_margin(x, context_with(StubAtmosphere({})))
        assert abs(back["x_cg_sm"] - CG[member]) < 1e-9, (member, world)
    if member in DESIGN_CG_MEMBERS:  # its CG is the design CG of the AVL world
        assert abs(target_cg.interval.worlds["neutral-point=avl"] - CG[member]) < 1e-9


@pytest.mark.asyncio
async def test_the_v_tail_aircraft_has_the_three_worlds_and_declares_its_unconverged_mesh() -> None:
    """BELEMNITOS (#1208): a V-tail is the horizontal tail of the textbook and Pappas worlds, and AVL
    takes its geometry as it is. The AVL mesh moves by 1.27 % MAC under the refined mesh, above the
    0.5 % tolerance: a declared defect (ADR 0020), the value is still returned."""
    result = await run(FleetMember.BELEMNITOS)
    neutral = result.quantities[0]
    assert neutral.interval is not None
    assert abs(neutral.interval.min - GOLDEN_NP[FleetMember.BELEMNITOS][0]) < ABS_M
    (not_converged,) = [w for w in neutral.warnings if w.code == "avl_mesh_not_converged"]
    assert not_converged.world == "neutral-point=avl"
    assert 0.012 < float(not_converged.detail["delta_mac"]) < 0.013  # pyright: ignore[reportArgumentType]
