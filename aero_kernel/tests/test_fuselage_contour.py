"""The point contour of a fuselage section: its rules and its distance to the a/b fit (#1349)."""

import math

from aero_kernel.fuselage_contour import (
    contour_defect,
    contour_fit_deviation,
    contour_set_defects,
)

MIN_POINTS = 8


def ellipse(a: float, b: float, count: int = 13) -> list[tuple[float, float]]:
    """The right half of the ellipse (a, b) from bottom centre to top centre, ``count`` points.

    An odd count puts a point at the widest place (angle 0), so the extent is exactly ``a``.
    """
    points: list[tuple[float, float]] = []
    for index in range(count):
        angle = -math.pi / 2 + math.pi * index / (count - 1)
        points.append((a * math.cos(angle), b * math.sin(angle)))
    # cos(+-pi/2) is 6e-17, not 0: the end points lie exactly on the centre line
    points[0] = (0.0, -b)
    points[-1] = (0.0, b)
    return points


class TestContourDefect:
    def test_a_half_ellipse_bottom_to_top_is_valid(self) -> None:
        assert contour_defect(ellipse(0.03, 0.05), MIN_POINTS) is None

    def test_a_flat_bottom_and_straight_tapered_sides_are_valid(self) -> None:
        # box bottom, sides tapering inwards to a narrow round back: the Bf 109 kind of section
        contour = [
            (0.0, -0.04),
            (0.012, -0.04),
            (0.024, -0.039),
            (0.026, -0.02),
            (0.025, 0.0),
            (0.022, 0.02),
            (0.015, 0.035),
            (0.006, 0.042),
            (0.0, 0.043),
        ]
        assert contour_defect(contour, MIN_POINTS) is None

    def test_fewer_points_than_the_minimum_are_a_defect(self) -> None:
        defect = contour_defect(ellipse(0.03, 0.05, count=7), MIN_POINTS)
        assert defect is not None
        assert defect.point is None
        assert "7 point(s)" in defect.message
        assert "at least 8" in defect.message

    def test_exactly_the_minimum_is_valid(self) -> None:
        assert contour_defect(ellipse(0.03, 0.05, count=8), MIN_POINTS) is None

    def test_the_first_point_must_be_the_bottom_centre(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[0] = (0.001, -0.05)
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 0
        assert "bottom centre" in defect.message

    def test_a_first_point_above_the_centre_is_a_defect(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[0] = (0.0, 0.01)
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 0

    def test_the_last_point_must_be_the_top_centre(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[-1] = (0.0, -0.06)
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == len(contour) - 1
        assert "top centre" in defect.message

    def test_a_point_on_the_left_half_is_a_defect(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[4] = (-0.01, contour[4][1])
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 4
        assert "y >= 0" in defect.message

    def test_an_interior_point_on_the_centre_line_is_a_defect(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[5] = (0.0, contour[5][1])
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 5
        assert "centre line" in defect.message

    def test_points_out_of_order_are_a_defect(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[3], contour[4] = contour[4], contour[3]
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 4
        assert "angle" in defect.message

    def test_a_contour_running_top_to_bottom_is_a_defect(self) -> None:
        defect = contour_defect(list(reversed(ellipse(0.03, 0.05))), MIN_POINTS)
        assert defect is not None
        assert defect.point == 0

    def test_a_repeated_point_is_a_defect(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour.insert(4, contour[3])
        defect = contour_defect(contour, MIN_POINTS)
        assert defect is not None
        assert defect.point == 4


class TestContourSetDefects:
    def test_no_contour_anywhere_is_valid(self) -> None:
        assert contour_set_defects([None, None, None]) == []

    def test_the_same_count_everywhere_is_valid(self) -> None:
        assert contour_set_defects([ellipse(0.02, 0.03), ellipse(0.03, 0.05)]) == []

    def test_a_section_without_a_contour_next_to_one_with_is_a_defect(self) -> None:
        (defect,) = contour_set_defects([ellipse(0.02, 0.03), None, ellipse(0.03, 0.05)])
        assert defect.section == 1
        assert "no contour" in defect.message
        assert "x_secs[0]" in defect.message

    def test_a_different_count_is_a_defect_against_the_first_contour(self) -> None:
        defects = contour_set_defects(
            [ellipse(0.02, 0.03, 13), ellipse(0.03, 0.05, 10), ellipse(0.03, 0.05, 13)]
        )
        assert [d.section for d in defects] == [1]
        assert "10 points" in defects[0].message
        assert "13" in defects[0].message


class TestFitDeviation:
    def test_a_contour_on_the_fit_has_no_deviation(self) -> None:
        assert math.isclose(
            contour_fit_deviation(ellipse(0.03, 0.05), 0.03, 0.05), 0.0, abs_tol=1e-12
        )

    def test_the_largest_of_width_top_and_bottom_counts(self) -> None:
        contour = ellipse(0.03, 0.05)
        # lower the bottom by 2 mm: the top and the width still match
        contour[0] = (0.0, -0.052)
        assert math.isclose(contour_fit_deviation(contour, 0.03, 0.05), 0.002, abs_tol=1e-12)

    def test_a_narrower_contour_deviates_by_the_width_difference(self) -> None:
        assert math.isclose(
            contour_fit_deviation(ellipse(0.0285, 0.05), 0.03, 0.05), 0.0015, abs_tol=1e-12
        )

    def test_a_top_above_b_deviates(self) -> None:
        contour = ellipse(0.03, 0.05)
        contour[-1] = (0.0, 0.0512)
        assert math.isclose(contour_fit_deviation(contour, 0.03, 0.05), 0.0012, abs_tol=1e-12)
