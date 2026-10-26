"""The fleet helpers that the aero-tier tests rely on, checked without a solver."""

import pytest
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.schema import QuantityResult, QuantityStatus
from aero_kernel.tests.reference_fleet import (
    FUSELAGE_REJECTED,
    FleetMember,
    assert_rejected_for_the_fuselage,
    flap_values,
)
from pydantic import JsonValue

UPSTREAM_DETAIL: dict[str, JsonValue] = {
    "causes": [{"quantity": "airplane-aerobuildup", "code": "unsupported_configuration"}]
}


def fuselage_error(member: FleetMember) -> QuantityResult:
    """The error the kernel records for a fuselage section with two shape exponents."""
    name, section = FUSELAGE_REJECTED[member]
    error = KernelError(
        code="unsupported_configuration",
        category=ErrorCategory.UNSUPPORTED_CONFIGURATION,
        message=(
            f"section {section} of the fuselage '{name}' has n_lower != n; "
            "AeroSandbox has one shape exponent per section"
        ),
        hint="a hint",
        detail={"fuselage": name},
    )
    return QuantityResult(slug="root", status=QuantityStatus.ERROR, error=error)


def waiting() -> QuantityResult:
    """A quantity that only waits for another one that failed."""
    error = KernelError(
        code="upstream_failed",
        category=ErrorCategory.UPSTREAM_FAILED,
        message="upstream failed",
        hint="a hint",
        retryable=False,
        escalate=False,
        detail=UPSTREAM_DETAIL,
    )
    return QuantityResult(slug="waits", status=QuantityStatus.ERROR, error=error)


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


@pytest.mark.parametrize("member", list(FUSELAGE_REJECTED))
def test_the_fuselage_error_and_its_followers_pass(member: FleetMember) -> None:
    assert_rejected_for_the_fuselage(member, [fuselage_error(member), waiting()])


def test_only_followers_pass_when_no_root_is_required() -> None:
    assert_rejected_for_the_fuselage(FleetMember.CHEKKER, [waiting()], rooted=False)


def test_only_followers_fail_when_a_root_is_required() -> None:
    quantities = [waiting()]
    with pytest.raises(AssertionError, match="no quantity carries the fuselage error itself"):
        assert_rejected_for_the_fuselage(FleetMember.CHEKKER, quantities)


def test_a_value_is_not_a_fuselage_rejection() -> None:
    quantities = [
        QuantityResult(
            slug="v", unit="m", status=QuantityStatus.OK, value=1.0, tool="GEO", application="a"
        )
    ]
    with pytest.raises(AssertionError, match="v"):
        assert_rejected_for_the_fuselage(FleetMember.CHEKKER, quantities)
