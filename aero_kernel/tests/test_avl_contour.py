"""The AVL contour resampling: unit chord, fixed count, never outside the chord."""

import math

import pytest
from aero_kernel.solvers.avl_contour import repanel


def ellipse(n: int, thickness: float = 0.12) -> list[tuple[float, float]]:
    """A symmetric lens contour in Selig order with n points per side."""
    xs = [0.5 * (1.0 + math.cos(math.pi * k / (n - 1))) for k in range(n)]
    upper = [(x, thickness * 2.0 * math.sqrt(x * (1.0 - x)) / 2.0) for x in xs]
    lower = [(x, -y) for x, y in reversed(upper)][1:]
    return [*upper, *lower]


def test_the_count_is_fixed_whatever_the_input() -> None:
    for n in (10, 80, 400):
        assert len(repanel(ellipse(n), 80)) == 159


def test_no_point_leaves_the_unit_chord() -> None:
    contour = repanel(ellipse(50), 80)
    xs = [x for x, _ in contour]
    assert min(xs) == 0.0
    assert max(xs) == 1.0


def test_the_contour_runs_trailing_edge_to_leading_edge_to_trailing_edge() -> None:
    contour = repanel(ellipse(50), 80)
    assert contour[0][0] == 1.0
    assert contour[79][0] == 0.0
    assert contour[-1][0] == 1.0


def test_the_thickness_is_kept() -> None:
    contour = repanel(ellipse(200), 80)
    upper = max(y for _, y in contour)
    lower = min(y for _, y in contour)
    assert math.isclose(upper - lower, 0.12, rel_tol=2e-3)


def test_a_contour_not_at_unit_chord_is_normalised() -> None:
    scaled = [(3.0 + 2.0 * x, 2.0 * y) for x, y in ellipse(50)]
    contour = repanel(scaled, 80)
    assert contour[0][0] == 1.0
    assert math.isclose(max(y for _, y in contour), 0.06, rel_tol=2e-3)


def test_a_blunt_trailing_edge_stays_blunt() -> None:
    base = ellipse(50)
    blunt = [(x, y + (0.01 if k < 50 else -0.01) * x) for k, (x, y) in enumerate(base)]
    contour = repanel(blunt, 80)
    assert contour[0][1] > contour[-1][1]


@pytest.mark.parametrize(
    ("coordinates", "points"), [([(1.0, 0.0), (0.0, 0.0)], 80), (ellipse(10), 2)]
)
def test_too_little_to_resample_is_refused(
    coordinates: list[tuple[float, float]], points: int
) -> None:
    with pytest.raises(ValueError, match="at least 3"):
        repanel(coordinates, points)
