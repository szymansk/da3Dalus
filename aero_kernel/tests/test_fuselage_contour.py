"""The closed point contour of a fuselage section and its rules (#1349, maintainer 2026-11-04)."""

import math

from aero_kernel.fuselage_contour import contour_defect, contour_set_defects, is_degenerate

MIN_POINTS = 3

Contour = list[tuple[float, float]]


def ellipse(a: float, b: float, count: int = 16) -> Contour:
    """The full ellipse (a, b), counter-clockwise from the bottom centre, ``count`` points."""
    return [
        (
            a * math.cos(-math.pi / 2 + 2 * math.pi * i / count),
            b * math.sin(-math.pi / 2 + 2 * math.pi * i / count),
        )
        for i in range(count)
    ]


# A former with a wing-saddle notch cut into the bottom: concave, counter-clockwise.
SADDLE: Contour = [
    (0.0, -0.03),
    (0.02, -0.03),
    (0.02, -0.045),
    (0.03, -0.045),
    (0.03, 0.02),
    (0.0, 0.05),
    (-0.03, 0.02),
    (-0.03, -0.045),
    (-0.02, -0.045),
    (-0.02, -0.03),
]

# A lopsided former: wider on the right, with an offset canopy.
ASYMMETRIC: Contour = [
    (0.0, -0.04),
    (0.035, -0.02),
    (0.03, 0.02),
    (0.01, 0.05),
    (-0.015, 0.03),
    (-0.02, -0.025),
]

FIGURE_EIGHT: Contour = [(0.0, 0.0), (0.02, 0.02), (0.02, 0.0), (0.0, 0.02)]


class TestContourDefect:
    def test_a_full_ellipse_counter_clockwise_is_valid(self) -> None:
        assert contour_defect(ellipse(0.03, 0.05), MIN_POINTS) is None

    def test_a_concave_former_with_a_wing_saddle_is_valid(self) -> None:
        assert contour_defect(SADDLE, MIN_POINTS) is None

    def test_an_asymmetric_former_is_valid(self) -> None:
        assert contour_defect(ASYMMETRIC, MIN_POINTS) is None

    def test_a_triangle_is_the_least_valid_contour(self) -> None:
        assert contour_defect([(0.0, -0.01), (0.01, 0.01), (-0.01, 0.01)], MIN_POINTS) is None

    def test_any_start_point_is_valid(self) -> None:
        shifted = ASYMMETRIC[3:] + ASYMMETRIC[:3]
        assert contour_defect(shifted, MIN_POINTS) is None

    def test_two_points_are_refused(self) -> None:
        defect = contour_defect([(0.0, -0.01), (0.0, 0.01)], MIN_POINTS)
        assert defect is not None
        assert defect.point is None
        assert "2 point(s)" in defect.message
        assert "at least 3" in defect.message

    def test_a_clockwise_contour_is_refused(self) -> None:
        defect = contour_defect(list(reversed(ASYMMETRIC)), MIN_POINTS)
        assert defect is not None
        assert defect.point is None
        assert "clockwise" in defect.message

    def test_a_figure_eight_is_refused(self) -> None:
        defect = contour_defect(FIGURE_EIGHT, MIN_POINTS)
        assert defect is not None
        assert "crosses itself" in defect.message
        assert defect.point == 2

    def test_a_crossing_with_the_implicit_closing_segment_is_refused(self) -> None:
        # the closing segment from the last point back to (0, 0) cuts through the outline
        contour: Contour = [(0.0, 0.0), (0.04, 0.0), (0.04, 0.03), (-0.01, 0.01), (0.03, 0.04)]
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert "crosses itself" in defect.message

    def test_a_spike_folding_back_onto_itself_is_refused(self) -> None:
        contour: Contour = [(0.0, 0.0), (0.04, 0.0), (0.04, 0.03), (0.04, 0.01), (0.0, 0.03)]
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert "crosses itself" in defect.message

    def test_a_repeated_consecutive_point_is_refused(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour.insert(4, contour[3])
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 4
        assert "repeats point 3" in defect.message

    def test_repeating_the_first_point_at_the_end_is_refused(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour.append(contour[0])
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 0

    def test_a_degenerate_contour_is_left_to_the_fuselage_check(self) -> None:
        assert contour_defect([(0.0, 0.01)] * 5, MIN_POINTS) is None
        assert contour_defect([(0.0, -0.02), (0.0, 0.0), (0.0, 0.02)], MIN_POINTS) is None


class TestDegenerate:
    def test_a_point_and_a_vertical_line_are_degenerate(self) -> None:
        assert is_degenerate([(0.01, 0.02)] * 4)
        assert is_degenerate([(0.0, -0.02), (0.0, -0.01), (0.0, 0.03), (0.0, 0.01)])

    def test_a_slanted_exactly_collinear_line_is_degenerate(self) -> None:
        assert is_degenerate([(0.0, 0.0), (0.25, 0.5), (0.5, 1.0), (0.125, 0.25)])

    def test_a_polygon_is_not_degenerate(self) -> None:
        assert not is_degenerate(ASYMMETRIC)


class TestContourSetDefects:
    def test_no_contour_anywhere_is_valid(self) -> None:
        assert contour_set_defects([None, None, None]) == []

    def test_the_same_count_everywhere_is_valid(self) -> None:
        assert contour_set_defects([ellipse(0.02, 0.03), ellipse(0.03, 0.05)]) == []

    def test_a_section_without_a_contour_next_to_one_with_is_a_defect(self) -> None:
        (defect,) = contour_set_defects([ellipse(0.02, 0.03), None, ellipse(0.03, 0.05)])
        assert (defect.section, defect.kind) == (1, "missing")
        assert "no contour" in defect.message
        assert "x_secs[0]" in defect.message

    def test_a_different_count_is_a_defect_against_the_first_contour(self) -> None:
        defects = contour_set_defects(
            [ellipse(0.02, 0.03, 16), ellipse(0.03, 0.05, 12), ellipse(0.03, 0.05, 16)]
        )
        assert [(d.section, d.kind) for d in defects] == [(1, "count")]
        assert "12 points" in defects[0].message
        assert "16" in defects[0].message

    def test_a_point_or_a_line_closes_the_first_and_the_last_section(self) -> None:
        nose: Contour = [(0.0, 0.0)] * 16
        tail: Contour = [(0.0, -0.01 + 0.001 * i) for i in range(16)]
        assert contour_set_defects([nose, ellipse(0.03, 0.05), tail]) == []

    def test_a_degenerate_interior_section_is_a_defect(self) -> None:
        pinch: Contour = [(0.0, 0.0)] * 16
        (defect,) = contour_set_defects([ellipse(0.02, 0.03), pinch, ellipse(0.03, 0.05)])
        assert (defect.section, defect.kind) == (1, "degenerate")
        assert "first or the last" in defect.message
