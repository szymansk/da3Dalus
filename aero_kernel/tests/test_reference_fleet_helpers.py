"""The fleet helpers that the aero-tier tests rely on, checked without a solver."""

import pytest
from aero_kernel.reference_fleet import (
    FleetMember,
    aircraft_input,
    flap_values,
    fleet_values,
)


@pytest.mark.parametrize("member", list(FleetMember))
def test_every_member_names_one_main_wing(member: FleetMember) -> None:
    assert member.main_wing_name == member.wing_name("main_wing")


@pytest.mark.parametrize("member", list(FleetMember))
def test_every_member_names_one_pitch_trimming_tail(member: FleetMember) -> None:
    """A horizontal tail, or BELEMNITOS's V-tail."""
    assert member.tail_name


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
