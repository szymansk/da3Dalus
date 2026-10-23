"""Airfoil contours for AVL: unit chord, a fixed number of cosine-spaced points per side.

Pure numpy, so it runs in the fast tier and the reference script of the BRYAN mesh study can use the
very same function. AeroSandbox's ``Airfoil.repanel`` is not used: on BRYAN's contour it puts points
at x > 1 (the defect noted in AVL_CONVERGENCE.md), where AVL returns nonsense. Each side here is
interpolated linearly in x at cosine-spaced stations in [0, 1], so no point can leave the chord.
"""

import numpy as np

__all__ = ["repanel"]


def repanel(
    coordinates: list[tuple[float, float]], points_per_side: int
) -> list[tuple[float, float]]:
    """Resample a Selig contour to ``points_per_side`` per side at cosine-spaced x, unit chord.

    The contour is normalised to unit chord first (leading edge at x = 0). The upper side runs from
    the trailing edge to the leading edge, the lower from there back; the leading-edge point is shared,
    so the result has ``2 * points_per_side - 1`` points.

    Args:
        coordinates: Selig-ordered points (x, y), the trailing edge first.
        points_per_side: Points per side, at least 3.

    Returns:
        The resampled contour, trailing edge first, every x in [0, 1].

    Raises:
        ValueError: If the contour has fewer than 3 points, no chord, or ``points_per_side`` < 3.
    """
    if points_per_side < 3 or len(coordinates) < 3:
        msg = "a contour needs at least 3 points, and 3 points per side"
        raise ValueError(msg)
    points = np.asarray(coordinates, dtype=float)
    x_min = float(points[:, 0].min())
    chord = float(points[:, 0].max()) - x_min
    if chord <= 0.0:
        msg = "the contour has no chord"
        raise ValueError(msg)
    unit = np.column_stack(((points[:, 0] - x_min) / chord, points[:, 1] / chord))
    leading_edge = int(np.argmin(unit[:, 0]))
    upper = unit[: leading_edge + 1]
    lower = unit[leading_edge:]
    stations = 0.5 * (1.0 - np.cos(np.pi * np.arange(points_per_side) / (points_per_side - 1)))

    def side(part: np.ndarray) -> np.ndarray:
        ordered = part[np.argsort(part[:, 0], kind="stable")]
        return np.interp(stations, ordered[:, 0], ordered[:, 1])

    upper_y, lower_y = side(upper), side(lower)
    x = np.concatenate((stations[::-1], stations[1:]))
    y = np.concatenate((upper_y[::-1], lower_y[1:]))
    return [(float(a), float(b)) for a, b in zip(x, y, strict=True)]
