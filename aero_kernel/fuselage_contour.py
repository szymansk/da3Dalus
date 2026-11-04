"""The point contour of a fuselage section and its distance to the super-ellipse fit (#1349).

A fuselage section may carry, besides its super-ellipse ``a``, ``b``, ``n``, ``n_lower``, the
measured outline as points (geometry format 7.1b). Only the right half is stored: ``(y, z)`` pairs
in metres relative to the section centre ``xyz``, running from the bottom centre (``y = 0``, below
the centre) over the right side to the top centre (``y = 0``, above the centre). The body is
mirrored about ``y = 0``. Points are lofted index to index, so every section of a fuselage that has
a contour has one with the same number of points.

The contour is display and CAD geometry. No solver reads it: AeroSandbox and AVL take the fitted
``a``, ``b``, ``n``, ``n_lower`` (ADR 0022, maintainer 2026-11-03). The kernel reads it only to
check it (``fuselage-contour``) and to declare how far the fit is from it
(``fuselage-contour-fit``). These functions are pure and know no thresholds; the caller passes the
canon's.

The order rule: the contour is star-shaped about the section centre and runs counter-clockwise, so
the polar angle ``atan2(z, y)`` rises strictly from -90 deg at the first point to +90 deg at the
last. This is what "monotonic order" means for an outline around a centre: it rules out a contour
that doubles back, crosses itself or repeats a point, and it fixes which way the points run.
"""

import math
from collections.abc import Sequence
from typing import NamedTuple

__all__ = [
    "ContourDefect",
    "ContourSetDefect",
    "contour_defect",
    "contour_fit_deviation",
    "contour_set_defects",
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
    """Why the contours of one fuselage do not fit together.

    Attributes:
        section: Index of the offending section in the fuselage's ``x_secs``.
        message: The reason, naming the section it is compared with.
    """

    section: int
    message: str


def _polar_angle(point: ContourPoint) -> float:
    """Return the polar angle of a contour point about the section centre, radians."""
    return math.atan2(point[1], point[0])


def contour_defect(contour: Sequence[ContourPoint], min_points: int) -> ContourDefect | None:
    """Return the first rule a section's half contour breaks, or ``None`` if it is valid.

    The rules, in the order they are checked: at least ``min_points`` points; the first point is
    the bottom centre (``y = 0``, ``z < 0``); the last is the top centre (``y = 0``, ``z > 0``);
    every ``y >= 0``; no interior point on the centre line ``y = 0``; the polar angle rises
    strictly from point to point. No tolerance is applied: ``y = 0`` means exactly zero.

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
    first, last = contour[0], contour[-1]
    if not (first[0] == 0 and first[1] < 0):
        return ContourDefect(
            0,
            f"starts at {list(first)}; the first point must be the bottom centre (y = 0, z < 0).",
        )
    if not (last[0] == 0 and last[1] > 0):
        return ContourDefect(
            count - 1,
            f"ends at {list(last)}; the last point must be the top centre (y = 0, z > 0).",
        )
    for index, (y, _) in enumerate(contour):
        if y < 0:
            return ContourDefect(
                index, f"has y = {y} at point {index}; the half contour needs y >= 0."
            )
    for index in range(1, count - 1):
        if contour[index][0] == 0:
            return ContourDefect(
                index,
                f"has point {index} on the centre line (y = 0); only the first and the last "
                "point may lie on it.",
            )
    for index in range(1, count):
        if _polar_angle(contour[index]) <= _polar_angle(contour[index - 1]):
            return ContourDefect(
                index,
                f"turns back at point {index}: its angle about the centre is not larger than "
                f"that of point {index - 1}; the points must run from the bottom centre over "
                "the right side to the top centre without doubling back or repeating.",
            )
    return None


def contour_set_defects(
    contours: Sequence[Sequence[ContourPoint] | None],
) -> list[ContourSetDefect]:
    """Return every section that breaks the all-or-none, same-count rule of one fuselage.

    If any section of a fuselage has a contour, every section has one, all with the same number
    of points: the loft joins point ``i`` to point ``i``. The first section with a contour is the
    reference.

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
    defects: list[ContourSetDefect] = []
    for index, contour in enumerate(contours):
        if contour is None:
            defects.append(
                ContourSetDefect(
                    index,
                    f"has no contour, but x_secs[{reference_index}] of the same fuselage has "
                    "one; either every section of a fuselage has a contour or none.",
                )
            )
        elif len(contour) != reference_count:
            defects.append(
                ContourSetDefect(
                    index,
                    f"has a contour of {len(contour)} points, but x_secs[{reference_index}] has "
                    f"{reference_count}; every contour of a fuselage has the same number of "
                    "points.",
                )
            )
    return defects


def contour_fit_deviation(contour: Sequence[ContourPoint], a: float, b: float) -> float:
    """Return how far the super-ellipse fit's extent is from the contour's, metres.

    The largest of three distances: the contour's widest point to the semi-axis ``a``, its top to
    ``b`` and its bottom to ``-b`` (the fit is centred on ``xyz``, as the contour is).

    Args:
        contour: A valid half contour (:func:`contour_defect` is ``None``), metres.
        a: The fit's semi-axis in y, metres.
        b: The fit's semi-axis in z, metres.

    Returns:
        The deviation, >= 0.
    """
    widest = max(y for y, _ in contour)
    top = max(z for _, z in contour)
    bottom = min(z for _, z in contour)
    return max(abs(widest - a), abs(top - b), abs(bottom + b))
