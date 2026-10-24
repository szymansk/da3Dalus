"""Per-surface geometry: the one function for the main wing and the tail (ADR 0022, #1203 S3)."""

import math
from bisect import bisect_right

import pytest
from aero_kernel.geometry import AirplaneGeometry, Wing
from aero_kernel.geometry_properties import main_wing_properties, surface_properties
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

SAMPLES = 100_001


def wing_of(*sections: tuple[float, float, float], symmetric: bool = True) -> Wing:
    """A wing from (y, chord, x_le) triples, root first."""
    return Wing.model_validate(
        {
            "name": "W",
            "symmetric": symmetric,
            "surface_type": "horizontal_tail",
            "x_secs": [
                {"xyz_le": [x, y, 0.0], "chord": c, "twist": 0.0, "airfoil": "naca0012"}
                for y, c, x in sections
            ],
        }
    )


def sampled_x_le_mac(points: list[tuple[float, float, float]], low: float, high: float) -> float:
    """integral(c x_le dy) / integral(c dy) on a fine grid; c and x_le interpolated, held inboard."""
    ys = [p[0] for p in points]

    def at(y: float, index: int) -> float:
        if y <= ys[0]:
            return points[0][index]
        k = bisect_right(ys, y)
        (y1, *v1), (y2, *v2) = points[k - 1], points[min(k, len(points) - 1)]
        value1, value2 = v1[index - 1], v2[index - 1]
        return value1 if y2 == y1 else value1 + (value2 - value1) * (y - y1) / (y2 - y1)

    step = (high - low) / (SAMPLES - 1)
    grid = [low + k * step for k in range(SAMPLES)]
    chords = [at(y, 1) for y in grid]
    moment = [c * at(y, 2) for y, c in zip(grid, chords, strict=True)]

    def trapezoid(values: list[float]) -> float:
        return step * (sum(values) - (values[0] + values[-1]) / 2.0)

    return trapezoid(moment) / trapezoid(chords)


def test_a_single_panel_tail_has_the_hand_values() -> None:
    """Half panel y 0..0.2 m, chord 0.10 -> 0.05 m, leading edge x 0.50 -> 0.52 m, mirrored.

    area = 2 * 0.2 * 0.075 = 0.03 m^2; span 0.4 m; AR = 0.16 / 0.03 = 5.3333;
    c_MAC = (2/3)(0.01 + 0.005 + 0.0025)/(0.15) = 0.077778 m;
    the leading edge of the MAC lies at the chord-weighted station:
    x_le_MAC = 0.50 + 0.02 (c1 + 2 c2) / (3 (c1 + c2)) = 0.50 + 0.02 * 0.2 / 0.45 = 0.508889 m.
    """
    properties = surface_properties(wing_of((0.0, 0.10, 0.50), (0.2, 0.05, 0.52)))
    assert math.isclose(properties.area, 0.03, rel_tol=1e-12)
    assert math.isclose(properties.span, 0.4, rel_tol=1e-12)
    assert math.isclose(properties.aspect_ratio, 0.16 / 0.03, rel_tol=1e-12)
    assert math.isclose(properties.c_mac, 2 / 3 * 0.0175 / 0.15, rel_tol=1e-12)
    assert math.isclose(properties.x_le_mac, 0.50 + 0.02 * 0.2 / 0.45, rel_tol=1e-12)
    assert (properties.extended_m, properties.clipped_m) == (0.0, 0.0)


def test_a_straight_untapered_wing_has_its_leading_edge_as_x_le_mac() -> None:
    properties = surface_properties(wing_of((0.0, 0.2, 0.3), (0.5, 0.2, 0.3)))
    assert math.isclose(properties.x_le_mac, 0.3, rel_tol=1e-12)
    assert math.isclose(properties.c_mac, 0.2, rel_tol=1e-12)


@pytest.mark.parametrize(
    "sections",
    [
        [(0.0, 0.2, 0.0), (0.3, 0.15, 0.04), (0.7, 0.08, 0.1)],
        [(0.05, 0.3, 0.1), (0.45, 0.2, 0.3)],  # root off the centreline: extended with the root
        [(-0.1, 0.3, 0.0), (0.4, 0.2, 0.2)],  # a side crossing y = 0: clipped there
    ],
)
def test_x_le_mac_equals_the_sampled_chord_weighted_leading_edge(
    sections: list[tuple[float, float, float]],
) -> None:
    """Independent of the panel formulas: a fine-grid integration of c x_le / c over the reference
    planform (0 ... max y, the root held inboard of the first section; the clipped side from 0)."""
    properties = surface_properties(wing_of(*sections))
    expected = sampled_x_le_mac(sections, 0.0, max(y for y, _, _ in sections))
    assert math.isclose(properties.x_le_mac, expected, rel_tol=1e-7)


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_main_wing_values_are_unchanged_through_surface_properties(
    member: FleetMember,
) -> None:
    """One authority for S_ref, b_ref and c_MAC (ADR 0022)."""
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    (main,) = [w for w in (airplane.wings or {}).values() if w.surface_type == "main_wing"]
    surface = surface_properties(main)
    reference = main_wing_properties(airplane)
    assert (surface.area, surface.span, surface.c_mac) == (
        reference.s_ref,
        reference.b_ref,
        reference.c_mac,
    )
    assert (surface.extended_m, surface.clipped_m) == (reference.extended_m, reference.clipped_m)


@pytest.mark.parametrize("member", list(FleetMember))
def test_the_fleet_tails_have_a_sane_mac_inside_their_own_chords(member: FleetMember) -> None:
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    (tail,) = [w for w in (airplane.wings or {}).values() if w.surface_type == "horizontal_tail"]
    surface = surface_properties(tail)
    chords = [s.chord for s in tail.x_secs]
    assert min(chords) < surface.c_mac < max(chords)
    leading_edges = [s.xyz_le[0] for s in tail.x_secs]
    assert min(leading_edges) <= surface.x_le_mac <= max(leading_edges)
    assert surface.aspect_ratio > 1.0


def test_surface_properties_of_a_vertical_surface_is_unsupported() -> None:
    from aero_kernel.errors import ErrorCategory, FormulaError

    fin = Wing.model_validate(
        {
            "name": "Fin",
            "symmetric": False,
            "surface_type": "vertical_tail",
            "x_secs": [
                {"xyz_le": [0.5, 0.0, z], "chord": 0.1, "twist": 0.0, "airfoil": "naca0012"}
                for z in (0.0, 0.2)
            ],
        }
    )
    with pytest.raises(FormulaError) as raised:
        surface_properties(fin)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
