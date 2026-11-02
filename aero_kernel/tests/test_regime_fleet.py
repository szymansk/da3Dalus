"""The regime warnings of the reference fleet at its stall estimate (#1342, ADR 0028 amended).

The speed is the stall estimate at C_L 1.4 at sea level, ``V = sqrt(2 m g / (rho S C_L))`` with the
fleet's mass and AeroSandbox's main-wing area. The fast test reads the MAC from the stand-in; the aero
test from AeroSandbox, the one producer.
"""

import math
from collections.abc import Sequence

import pytest
from aero_kernel.reference_fleet import FleetMember, aircraft_input
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.regime import SurfaceSections, regime_by_surface
from aero_kernel.tests.planform_stand_in import canon_bands, stand_in_surface_sections

RHO, MU, A, G = 1.225, 1.7894e-5, 340.294, 9.80665
CL_STALL_ESTIMATE = 1.4
OUTSIDE = "reynolds_outside_band"

# The surfaces whose Reynolds number at the MAC lies below 3e4 at the stall estimate (#1342).
BELOW_THE_BAND = {
    (FleetMember.BRYAN, "horizontal_tail"),
    (FleetMember.BRYAN, "vertical_tail"),
    (FleetMember.JAGUAR, "horizontal_tail"),
    (FleetMember.JAGUAR, "vertical_tail"),
    (FleetMember.BELEMNITOS, "v_tail"),
}


def stall_estimate(member: FleetMember) -> float:
    """The stall speed at C_L 1.4, sea level, in m/s."""
    area = member.asb_reference[0]
    return math.sqrt(2.0 * member.mass_kg * G / (RHO * area * CL_STALL_ESTIMATE))


def warnings_of(
    member: FleetMember, sections: dict[str, SurfaceSections]
) -> dict[str, list[KernelWarning]]:
    """The Reynolds warnings per surface type of the member at its stall estimate."""
    airplane = aircraft_input(member).airplane
    found = regime_by_surface(sections, stall_estimate(member), A, MU / RHO, canon_bands())
    types = {key: str(wing.surface_type) for key, wing in (airplane.wings or {}).items()}
    by_type: dict[str, list[KernelWarning]] = {t: [] for t in types.values()}
    for warning in found:
        if "wing" in warning.detail:
            by_type[types[str(warning.detail["wing"])]].append(warning)
    return by_type


def band_of(re_mac: float) -> str | None:
    """The surface code ADR 0028 (amended) gives a Reynolds number at the MAC."""
    if re_mac < 3e4:
        return OUTSIDE
    if re_mac < 7e4:
        return "reynolds_bubble_sensitive"
    return "reynolds_above_band" if re_mac > 1e6 else None


def assert_regime_per_surface(warnings: Sequence[KernelWarning], main_wing: str) -> None:
    """A fleet value's Reynolds warnings: present, each naming its surface, judged at the surface's
    MAC (never the main wing outside the band from its tip strips), the device ones naming the device."""
    reynolds = [w for w in warnings if w.code.startswith("reynolds_")]
    assert reynolds, "the fleet flies at low Reynolds number somewhere"
    for warning in reynolds:
        assert "wing" in warning.detail, warning
        if warning.code == "reynolds_outside_band_at_device":
            assert "device" in warning.detail, warning
            continue
        assert warning.code == band_of(float(warning.detail["re_mac"])), warning  # pyright: ignore[reportArgumentType]
    assert not [w for w in reynolds if w.code == OUTSIDE and w.detail["wing"] == main_wing]


def surface_codes(warnings: list[KernelWarning]) -> list[str]:
    """The surface warnings (not the device ones)."""
    return [w.code for w in warnings if "device" not in w.detail]


@pytest.mark.parametrize("member", list(FleetMember), ids=lambda m: m.name)
def test_only_the_small_tails_leave_the_band_at_their_mac(member: FleetMember) -> None:
    """No main wing carries reynolds_outside_band from its tip strips; BRYAN's and JAGUAR's tails
    and BELEMNITOS' V-tail do (stand-in MAC)."""
    sections = stand_in_surface_sections(aircraft_input(member).airplane)
    for surface_type, warnings in warnings_of(member, sections).items():
        below = (member, surface_type) in BELOW_THE_BAND
        assert (OUTSIDE in surface_codes(warnings)) is below, (member.name, surface_type)


@pytest.mark.aero
@pytest.mark.parametrize("member", list(FleetMember), ids=lambda m: m.name)
def test_aerosandbox_gives_the_same_verdicts(member: FleetMember) -> None:
    from aero_kernel.solvers.asb_airplane import surface_sections

    sections = surface_sections(aircraft_input(member).airplane)
    for surface_type, warnings in warnings_of(member, sections).items():
        below = (member, surface_type) in BELOW_THE_BAND
        assert (OUTSIDE in surface_codes(warnings)) is below, (member.name, surface_type)


@pytest.mark.aero
@pytest.mark.parametrize(
    ("member", "surface_type", "re_mac"),
    [
        (FleetMember.BRYAN, "main_wing", 45_148.0),
        (FleetMember.BRYAN, "horizontal_tail", 27_415.0),
        (FleetMember.JAGUAR, "horizontal_tail", 20_446.0),
        (FleetMember.BELEMNITOS, "v_tail", 19_730.0),
        (FleetMember.WIESEL, "main_wing", 79_432.0),
    ],
)
def test_the_reynolds_number_at_the_mac_is_the_measured_one(
    member: FleetMember, surface_type: str, re_mac: float
) -> None:
    """The values measured for the issue with AeroSandbox's MAC (#1342), to 0.1 %."""
    from aero_kernel.solvers.asb_airplane import surface_sections

    airplane = aircraft_input(member).airplane
    (key,) = [k for k, w in (airplane.wings or {}).items() if w.surface_type == surface_type]
    sections = surface_sections(airplane)[key]
    found = stall_estimate(member) * sections.c_mac_m / (MU / RHO)
    assert math.isclose(found, re_mac, rel_tol=1e-3)
