"""The fleet helpers that the aero-tier tests rely on, checked without a solver."""

import pytest
from aero_kernel.tests.reference_fleet import (
    FleetMember,
    flap_values,
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
