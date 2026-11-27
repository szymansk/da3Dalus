"""The MVP chain on the reference fleet with fake solvers: the fast counterpart of the aero tier.

Fast tier (#1458, P8-F04). ``test_mvp_chain_fleet.py`` and ``test_plan_batch_fleet.py`` run the
fleet through the real solvers and are not part of the pull-request run. Here the same documents go
through the same engine and the shipped canon with the stub adapters of the per-formula tests
(``fleet_chain_fakes``). The values of the solvers are fake; the tests compare what does not depend
on them: the status of every quantity, the error of a layout and what fails upstream of it, the
worlds, the tool and the application, and the arithmetic of the nodes that only combine inputs.

Five layouts are named: BRYAN (conventional, ailerons), CHEKKER (rudder only), BELEMNITOS (V-tail),
RV-7 (flaps) and VOODOO (tailless). The 28 plan models are compared with what the aero tier
recorded for them, cell by cell.
"""

import math
from typing import Any, cast

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import QuantityStatus
from aero_kernel.tests.asb_fakes import (
    stand_in_fin_area,
    stand_in_horizontal_tail_area,
    stand_in_main_wing_properties,
    stand_in_quarter_chord_x,
)
from aero_kernel.tests.fleet_chain_fakes import (
    FAKE_DENSITY,
    FAKE_X_NP_AVL,
    NEUTRAL_POINT_WORLDS,
    OK,
    ROLL_RATE_WORLDS,
    SM_TARGET,
    FleetChainRun,
    Outcome,
    run_fleet_chain,
)
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import PLAN_BATCH, FleetMember, reference_document
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK
from aero_kernel.tests.test_plan_batch_fleet import (
    GOLDEN,
    NOT_APPLICABLE,
    SLUGS,
    Failed,
    Golden,
)

pytestmark = pytest.mark.asyncio

STANDARD_GRAVITY = 9.80665  # m/s^2, the canon default of `gravity`
SCALARS = (
    "stall-speed",
    "max-lift-coefficient",
    "minimum-drag-speed",
    "max-lift-to-drag-ratio",
    "minimum-sink-speed",
)
# Canon `when: has_no_aileron`: the rudder is the roll control.
WITHOUT_AILERON_ONLY = (
    "turn-sideslip",
    "turn-sideslip-gain",
    "rudder-roll-authority-md",
    "rudder-roll-authority-mp",
)
APPROACH = (
    "dihedral-effect-app",
    "weathercock-stability-app",
    "spiral-criterion-app",
    "spiral-doubling-time-app",
)
NO_AILERON = Outcome("not_applicable")
# The errors of the real solvers that a fake solver cannot give: no convergence, no AVL output.
SOLVER_CODES = frozenset({"internal", "not_converged"})
WITH_AILERONS = (FleetMember.BRYAN, FleetMember.BELEMNITOS, FleetMember.RV7)
WITH_TAIL = (*WITH_AILERONS, FleetMember.CHEKKER)
FLAPPED_PLAN_MODELS = (
    FleetMember.ALBATROS_4,
    FleetMember.GEE_BEE_R3,
    FleetMember.P39,
    FleetMember.SPIRIT_100,
)
LANDING_NEEDS_A_DEFLECTION = Outcome("upstream_failed", (("airplane-landing", "missing_input"),))
NEEDS_A_NEUTRAL_POINT = Outcome("upstream_failed", (("neutral-point", "unsupported_layout"),))


def expected_with_fake_solvers(golden: Golden) -> Outcome:
    """What a fake-solver run must answer where the aero tier recorded ``golden``.

    A value is ``ok`` and ``not_applicable`` stays. An error stays with its causes, except what only
    a real solver can produce (``SOLVER_CODES``): such an error, and an ``upstream_failed`` whose
    every cause is one, is ``ok`` with a fake solver, which always answers.
    """
    if not isinstance(golden, Failed):
        return Outcome(NOT_APPLICABLE if golden == NOT_APPLICABLE else OK)
    remaining = tuple(cause for cause in golden.causes if cause[1] not in SOLVER_CODES)
    solver_only = golden.code in SOLVER_CODES or (golden.causes != () and not remaining)
    return Outcome(OK) if solver_only else Outcome(golden.code, remaining)


def has_the_shape_of(run: FleetChainRun, slug: str, golden: Golden) -> bool:
    """Whether an ``ok`` result is a scalar, three neutral-point worlds or the named worlds, as ``golden``."""
    quantity = run.quantity(slug)
    if isinstance(golden, float):
        return quantity.value is not None and quantity.interval is None
    if isinstance(golden, tuple):
        return quantity.value is None and frozenset(run.worlds(slug)) == NEUTRAL_POINT_WORLDS
    # Named worlds: the aero tier may have dropped a world outside its validity (roll-rate, AVL).
    return isinstance(golden, dict) and set(golden) <= set(run.worlds(slug)) <= ROLL_RATE_WORLDS


@pytest.mark.parametrize("member", PLAN_BATCH, ids=lambda m: m.name)
async def test_the_fast_chain_answers_each_cell_of_the_plan_batch_as_the_aero_tier_recorded(
    member: FleetMember,
) -> None:
    """The oracle is the recorded real-solver run (GOLDEN of test_plan_batch_fleet.py), not this run:
    status, error code and causes of all 29 quantities must be the same, except the errors only a
    real solver gives. A broken binding or applicability fact changes a status here, in the PR run."""
    run = await run_fleet_chain(member, *SLUGS)
    for slug, golden in GOLDEN[member].items():
        expected = expected_with_fake_solvers(golden)
        assert run.outcome(slug) == expected, (slug, run.quantity(slug).error)
        if expected.status == OK and not isinstance(golden, Failed):
            assert has_the_shape_of(run, slug, golden), slug


async def test_only_the_solver_errors_of_two_aircraft_differ_from_the_aero_goldens() -> None:
    """The exception of the test above is narrow: 13 cells of MINI_FUNTANA (AVL's lateral run,
    `internal`). The 6 cells of AERONCA_CHAMP (stall `not_converged` and the approach chain behind
    it) are values since gh-1423."""
    differing = {
        member: sum(
            isinstance(golden, Failed) and expected_with_fake_solvers(golden).status == OK
            for golden in cells.values()
        )
        for member, cells in GOLDEN.items()
    }
    assert {member: count for member, count in differing.items() if count} == {
        FleetMember.MINI_FUNTANA: 13,
    }


@pytest.mark.parametrize("member", WITH_AILERONS, ids=lambda m: m.name)
async def test_with_ailerons_everything_computes_but_the_rudder_only_quantities(
    member: FleetMember,
) -> None:
    """Conventional, V-tail and flapped (RV-7 with the fleet's flap deflections): 25 quantities are
    ok; the four of `when: has_no_aileron` are not applicable and say which condition failed."""
    run = await run_fleet_chain(member, *SLUGS)
    for slug in SLUGS:
        expected = NO_AILERON if slug in WITHOUT_AILERON_ONLY else Outcome(OK)
        assert run.outcome(slug) == expected, (slug, run.quantity(slug).error)
    for slug in WITHOUT_AILERON_ONLY:
        reason = run.quantity(slug).reason
        assert reason is not None
        assert reason.code.value == "condition_not_met"
        assert "`has_no_aileron`" in reason.message


async def test_the_rudder_only_chekker_has_the_turn_sideslip_and_no_roll_rate() -> None:
    """CHEKKER has a rudder and an elevator, no aileron: `roll-rate-approach` (`when: has_aileron`)
    is the one quantity that is not applicable; the four of `has_no_aileron` compute."""
    run = await run_fleet_chain(FleetMember.CHEKKER, *SLUGS)
    for slug in SLUGS:
        expected = Outcome("not_applicable") if slug == "roll-rate-approach" else Outcome(OK)
        assert run.outcome(slug) == expected, (slug, run.quantity(slug).error)
    reason = run.quantity("roll-rate-approach").reason
    assert reason is not None
    assert reason.code.value == "condition_not_met"
    assert "`has_aileron`" in reason.message


@pytest.mark.parametrize(
    "member", [FleetMember.VOODOO, FleetMember.WINDFREAK], ids=lambda m: m.name
)
async def test_a_flying_wing_has_no_neutral_point_and_says_which_layouts_are_missing(
    member: FleetMember,
) -> None:
    """The tripwire for the tailless neutral point (#1206, P8-F18): the error names the layouts the
    kernel does not cover and the surface types it found; the design CG and everything that needs
    it fail upstream with that cause; the speeds, which need no neutral point, compute."""
    run = await run_fleet_chain(member, *SLUGS)
    error = run.quantity("neutral-point").error
    assert error is not None
    assert error.code == "unsupported_layout"
    assert error.hint == "a tailless wing, a canard and a tandem wing are not covered yet"
    assert "horizontal_tail" not in cast("list[str]", error.detail["surface_types"])
    assert "v_tail" not in cast("list[str]", error.detail["surface_types"])
    assert "main_wing" in cast("list[str]", error.detail["surface_types"])
    for slug in SCALARS:
        assert run.outcome(slug) == Outcome(OK), slug
    for slug in ("centre-of-gravity-design", "dihedral-effect-md", "spiral-doubling-time-mp"):
        assert run.outcome(slug) == NEEDS_A_NEUTRAL_POINT, slug
    assert run.outcome("horizontal-tail-volume") == Outcome("not_applicable")


@pytest.mark.parametrize("member", WITH_TAIL, ids=lambda m: m.name)
async def test_the_worlds_of_the_chain_are_the_three_neutral_points(member: FleetMember) -> None:
    """A11: the speeds are scalars; everything behind the neutral point carries its three worlds;
    the roll rate carries its own two (the stub AVL's p b / 2V = 0.08 is inside AVL's range)."""
    run = await run_fleet_chain(member, *SLUGS)
    for slug in SLUGS:
        quantity = run.quantity(slug)
        if quantity.status is not QuantityStatus.OK:
            continue
        if slug in SCALARS:
            assert quantity.value is not None, slug
            assert quantity.interval is None, slug
        elif slug == "roll-rate-approach":
            assert frozenset(run.worlds(slug)) == ROLL_RATE_WORLDS
        else:
            assert frozenset(run.worlds(slug)) == NEUTRAL_POINT_WORLDS, slug


def expected_tool_and_application(slug: str) -> tuple[str, str]:
    """The tool and the application id the canon binds for a quantity of the chain (canon_model.json).

    OPT answers the speeds and the roll rate, AVL the neutral point (the last world) and the lateral
    derivatives, APP is the kernel's own arithmetic. The applications: the stall is `clean`, the
    glide and sink optima `level_flight`, the approach point `approach`, the tail volumes and the
    spiral parameter the ones of their tail, the rudder-only quantities `without_aileron`.
    """
    if slug in ("stall-speed", "max-lift-coefficient"):
        return "OPT", "clean"
    if slug in SCALARS:
        return "OPT", "level_flight"
    if slug == "roll-rate-approach":
        return "OPT", "approach"
    if slug in WITHOUT_AILERON_ONLY:
        return "APP", "without_aileron"
    if slug == "horizontal-tail-volume":
        return "APP", "with_horizontal_tail"
    if slug == "vertical-tail-volume" or slug.startswith("spiral-parameter"):
        return "APP", "with_vertical_tail"
    if slug == "centre-of-gravity-design":
        return "APP", "default"
    return "AVL", "approach" if slug in APPROACH else "default"


@pytest.mark.parametrize("member", WITH_TAIL, ids=lambda m: m.name)
async def test_every_value_names_its_tool_and_its_application(member: FleetMember) -> None:
    run = await run_fleet_chain(member, *SLUGS)
    for slug in SLUGS:
        quantity = run.quantity(slug)
        if quantity.status is QuantityStatus.OK:
            assert (quantity.tool, quantity.application) == expected_tool_and_application(slug), (
                slug
            )
        else:
            assert (quantity.tool, quantity.application) == (None, None), slug


def airplane_of(member: FleetMember) -> AirplaneGeometry:
    return AirplaneGeometry.model_validate(reference_document(member))


@pytest.mark.parametrize("member", WITH_TAIL, ids=lambda m: m.name)
async def test_the_speeds_are_the_closed_forms_of_the_fake_polar_at_the_fleet_mass(
    member: FleetMember,
) -> None:
    """The stub optimiser answers V_S = sqrt(2 m g / (rho S C_L,max)) with C_L,max = 1.19 and the
    stand-in area. Recomputed here with the member's mass (the README's), g = 9.80665 m/s^2 (the
    canon default, not passed), rho = 1.225 kg/m^3: the chain bound mass, gravity and density.
    `approach-speed` = 1.3 V_S,landing (canon: speed-from-stall-margin, k = 1.3); the fake's lift
    curve does not know flaps, so V_S,landing = V_S for it."""
    run = await run_fleet_chain(member, "stall-speed", "max-lift-coefficient", "approach-speed")
    area = stand_in_main_wing_properties(airplane_of(member)).s_ref
    weight = member.mass_kg * STANDARD_GRAVITY
    v_s = math.sqrt(2.0 * weight / (FAKE_DENSITY * area * UPRIGHT_PEAK[1]))
    assert close(run.value("stall-speed"), v_s, 1e-12)
    assert run.value("max-lift-coefficient") == UPRIGHT_PEAK[1]
    assert close(run.value("approach-speed"), 1.3 * v_s, 1e-12)
    assert {call[1] for call in run.opti.calls} == {member.mass_kg}


def tail_key(member: FleetMember, *types: str) -> str:
    (key,) = [
        name
        for name, wing in cast("dict[str, Any]", reference_document(member)["wings"]).items()
        if wing["surface_type"] in types
    ]
    return key


@pytest.mark.parametrize("member", WITH_TAIL, ids=lambda m: m.name)
async def test_the_design_cg_and_the_tail_volumes_follow_from_the_neutral_point_per_world(
    member: FleetMember,
) -> None:
    """Hand values from the fake inputs, per world (never across worlds, A11):

    x_CG = x_NP - SM_target c_MAC with SM_target = 0.10; in the AVL world x_NP is the stub's 0.14 m.
    V_H = S_h (x_h - x_CG) / (S c_MAC), Drela Eq. 3 with c_MAC; V_V = S_v (x_v - x_CG) / (S b).
    S, b, c_MAC, the tail areas and the quarter-chord MAC positions x_h, x_v are the stand-ins of
    the GEO stub; a V-tail (BELEMNITOS) is both tails, with its effective and its fin share.
    """
    run = await run_fleet_chain(member, *SLUGS)
    airplane = airplane_of(member)
    wings = airplane.wings or {}
    main = stand_in_main_wing_properties(airplane)
    h_tail = wings[tail_key(member, "horizontal_tail", "v_tail")]
    v_tail = wings[tail_key(member, "vertical_tail", "v_tail")]
    s_h, x_h = stand_in_horizontal_tail_area(h_tail), stand_in_quarter_chord_x(h_tail)
    s_v, x_v = stand_in_fin_area(v_tail), stand_in_quarter_chord_x(v_tail)
    neutral_point = run.worlds("neutral-point")
    assert neutral_point["neutral-point=avl"] == FAKE_X_NP_AVL
    for world, x_np in neutral_point.items():
        x_cg = x_np - SM_TARGET * main.c_mac
        assert close(run.worlds("centre-of-gravity-design")[world], x_cg, 1e-12), world
        v_h = s_h * (x_h - x_cg) / (main.s_ref * main.c_mac)
        assert close(run.worlds("horizontal-tail-volume")[world], v_h, 1e-12), world
        v_v = s_v * (x_v - x_cg) / (main.s_ref * main.b_ref)
        assert close(run.worlds("vertical-tail-volume")[world], v_v, 1e-12), world


@pytest.mark.parametrize("member", WITH_TAIL, ids=lambda m: m.name)
async def test_the_lateral_quantities_are_the_stub_derivatives_at_each_point(
    member: FleetMember,
) -> None:
    """The stub AVL answers C_l,beta = -0.05, C_n,beta = 0.07, C_l,r = 0.11, C_n,r = -0.06 at every
    point. The spiral criterion is E = C_l,beta C_n,r - C_n,beta C_l,r = 0.0030 - 0.0077 = -0.0047:
    unstable, so the doubling time is positive. Each of the three points asked AVL at its own design
    CG: the three worlds' CGs appear among the recorded calls."""
    run = await run_fleet_chain(member, *SLUGS)
    for point in ("md", "mp", "app"):
        for world in NEUTRAL_POINT_WORLDS:
            assert run.worlds(f"dihedral-effect-{point}")[world] == -0.05
            assert run.worlds(f"weathercock-stability-{point}")[world] == 0.07
            assert close(run.worlds(f"spiral-criterion-{point}")[world], -0.0047, 1e-12)
            assert run.worlds(f"spiral-doubling-time-{point}")[world] > 0.0
    assert set(run.worlds("roll-due-to-yaw-rate-mp").values()) == {0.11}
    asked_cgs = {call[2] for call in run.avl.lateral_calls}
    assert asked_cgs == set(run.worlds("centre-of-gravity-design").values())


async def test_the_turn_sideslip_gain_of_chekker_is_the_ratio_of_the_stub_derivatives() -> None:
    """kappa = -C_l,r / C_l,beta = 0.11 / 0.05 = 2.2 with the stub's derivatives, in every world."""
    run = await run_fleet_chain(FleetMember.CHEKKER, "turn-sideslip-gain")
    for value in run.worlds("turn-sideslip-gain").values():
        assert close(value, 2.2, 1e-12)


async def test_the_rv7_approach_point_needs_the_landing_deflection_in_the_fast_chain() -> None:
    """RV-7 has flaps: without `flap-deflection-landing` the landing configuration cannot be built
    and the approach point fails upstream of it; the clean points still compute (the aero twin is
    test_the_rv7_approach_point_needs_the_landing_deflection of test_mvp_chain_fleet.py)."""
    run = await run_fleet_chain(FleetMember.RV7, *SLUGS)
    assert all(run.outcome(slug) == Outcome(OK) for slug in APPROACH)
    without = await run_fleet_chain(FleetMember.RV7, *SLUGS, flaps=False)
    for slug in (*APPROACH, "roll-rate-approach"):
        assert without.outcome(slug) == LANDING_NEEDS_A_DEFLECTION, slug
    assert without.outcome("dihedral-effect-md") == Outcome(OK)
    assert without.outcome("stall-speed") == Outcome(OK)


@pytest.mark.parametrize("member", FLAPPED_PLAN_MODELS, ids=lambda m: m.name)
async def test_a_flapped_plan_model_computes_its_approach_once_it_gets_flap_deflections(
    member: FleetMember,
) -> None:
    """P8-F18 (1), the fast part: ALBATROS_4, GEE_BEE_R3, P39 and SPIRIT_100 have flaps and the
    fleet gives them no deflection, so the aero goldens record the approach as failed upstream of
    `airplane-landing`. With 15 / 30 deg as caller values the same cells compute. (The values with
    the real solvers, e.g. V_S,landing < V_S, are not recorded: aero tier.)"""
    recorded = [slug for slug, golden in GOLDEN[member].items() if isinstance(golden, Failed)]
    assert set(recorded) == {*APPROACH, "roll-rate-approach"}
    without = await run_fleet_chain(member, *SLUGS)
    deflections = {"flap-deflection-takeoff": 15.0, "flap-deflection-landing": 30.0}
    with_flaps = await run_fleet_chain(member, *SLUGS, "stall-speed-landing", values=deflections)
    for slug in recorded:
        assert without.outcome(slug) == LANDING_NEEDS_A_DEFLECTION, slug
        assert with_flaps.outcome(slug) == Outcome(OK), (slug, with_flaps.quantity(slug).error)
    assert with_flaps.quantity("stall-speed-landing").application == "landing"


def bryan_with_flaperons() -> dict[str, Any]:
    """BRYAN's document with the role of its aileron devices changed to `flaperon` (synthetic)."""
    document = reference_document(FleetMember.BRYAN)
    changed = 0
    for wing in cast("dict[str, Any]", document["wings"]).values():
        for section in cast("list[dict[str, Any]]", wing["x_secs"]):
            device = cast("dict[str, Any] | None", section.get("trailing_edge_device"))
            if device is not None and device["role"] == "aileron":
                device["role"] = "flaperon"
                changed += 1
    assert changed > 0
    return document


async def test_a_flaperon_bryan_rolls_and_lands_as_a_flap_and_has_no_butterfly() -> None:
    """P8-F18 (2) on a fleet document: a flaperon is a roll device and a flap (FLAP_ROLES), so the
    approach needs `flap-deflection-landing` (without it: upstream of `airplane-landing`) and the
    roll rate on approach computes with it; it is no separate flap, so the butterfly mix (Q35,
    `when: has_separate_flap_and_aileron`) is not applicable either way."""
    slugs = ("roll-rate-approach", "butterfly-max-mix")
    document = bryan_with_flaperons()
    without = await run_fleet_chain(FleetMember.BRYAN, *slugs, document=document)
    assert without.outcome("roll-rate-approach") == LANDING_NEEDS_A_DEFLECTION
    landing = {"flap-deflection-landing": 30.0}
    run = await run_fleet_chain(FleetMember.BRYAN, *slugs, document=document, values=landing)
    assert run.outcome("roll-rate-approach") == Outcome(OK)
    assert frozenset(run.worlds("roll-rate-approach")) == ROLL_RATE_WORLDS
    for result in (without, run):
        reason = result.quantity("butterfly-max-mix").reason
        assert result.outcome("butterfly-max-mix") == Outcome("not_applicable")
        assert reason is not None
        assert reason.code.value == "condition_not_met"
        assert "`has_separate_flap_and_aileron`" in reason.message
