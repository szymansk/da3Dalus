"""The point contour of a fuselage section (#1349, geometry format 7.1b).

A fuselage section may carry, besides its super-ellipse ``a``, ``b``, ``n``, ``n_lower``, the
measured outline as a **full closed loop**: ``(y, z)`` pairs in metres relative to the section
centre ``xyz``, counter-clockwise in the plane with y to the right and z up. The segment from the
last point back to the first is implicit; the first point is not repeated. The start point is the
writer's choice. Nothing is assumed about symmetry: a real former may be asymmetric and concave.
Points are lofted index to index, so every section of a fuselage that has a contour has one with
the same number of points.

The first and the last section of a fuselage may close the body: their contour may be degenerate,
a point (all points identical) or a line (all points exactly collinear, e.g. a vertical trailing
edge), still with the common point count. A degenerate contour anywhere else would pinch the body.

The contour is display and CAD geometry. No solver reads it: AeroSandbox and AVL take the fitted
``a``, ``b``, ``n``, ``n_lower`` (ADR 0022, maintainer 2026-11-03). The kernel reads it only to
check it (``fuselage-contour``); a deviation of the fit from the contour is expected and not
warned about (maintainer 2026-11-04). These functions are pure and know no thresholds; the caller
passes the canon's. No tolerance is applied: collinear means exactly collinear.
"""

from collections.abc import Sequence
from itertools import combinations
from typing import Literal, NamedTuple

__all__ = [
    "ContourDefect",
    "ContourSetDefect",
    "contour_defect",
    "contour_set_defects",
    "is_degenerate",
]

ContourPoint = tuple[float, float]


class ContourDefect(NamedTuple):
    """Why a contour is refused.

    Attributes:
        point: Index of the offending point, ``None`` when the contour as a whole is at fault.
        message: The reason, without the path of the contour.
    """

    point: int | None
    message: str


class ContourSetDefect(NamedTuple):
    """Why a section's contour does not fit the other sections of its fuselage.

    Attributes:
        section: Index of the offending section in the fuselage's ``x_secs``.
        kind: ``missing`` (no contour among contours), ``count`` (another point count) or
            ``degenerate`` (a point or line contour at an interior section).
        message: The reason, naming the section it is compared with where there is one.
    """

    section: int
    kind: Literal["missing", "count", "degenerate"]
    message: str


def _cross(origin: ContourPoint, a: ContourPoint, b: ContourPoint) -> float:
    """Return the z component of ``(a - origin) x (b - origin)``: > 0 if ``b`` is left of it."""
    return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])


def is_degenerate(contour: Sequence[ContourPoint]) -> bool:
    """Whether a contour is a point (all points identical) or a line (all exactly collinear)."""
    first = contour[0]
    other = next((point for point in contour if point != first), None)
    if other is None:
        return True
    return all(_cross(first, other, point) == 0 for point in contour)


def _on_segment(a: ContourPoint, b: ContourPoint, point: ContourPoint) -> bool:
    """Whether ``point``, collinear with the segment ``a``-``b``, lies on it."""
    return min(a[0], b[0]) <= point[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= point[1] <= max(
        a[1], b[1]
    )


def _segments_meet(a: ContourPoint, b: ContourPoint, c: ContourPoint, d: ContourPoint) -> bool:
    """Whether the closed segments ``a``-``b`` and ``c``-``d`` share a point."""
    d1, d2 = _cross(c, d, a), _cross(c, d, b)
    d3, d4 = _cross(a, b, c), _cross(a, b, d)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True
    return (
        (d1 == 0 and _on_segment(c, d, a))
        or (d2 == 0 and _on_segment(c, d, b))
        or (d3 == 0 and _on_segment(a, b, c))
        or (d4 == 0 and _on_segment(a, b, d))
    )


def _crossing(contour: Sequence[ContourPoint]) -> tuple[int, int] | None:
    """Return the first two segments of the closed loop that meet other than at a shared vertex.

    Segment ``i`` runs from point ``i`` to point ``i + 1`` (the last to point 0). Adjacent segments
    share their common vertex; they cross only if they fold back onto each other.
    """
    count = len(contour)
    segments = [(contour[i], contour[(i + 1) % count]) for i in range(count)]
    for i, j in combinations(range(count), 2):
        (a, b), (c, d) = segments[i], segments[j]
        if j == i + 1 or (i == 0 and j == count - 1):
            # adjacent: the shared vertex is b (= c) for j = i + 1, a (= d) for the closing pair
            shared, far_first, far_second = (b, a, d) if j == i + 1 else (a, b, c)
            if _cross(shared, far_first, far_second) == 0 and (
                _on_segment(shared, far_first, far_second)
                or _on_segment(shared, far_second, far_first)
            ):
                return i, j
            continue
        if _segments_meet(a, b, c, d):
            return i, j
    return None


def _signed_area(contour: Sequence[ContourPoint]) -> float:
    """Return the shoelace area of the closed loop: > 0 counter-clockwise (y right, z up)."""
    count = len(contour)
    twice = sum(
        contour[i][0] * contour[(i + 1) % count][1] - contour[(i + 1) % count][0] * contour[i][1]
        for i in range(count)
    )
    return twice / 2


def contour_defect(contour: Sequence[ContourPoint], min_points: int) -> ContourDefect | None:
    """Return the first rule a section's closed contour breaks, or ``None`` if it is valid.

    The rules, in the order they are checked: at least ``min_points`` points; then, unless the
    contour is degenerate (:func:`is_degenerate`, judged by the fuselage-level check
    :func:`contour_set_defects`), no repeated consecutive point (including last to first), no
    crossing or touching segments (including the implicit closing one), and a positive signed
    area (counter-clockwise with y to the right and z up).

    Args:
        contour: The ``(y, z)`` points in metres relative to the section centre; finite (the
            caller reports non-finite values).
        min_points: The least number of points a contour must have.

    Returns:
        The first defect, or ``None``.
    """
    count = len(contour)
    if count < min_points:
        return ContourDefect(None, f"has {count} point(s); a contour needs at least {min_points}.")
    if is_degenerate(contour):
        return None
    for index in range(count):
        if contour[index] == contour[index - 1]:
            return ContourDefect(
                index,
                f"repeats point {(index - 1) % count} at point {index}; consecutive points "
                "(also the last and the first) must differ.",
            )
    crossing = _crossing(contour)
    if crossing is not None:
        first, second = crossing
        return ContourDefect(
            second,
            f"crosses itself: segment {first} (point {first} to {(first + 1) % count}) meets "
            f"segment {second} (point {second} to {(second + 1) % count}); the outline must be a "
            "simple polygon.",
        )
    area = _signed_area(contour)
    if area <= 0:
        return ContourDefect(
            None,
            f"runs clockwise (signed area {area:.3g} m^2); list the points counter-clockwise "
            "with y to the right and z up.",
        )
    return None


def contour_set_defects(
    contours: Sequence[Sequence[ContourPoint] | None],
) -> list[ContourSetDefect]:
    """Return every section that breaks the fuselage-level rules of the contours.

    If any section of a fuselage has a contour, every section has one, all with the same number
    of points (the loft joins point ``i`` to point ``i``; the first section with a contour is the
    reference). Only the first and the last section may have a degenerate contour (a point or a
    line), which closes the body; anywhere else it would pinch it.

    Args:
        contours: The contour of each section in loft order, ``None`` where a section has none.

    Returns:
        One defect per offending section, in section order; empty if the set is consistent.
    """
    reference = next(
        ((index, len(contour)) for index, contour in enumerate(contours) if contour is not None),
        None,
    )
    if reference is None:
        return []
    reference_index, reference_count = reference
    last = len(contours) - 1
    defects: list[ContourSetDefect] = []
    for index, contour in enumerate(contours):
        if contour is None:
            defects.append(
                ContourSetDefect(
                    index,
                    "missing",
                    f"has no contour, but x_secs[{reference_index}] of the same fuselage has "
                    "one; either every section of a fuselage has a contour or none.",
                )
            )
        elif len(contour) != reference_count:
            defects.append(
                ContourSetDefect(
                    index,
                    "count",
                    f"has a contour of {len(contour)} points, but x_secs[{reference_index}] has "
                    f"{reference_count}; every contour of a fuselage has the same number of "
                    "points.",
                )
            )
        elif index not in (0, last) and contour and is_degenerate(contour):
            defects.append(
                ContourSetDefect(
                    index,
                    "degenerate",
                    "has a degenerate contour (a point or a line); only the first or the last "
                    "section of a fuselage may close the body that way.",
                )
            )
    return defects
