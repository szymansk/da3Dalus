"""The fleet helpers that the aero-tier tests rely on, checked without a solver."""

import pytest
from aero_kernel.reference_fleet import (
    FleetMember,
    aircraft_input,
    flap_values,
    fleet_values,
)
from aero_kernel.tests.reference_fleet import (
    MVP_FLEET,
    PLAN_BATCH,
    TAILLESS,
    VALIDATION,
    WITH_PITCH_TAIL,
)
from aero_kernel.tests.test_mvp_chain_fleet import RUDDER_ONLY, WITHOUT_TURN_SIDESLIP
from aero_kernel.tests.test_plan_batch_fleet import GOLDEN, SLUGS, Failed

# Every error the plan-batch goldens pin that is not a consequence of another one, with the issue
# that owns it (P8-F02). Recording a new one needs an entry here, so somebody decides it.
ROOT_ERROR_ISSUES: dict[tuple[FleetMember, str], str] = {
    # AVL's lateral run gives no derivatives
    (FleetMember.MINI_FUNTANA, "internal"): "#1373",
    # the neutral point of a tailless aircraft (ARCHITECTURE: "open: #1206 tailless")
    (FleetMember.VOODOO, "unsupported_layout"): "#1206",
    (FleetMember.WINDFREAK, "unsupported_layout"): "#1206",
}
# A pinned root error that no issue owns yet. None at present: the stall of AERONCA_CHAMP
# (`not_converged`, the optimum on the alpha bound) computes since gh-1423.
ROOT_ERRORS_AWAITING_AN_ISSUE: set[tuple[FleetMember, str]] = set()
# Not a defect: the fleet gives these flapped aircraft no flap deflection (FLAP_DEFLECTIONS_DEG),
# so the landing configuration lacks its input.
FLAPS_WITHOUT_A_DEFLECTION = {
    (member, "missing_input")
    for member in (
        FleetMember.ALBATROS_4,
        FleetMember.GEE_BEE_R3,
        FleetMember.P39,
        FleetMember.SPIRIT_100,
    )
}


@pytest.mark.parametrize("member", list(FleetMember))
def test_every_member_names_one_main_wing(member: FleetMember) -> None:
    assert member.main_wing_name == member.wing_name("main_wing")


@pytest.mark.parametrize("member", WITH_PITCH_TAIL)
def test_every_member_with_a_tail_names_one_pitch_trimming_tail(member: FleetMember) -> None:
    """A horizontal tail, or the V-tail of BELEMNITOS, ALBATROS_4 and BARRACUDA."""
    assert member.tail_name


@pytest.mark.parametrize("member", TAILLESS)
def test_a_flying_wing_has_no_pitch_trimming_tail(member: FleetMember) -> None:
    with pytest.raises(ValueError, match="not enough values to unpack"):
        _ = member.tail_name


def test_the_fleet_is_the_first_six_the_plan_batch_and_the_validation_aircraft() -> None:
    assert len(MVP_FLEET) == 6
    assert len(PLAN_BATCH) == 28
    assert VALIDATION == (FleetMember.AVISTAR_ELITE, FleetMember.ULTRA_STICK_120)
    assert set(MVP_FLEET) | set(PLAN_BATCH) | set(VALIDATION) == set(FleetMember)
    assert len(MVP_FLEET) + len(PLAN_BATCH) + len(VALIDATION) == len(FleetMember)


def test_only_rv7_takes_flap_deflections() -> None:
    assert flap_values(FleetMember.RV7) == {
        "flap-deflection-takeoff": 15.0,
        "flap-deflection-landing": 30.0,
    }
    assert flap_values(FleetMember.BRYAN) == {}


def test_flap_values_are_a_copy() -> None:
    flap_values(FleetMember.RV7)["flap-deflection-landing"] = 0.0
    assert flap_values(FleetMember.RV7)["flap-deflection-landing"] == 30.0


def test_fleet_ids_are_unique_lower_case_names() -> None:
    ids = [member.fleet_id for member in FleetMember]
    assert len(set(ids)) == len(ids)
    assert "rv-7" in ids
    assert FleetMember.RV7.display_name == "RV-7"
    assert FleetMember.BRYAN.display_name == "BRYAN"


@pytest.mark.parametrize("member", list(FleetMember))
def test_a_member_is_found_by_its_id(member: FleetMember) -> None:
    assert FleetMember.from_fleet_id(member.fleet_id) is member


def test_an_unknown_id_finds_no_member() -> None:
    assert FleetMember.from_fleet_id("nonexistent") is None


def test_fleet_values_are_the_mass_and_the_flap_deflections() -> None:
    assert fleet_values(FleetMember.BRYAN) == {"aircraft-mass": 0.151}
    assert fleet_values(FleetMember.RV7) == {
        "aircraft-mass": 0.5,
        "flap-deflection-takeoff": 15.0,
        "flap-deflection-landing": 30.0,
    }


def test_the_aircraft_input_overlays_the_callers_values_on_the_fleet_values() -> None:
    aircraft = aircraft_input(FleetMember.RV7, {"aircraft-mass": 0.7, "altitude": 100.0})
    assert aircraft.values == {
        "aircraft-mass": 0.7,
        "altitude": 100.0,
        "flap-deflection-takeoff": 15.0,
        "flap-deflection-landing": 30.0,
    }
    wings = aircraft.airplane.wings
    assert wings is not None
    assert FleetMember.RV7.main_wing_name in wings


def test_every_member_of_the_batch_has_its_golden() -> None:
    """Moved here from the aero-marked test_plan_batch_fleet.py: data only, so the PR run sees it."""
    assert set(GOLDEN) == set(PLAN_BATCH)
    assert all(tuple(golden) == SLUGS for golden in GOLDEN.values())


def test_the_fleet_has_members_with_and_without_a_roll_device() -> None:
    """Moved here from the aero-marked test_mvp_chain_fleet.py: data only."""
    assert FleetMember.CHEKKER in RUDDER_ONLY
    assert FleetMember.BRYAN in WITHOUT_TURN_SIDESLIP
    assert len(WITHOUT_TURN_SIDESLIP) + len(RUDDER_ONLY) == len(FleetMember)


def root_errors_of_the_plan_batch() -> set[tuple[FleetMember, str]]:
    """``(member, code)`` of every pinned error that is not ``upstream_failed``, and of every cause."""
    found: set[tuple[FleetMember, str]] = set()
    for member, cells in GOLDEN.items():
        failed = [golden for golden in cells.values() if isinstance(golden, Failed)]
        codes = {golden.code for golden in failed}
        codes |= {code for golden in failed for _quantity, code in golden.causes}
        found |= {(member, code) for code in codes if code != "upstream_failed"}
    return found


def test_every_error_pinned_as_a_golden_is_registered() -> None:
    """A golden may pin an error (the kernel's answer is recorded, never repaired), but only a known
    one: `internal` for a new aircraft cannot be recorded without a line in the register."""
    registered = set(ROOT_ERROR_ISSUES) | ROOT_ERRORS_AWAITING_AN_ISSUE | FLAPS_WITHOUT_A_DEFLECTION
    assert root_errors_of_the_plan_batch() == registered


@pytest.mark.parametrize("issue", sorted(set(ROOT_ERROR_ISSUES.values())))
def test_a_registered_error_names_an_issue_number(issue: str) -> None:
    assert issue.startswith("#")
    assert issue[1:].isdigit()


def test_the_internal_error_of_the_batch_is_the_one_of_bug_1373() -> None:
    """13 lateral cells of MINI_FUNTANA, no other `internal` anywhere in the goldens."""
    internal = {
        (member, slug)
        for member, cells in GOLDEN.items()
        for slug, golden in cells.items()
        if isinstance(golden, Failed) and golden.code == "internal"
    }
    assert {member for member, _slug in internal} == {FleetMember.MINI_FUNTANA}
    assert len(internal) == 13
    assert ROOT_ERROR_ISSUES[(FleetMember.MINI_FUNTANA, "internal")] == "#1373"
