"""S_ref, b_ref and c_MAC of the main wing against an independent numerical integration.

The reference values are the sections' chords and leading edges as given, projected onto the x-y
plane (maintainer 2026-10-22); twist does not change them. The independent computation
samples the piecewise-linear chord ``c(y)`` of the reference planform on a fine grid and
integrates it with the trapezoid rule; it shares no formula with the function under test.
Tolerance: relative 1e-7 (the sampling error is below 1e-9).
"""

import math
from bisect import bisect_right
from itertools import pairwise
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import main_wing_properties
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

TOLERANCE = 1e-7
SAMPLES = 100_001


def numeric_projected(wing: dict[str, Any]) -> tuple[float, float, float]:
    """(S, b, c_MAC) of the reference planform, by sampling c(y) on a fine y grid.

    Independent of the adapter's panel formulas and of its handling of the centreline: the
    chord is interpolated between the sections (and held at the root chord inboard of the root),
    sampled at 100001 points over the planform and integrated with the trapezoid rule.

    - A mirrored wing is carried to the centreline: the grid runs from y = 0 to the outermost
      section (the stored side flipped to y >= 0), and S, b are doubled.
    - A wing that is not mirrored keeps its stored extent: the grid runs from its smallest to
      its largest y.
    """
    points = sorted((s["xyz_le"][1], s["chord"]) for s in wing["x_secs"])
    mirrored = wing["symmetric"]
    if mirrored and abs(points[0][0]) > abs(points[-1][0]):
        points = sorted((-y, c) for y, c in points)
    ys = [y for y, _ in points]
    low = 0.0 if mirrored else ys[0]
    high = ys[-1]

    def chord(y: float) -> float:
        if y <= ys[0]:
            return points[0][1]
        k = bisect_right(ys, y)
        (y1, c1), (y2, c2) = points[k - 1], points[min(k, len(points) - 1)]
        return c1 if y2 == y1 else c1 + (c2 - c1) * (y - y1) / (y2 - y1)

    step = (high - low) / (SAMPLES - 1)
    values = [chord(low + k * step) for k in range(SAMPLES)]
    area = step * (sum(values) - (values[0] + values[-1]) / 2.0)
    squares = step * (sum(v * v for v in values) - (values[0] ** 2 + values[-1] ** 2) / 2.0)
    factor = 2.0 if mirrored else 1.0
    return factor * area, factor * (high - low), squares / area


def planform_area(wing: dict[str, Any]) -> float:
    """The area measured along the panels (slant length times mean chord), for contrast."""
    total = 0.0
    sections = wing["x_secs"]
    for inner, outer in pairwise(sections):
        slant = math.dist(inner["xyz_le"][1:], outer["xyz_le"][1:])
        total += slant * (inner["chord"] + outer["chord"]) / 2.0
    return (2.0 if wing["symmetric"] else 1.0) * total


def dihedral_wing(degrees: float) -> dict[str, Any]:
    """A three-section symmetric wing with a constant dihedral, no twist."""
    rise = math.tan(math.radians(degrees))
    sections = [
        {"xyz_le": [0.02 * y, y, rise * y], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
        for y, c in ((0.0, 0.2), (0.3, 0.15), (0.7, 0.08))
    ]
    return {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}


def properties_of(wing: dict[str, Any]) -> tuple[float, float, float]:
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    result = main_wing_properties(airplane)
    return result.s_ref, result.b_ref, result.c_mac


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=TOLERANCE)


@pytest.mark.parametrize("degrees", [0.0, 8.0])
def test_a_synthetic_wing_matches_the_numerical_integration(degrees: float) -> None:
    wing = dihedral_wing(degrees)
    expected = numeric_projected(wing)
    assert all(close(a, e) for a, e in zip(properties_of(wing), expected, strict=True))


def test_the_projected_and_the_planform_area_are_distinguished_at_8_degrees() -> None:
    wing = dihedral_wing(8.0)
    s_ref, _, _ = properties_of(wing)
    ratio = planform_area(wing) / s_ref
    assert ratio > 1.009  # 1 / cos(8 deg) = 1.0098
    assert close(s_ref, numeric_projected(wing)[0])


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_fleet_main_wing_matches_the_numerical_integration(member: FleetMember) -> None:
    document = reference_document(member)
    wing = document["wings"]["Tragflaeche"]
    airplane = AirplaneGeometry.model_validate(document)
    result = main_wing_properties(airplane)
    s_ref, b_ref, c_mac = numeric_projected(wing)
    assert close(result.s_ref, s_ref)
    assert close(result.b_ref, b_ref)
    assert close(result.c_mac, c_mac)


def twisted(wing: dict[str, Any], degrees: float) -> dict[str, Any]:
    """The same wing with every section twisted by ``degrees``."""
    return {**wing, "x_secs": [{**s, "twist": degrees} for s in wing["x_secs"]]}


@pytest.mark.parametrize("degrees", [0.0, 8.0])
def test_twisting_the_sections_changes_no_reference_value(degrees: float) -> None:
    """Twist does not change the reference planform, with or without dihedral."""
    wing = dihedral_wing(degrees)
    assert properties_of(twisted(wing, 5.0)) == properties_of(wing)


def test_twisting_the_reference_fleet_changes_no_reference_value() -> None:
    wing = reference_document(FleetMember.BRYAN)["wings"]["Tragflaeche"]
    assert properties_of(twisted(wing, 0.0)) == properties_of(wing)


def test_a_wing_stored_on_the_negative_side_has_the_same_values() -> None:
    wing = dihedral_wing(3.0)
    mirrored = {
        **wing,
        "x_secs": [
            {**s, "xyz_le": [s["xyz_le"][0], -s["xyz_le"][1], s["xyz_le"][2]]}
            for s in wing["x_secs"]
        ],
    }
    assert properties_of(mirrored) == properties_of(wing)


def test_a_wing_that_is_not_mirrored_counts_its_stored_side_once() -> None:
    wing = {**dihedral_wing(0.0), "symmetric": False}
    s_ref, b_ref, c_mac = properties_of(wing)
    s_sym, b_sym, c_sym = properties_of(dihedral_wing(0.0))
    assert close(s_ref, s_sym / 2)
    assert close(b_ref, b_sym / 2)
    assert close(c_mac, c_sym)


def test_hand_values_of_a_single_trapezoid() -> None:
    """Half panel y 0..0.4 m, chord 0.2 -> 0.1 m, mirrored.

    S = 2 * 0.4 * (0.2 + 0.1) / 2 = 0.12 m^2; b = 2 * 0.4 = 0.8 m;
    c_MAC = (2 / S) * 0.4 * (0.2^2 + 0.2*0.1 + 0.1^2) / 3 = 0.155556 m.
    """
    sections = [
        {"xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"},
        {"xyz_le": [0.0, 0.4, 0.0], "chord": 0.1, "twist": 0.0, "airfoil": "naca2412"},
    ]
    wing = {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}
    s_ref, b_ref, c_mac = properties_of(wing)
    assert close(s_ref, 0.12)
    assert close(b_ref, 0.8)
    assert close(c_mac, 2 / 0.12 * 0.4 * 0.07 / 3)


def test_a_main_wing_without_projected_area_is_unsupported() -> None:
    """A vertical main wing (all sections at the same y) has no projected planform."""
    sections = [
        {"xyz_le": [0.0, 0.0, z], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
        for z in (0.0, 0.5)
    ]
    wing = {"name": "Main", "symmetric": True, "surface_type": "main_wing", "x_secs": sections}
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    with pytest.raises(FormulaError) as raised:
        main_wing_properties(airplane)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def two_wing_airplane() -> AirplaneGeometry:
    """A tail listed first and the main wing second, so the choice cannot be 'the first wing'."""

    def sections(chords: tuple[float, float], half_span: float) -> list[dict[str, Any]]:
        return [
            {"xyz_le": [0.0, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
            for y, c in zip((0.0, half_span), chords, strict=True)
        ]

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


def test_the_main_wing_properties_are_those_of_the_main_wing_not_the_first_wing() -> None:
    """Tail: half panel 0.2 m, chords 0.1 -> 0.05; Main: 0.4 m, 0.2 -> 0.1 (S 0.12, b 0.8)."""
    properties = main_wing_properties(two_wing_airplane())
    assert math.isclose(properties.s_ref, 0.12, rel_tol=1e-12)
    assert math.isclose(properties.b_ref, 0.8, rel_tol=1e-12)
    assert math.isclose(properties.c_mac, 0.07 * 0.4 / 3 / 0.06, rel_tol=1e-12)


def wing_of(symmetric: bool, *sections: tuple[float, float]) -> dict[str, Any]:
    """A wing from (y, chord) pairs, in the order given (root first)."""
    return {
        "name": "Main",
        "symmetric": symmetric,
        "surface_type": "main_wing",
        "x_secs": [
            {"xyz_le": [0.0, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca2412"}
            for y, c in sections
        ],
    }


def test_a_root_beyond_the_centreline_is_clipped_at_y_zero() -> None:
    """Root y = -0.1 m (chord 0.3), tip y = 0.4 m (chord 0.2), mirrored.

    The chord at y = 0 is 0.3 - 0.1 * 0.1 / 0.5 = 0.28; the planform 0..0.4 has the half area
    0.4 * (0.28 + 0.2) / 2 = 0.096, so S = 0.192 m^2 and b = 2 * 0.4 = 0.8 m;
    integral c^2 = 0.4 * (0.28^2 + 0.28*0.2 + 0.2^2) / 3 = 0.0232533, c_MAC = 0.242222 m.
    """
    wing = wing_of(True, (-0.1, 0.3), (0.4, 0.2))
    s_ref, b_ref, c_mac = properties_of(wing)
    assert math.isclose(s_ref, 0.192, rel_tol=1e-12)
    assert math.isclose(b_ref, 0.8, rel_tol=1e-12)
    assert math.isclose(c_mac, 0.0232533333333 / 0.096, rel_tol=1e-9)
    assert all(
        close(a, e) for a, e in zip((s_ref, b_ref, c_mac), numeric_projected(wing), strict=True)
    )


def test_a_root_off_the_centreline_is_carried_to_it_with_the_root_chord() -> None:
    """Root y = 0.05 m (chord 0.3), tip y = 0.45 m (chord 0.2), mirrored.

    Half area = 0.05 * 0.3 + 0.4 * 0.25 = 0.115, so S = 0.23 m^2 and b = 2 * 0.45 = 0.9 m;
    integral c^2 = 0.05 * 0.09 + 0.4 * (0.09 + 0.06 + 0.04) / 3 = 0.0298333, c_MAC = 0.259420 m.
    """
    wing = wing_of(True, (0.05, 0.3), (0.45, 0.2))
    s_ref, b_ref, c_mac = properties_of(wing)
    assert math.isclose(s_ref, 0.23, rel_tol=1e-12)
    assert math.isclose(b_ref, 0.9, rel_tol=1e-12)
    assert math.isclose(c_mac, 0.0298333333333 / 0.115, rel_tol=1e-9)
    assert all(
        close(a, e) for a, e in zip((s_ref, b_ref, c_mac), numeric_projected(wing), strict=True)
    )


def test_the_same_wing_stored_on_the_negative_side_has_the_same_values() -> None:
    assert properties_of(wing_of(True, (-0.05, 0.3), (-0.45, 0.2))) == properties_of(
        wing_of(True, (0.05, 0.3), (0.45, 0.2))
    )


def test_a_wing_that_is_not_mirrored_keeps_its_stored_extent_across_y_zero() -> None:
    """y -0.1 .. 0.4 m, chord 0.3 -> 0.2, not mirrored: no clipping, no extension.

    b = 0.5 m, S = 0.5 * 0.25 = 0.125 m^2, integral c^2 = 0.5 * (0.09 + 0.06 + 0.04) / 3.
    """
    wing = wing_of(False, (-0.1, 0.3), (0.4, 0.2))
    s_ref, b_ref, c_mac = properties_of(wing)
    assert math.isclose(s_ref, 0.125, rel_tol=1e-12)
    assert math.isclose(b_ref, 0.5, rel_tol=1e-12)
    assert math.isclose(c_mac, 0.5 * 0.19 / 3 / 0.125, rel_tol=1e-12)
    assert all(
        close(a, e) for a, e in zip((s_ref, b_ref, c_mac), numeric_projected(wing), strict=True)
    )


@pytest.mark.parametrize("symmetric", [True, False])
@pytest.mark.parametrize("ys", [(0.2, 0.0, 0.3), (0.0, 0.3, 0.1), (0.0, 0.3, -0.1)])
def test_a_chain_that_folds_back_in_y_is_unsupported(
    symmetric: bool, ys: tuple[float, ...]
) -> None:
    """The planform would be counted twice where the chain doubles back."""
    wing = wing_of(symmetric, *((y, 0.2) for y in ys))
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


def full(wing: dict[str, Any]) -> Any:  # the properties model, read by attribute
    airplane = AirplaneGeometry.model_validate({"name": "t", "wings": {"Main": wing}})
    return main_wing_properties(airplane)


@pytest.mark.parametrize("ys", [(0.5, 0.3, 0.0), (0.0, 0.3, 0.5)])
def test_a_mirrored_wing_stored_tip_first_is_no_fold(ys: tuple[float, ...]) -> None:
    """Only a genuine fold back is rejected; the direction of the chain is free."""
    reference = properties_of(wing_of(True, (0.0, 0.3), (0.3, 0.25), (0.5, 0.2)))
    chords = {0.0: 0.3, 0.3: 0.25, 0.5: 0.2}
    assert properties_of(wing_of(True, *((y, chords[y]) for y in ys))) == reference


def test_a_mirrored_wing_stored_tip_first_on_the_negative_side_is_no_fold() -> None:
    reference = properties_of(wing_of(True, (0.0, 0.3), (0.3, 0.25), (0.5, 0.2)))
    assert properties_of(wing_of(True, (-0.5, 0.2), (-0.3, 0.25), (0.0, 0.3))) == reference
    assert properties_of(wing_of(True, (0.0, 0.3), (-0.3, 0.25), (-0.5, 0.2))) == reference


def test_the_centreline_changes_are_reported_in_metres() -> None:
    assert (
        full(wing_of(True, (0.0, 0.3), (0.4, 0.2))).extended_m,
        full(wing_of(True, (0.0, 0.3), (0.4, 0.2))).clipped_m,
    ) == (0.0, 0.0)
    extended = full(wing_of(True, (0.05, 0.3), (0.45, 0.2)))
    assert (extended.extended_m, extended.clipped_m) == (0.05, 0.0)
    clipped = full(wing_of(True, (-0.1, 0.3), (0.4, 0.2)))
    assert (clipped.extended_m, clipped.clipped_m) == (0.0, 0.1)
    kept = full(wing_of(False, (-0.1, 0.3), (0.4, 0.2)))
    assert (kept.extended_m, kept.clipped_m) == (0.0, 0.0)
