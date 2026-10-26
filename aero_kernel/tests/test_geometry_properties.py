"""S_ref, b_ref and c_MAC of the main wing against AeroSandbox, built independently here.

The reference values are AeroSandbox's, of the wing with ``surface_type`` ``main_wing``
(maintainer, 2026-10-25, gh-1262): ``area(type="planform", include_centerline_distance=True)``,
``span(type="yz", include_centerline_distance=True)`` and ``mean_aerodynamic_chord()``. The expected values are taken from an ``asb.Wing`` that this module
builds itself from the document dict, so a defect of the kernel's conversion cannot hide in both.
"""

import importlib
import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.asb_airplane import main_wing_properties, surface_properties
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

pytestmark = pytest.mark.aero

TOLERANCE = 1e-12


def asb_values(wing: dict[str, Any]) -> tuple[float, float, float]:
    """(area, span with centreline distance, MAC) of an ``asb.Wing`` built from the document dict."""
    asb: Any = importlib.import_module("aerosandbox")
    built = asb.Wing(
        name=wing["name"],
        symmetric=wing["symmetric"],
        xsecs=[
            asb.WingXSec(
                xyz_le=s["xyz_le"],
                chord=s["chord"],
                twist=s["twist"],
                airfoil=asb.Airfoil("naca2412"),
            )
            for s in wing["x_secs"]
        ],
    )
    return (
        float(built.area(type="planform", include_centerline_distance=True)),
        float(built.span(type="yz", include_centerline_distance=True)),
        float(built.mean_aerodynamic_chord()),
    )


def properties_of(wing: dict[str, Any]) -> tuple[float, float, float]:
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    result = main_wing_properties(airplane)
    return result.s_ref, result.b_ref, result.c_mac


def agree(actual: tuple[float, ...], expected: tuple[float, ...]) -> bool:
    return all(math.isclose(a, e, rel_tol=TOLERANCE) for a, e in zip(actual, expected, strict=True))


def section(x: float, y: float, z: float, chord: float, twist: float = 0.0) -> dict[str, Any]:
    return {"xyz_le": [x, y, z], "chord": chord, "twist": twist, "airfoil": "naca2412"}


def wing_of(*sections: dict[str, Any], symmetric: bool = True) -> dict[str, Any]:
    return {
        "name": "Main",
        "symmetric": symmetric,
        "surface_type": "main_wing",
        "x_secs": list(sections),
    }


def polyhedral_twisted_wing(root_y: float = 0.0) -> dict[str, Any]:
    """Dihedral 8 deg (outer panel 14 deg), twist, sweep and an offset root: all that ASB feels."""
    rise = math.tan(math.radians(8.0))
    return wing_of(
        section(0.00, root_y, 0.0, 0.20, 2.0),
        section(0.03, root_y + 0.30, rise * 0.30, 0.15, -1.0),
        section(0.07, root_y + 0.70, rise * 0.30 + 0.25 * 0.4, 0.08, -3.0),
    )


@pytest.mark.parametrize("root_y", [0.0, 0.05])
def test_a_polyhedral_twisted_swept_wing_matches_asb_directly(root_y: float) -> None:
    wing = polyhedral_twisted_wing(root_y)
    assert agree(properties_of(wing), asb_values(wing))


def test_the_twist_and_dihedral_are_felt_as_asb_feels_them() -> None:
    """ASB measures along the quarter-chord line: the twist moves the values (not the old rule)."""
    flat = wing_of(section(0, 0, 0, 0.2, 0.0), section(0, 0.5, 0.0, 0.1, 0.0))
    twisted = wing_of(section(0, 0, 0, 0.2, 6.0), section(0, 0.5, 0.0, 0.1, 6.0))
    assert properties_of(twisted) != properties_of(flat)
    assert agree(properties_of(twisted), asb_values(twisted))


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_fleet_main_wing_matches_asb_directly(member: FleetMember) -> None:
    document = reference_document(member)
    airplane = AirplaneGeometry.model_validate(document)
    result = main_wing_properties(airplane)
    expected = asb_values(document["wings"][member.main_wing_name])
    assert agree((result.s_ref, result.b_ref, result.c_mac), expected)


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_frozen_fleet_reference_values_are_the_real_ones(member: FleetMember) -> None:
    """The fast tier uses ``FleetMember.reference``; this keeps it honest (same ASB, same values)."""
    result = main_wing_properties(AirplaneGeometry.model_validate(reference_document(member)))
    assert agree((result.s_ref, result.b_ref, result.c_mac), member.asb_reference)


def test_hand_values_of_a_single_trapezoid() -> None:
    """Half panel y 0..0.4 m, chord 0.2 -> 0.1 m, mirrored, flat, no twist.

    S = 2 * 0.4 * (0.2 + 0.1) / 2 = 0.12 m^2; b = 2 * 0.4 = 0.8 m;
    c_MAC = (2 / S) * 0.4 * (0.2^2 + 0.2*0.1 + 0.1^2) / 3 = 0.155556 m.
    """
    wing = wing_of(section(0, 0, 0, 0.2), section(0, 0.4, 0, 0.1))
    s_ref, b_ref, c_mac = properties_of(wing)
    assert math.isclose(s_ref, 0.12, rel_tol=1e-12)
    assert math.isclose(b_ref, 0.8, rel_tol=1e-12)
    assert math.isclose(c_mac, 2 / 0.12 * 0.4 * 0.07 / 3, rel_tol=1e-12)


def test_the_area_and_the_span_both_include_the_centreline_gap() -> None:
    """Root at y = 0.05 m (chord 0.3), tip at 0.45 m (chord 0.2), mirrored (gh-1262).

    The two panels 0.05 ... 0.45 give 2 * 0.4 * 0.25 = 0.2 m^2. ASB extrudes the root section to the
    centreline with the wing's geometric chord (0.25 m) as width, which adds 2 * 0.05 * 0.25 =
    0.025 m^2, so S = 0.225 m^2; the span is 2 * 0.45 = 0.9 m. Both describe the same planform.
    """
    s_ref, b_ref, _ = properties_of(wing_of(section(0, 0.05, 0, 0.3), section(0, 0.45, 0, 0.2)))
    assert math.isclose(s_ref, 0.225, rel_tol=1e-12)
    assert math.isclose(b_ref, 0.9, rel_tol=1e-12)


def test_a_wing_stored_on_the_negative_side_or_tip_first_has_the_same_values() -> None:
    reference = properties_of(wing_of(section(0, 0, 0, 0.3), section(0, 0.5, 0, 0.2)))
    negative = wing_of(section(0, 0, 0, 0.3), section(0, -0.5, 0, 0.2))
    tip_first = wing_of(section(0, 0.5, 0, 0.2), section(0, 0, 0, 0.3))
    assert agree(properties_of(negative), reference)
    assert agree(properties_of(tip_first), reference)


def test_a_wing_that_is_not_mirrored_counts_its_stored_side_once() -> None:
    one = wing_of(section(0, 0, 0, 0.2), section(0, 0.4, 0, 0.1), symmetric=False)
    assert agree(properties_of(one), asb_values(one))
    assert math.isclose(properties_of(one)[0], 0.06, rel_tol=1e-12)


def two_wing_airplane() -> AirplaneGeometry:
    """A tail listed first and the main wing second, so the choice cannot be 'the first wing'."""

    def sections(chords: tuple[float, float], half_span: float) -> list[dict[str, Any]]:
        return [section(0.0, y, 0.0, c) for y, c in zip((0.0, half_span), chords, strict=True)]

    return AirplaneGeometry.model_validate(
        {
            "name": "t",
            "wings": {
                "Tail": {
                    "name": "Tail",
                    "surface_type": "horizontal_tail",
                    "x_secs": sections((0.1, 0.05), 0.2),
                },
                "Main": {
                    "name": "Main",
                    "surface_type": "main_wing",
                    "x_secs": sections((0.2, 0.1), 0.4),
                },
            },
        }
    )


def test_the_main_wing_is_chosen_by_type_not_by_list_position() -> None:
    properties = main_wing_properties(two_wing_airplane())
    assert math.isclose(properties.s_ref, 0.12, rel_tol=1e-12)
    assert math.isclose(properties.b_ref, 0.8, rel_tol=1e-12)


def test_the_airplane_asb_builds_carries_the_same_values() -> None:
    """``asb.Airplane`` would take the tail (first wing); the kernel passes the main wing's values."""
    from aero_kernel.solvers.asb_airplane import to_asb_airplane

    airplane = to_asb_airplane(two_wing_airplane())
    properties = main_wing_properties(two_wing_airplane())
    assert (airplane.s_ref, airplane.b_ref, airplane.c_ref) == (
        properties.s_ref,
        properties.b_ref,
        properties.c_mac,
    )


@pytest.mark.parametrize("ys", [(0.2, 0.0, 0.3), (0.0, 0.3, 0.1)])
def test_a_chain_that_folds_back_in_y_is_unsupported(ys: tuple[float, ...]) -> None:
    wing = wing_of(*(section(0, y, 0, 0.2) for y in ys))
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    with pytest.raises(FormulaError) as raised:
        main_wing_properties(airplane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert "fold" in raised.value.message


def test_a_wing_count_other_than_one_is_an_internal_guard_not_an_input_error() -> None:
    """validate.py is the one producer of main_wing_count; here it would be a defect."""
    airplane = AirplaneGeometry.model_validate({"name": "t"})
    with pytest.raises(ValueError, match="exactly one main wing"):
        main_wing_properties(airplane)


def asb_surface(wing: dict[str, Any]) -> tuple[float, float, float, float, float]:
    """(area, span, AR = b^2/S, MAC, x_le_MAC = x_AC - 0.25 MAC) from an independently built asb.Wing."""
    asb: Any = importlib.import_module("aerosandbox")
    built = asb.Wing(
        name=wing["name"],
        symmetric=wing["symmetric"],
        xsecs=[
            asb.WingXSec(
                xyz_le=s["xyz_le"],
                chord=s["chord"],
                twist=s["twist"],
                airfoil=asb.Airfoil("naca2412"),
            )
            for s in wing["x_secs"]
        ],
    )
    area = float(built.area(type="planform", include_centerline_distance=True))
    span = float(built.span(type="yz", include_centerline_distance=True))
    mac = float(built.mean_aerodynamic_chord())
    x_ac = float(built.aerodynamic_center()[0])
    return area, span, span**2 / area, mac, x_ac - 0.25 * mac


def test_surface_properties_of_a_swept_polyhedral_twisted_wing_match_asb_directly() -> None:
    wing = polyhedral_twisted_wing()
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    found = surface_properties(airplane, "Main")
    assert agree(
        (found.area, found.span, found.aspect_ratio, found.c_mac, found.x_le_mac),
        asb_surface(wing),
    )


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_fleet_main_wing_and_tail_surfaces_match_asb_directly(member: FleetMember) -> None:
    document = reference_document(member)
    airplane = AirplaneGeometry.model_validate(document)
    for key in (member.main_wing_name, member.tail_name):
        found = surface_properties(airplane, key)
        assert agree(
            (found.area, found.span, found.aspect_ratio, found.c_mac, found.x_le_mac),
            asb_surface(document["wings"][key]),
        )


def test_a_rectangular_wing_has_its_leading_edge_as_x_le_mac() -> None:
    """Hand value: chord 0.2, leading edge x = 0.05: the AC is at 0.05 + 0.25 * 0.2, so x_le_MAC = 0.05."""
    wing = wing_of(section(0.05, 0, 0, 0.2), section(0.05, 0.7, 0, 0.2))
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    found = surface_properties(airplane, "Main")
    assert math.isclose(found.x_le_mac, 0.05, rel_tol=1e-12)
    assert math.isclose(found.aspect_ratio, 1.4**2 / 0.28, rel_tol=1e-12)
