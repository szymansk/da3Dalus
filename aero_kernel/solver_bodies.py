"""The bodies the solvers see: every canopy merged into the body it sits on (#1355, slice 2).

A canopy (``role: canopy``) is modelled by its writer as a whole body whose lower part lies inside
the body it sits on (``attached_to``). Handed to a solver as a body of its own, its hidden part
would count: its skin friction, its form drag, its volume. The kernel therefore hands the solvers
one body per parent instead, the **envelope** of the parent and its canopies (maintainer
2026-11-05: only the visible part of a canopy counts; this is a decision, not a textbook method).
Nacelles, fairings, pods and other bodies stay bodies of their own.

Per parent ``P`` with canopies ``C1 ... Ck``:

1. **Stations.** ``P``'s sections, and the stations of the canopies inside ``P``'s x range, an exact
   duplicate x collapsed into ``P``'s section. A station where no canopy shows (outside every
   canopy, a canopy section of size 0, or a canopy hidden inside ``P``) keeps ``P``'s section
   verbatim; an inserted station where nothing shows is not inserted.
2. **Interpolation.** Each body's section at a station is the linear interpolation in x of its
   neighbouring sections: ``xyz``, ``a``, ``b``, ``n`` and ``n_lower`` (``n_lower`` defaults to
   ``n``).
3. **Envelope.** On a grid in z the half-width is the largest of the bodies' half-widths about
   ``P``'s y (a canopy off ``P``'s y counts with its offset). An interior gap of zero width (a
   canopy floating just above ``P``) is filled with the smaller of the widest half-width below and
   above it; a notch of positive width is real and kept.
4. **Refit.** The envelope becomes one section of two exponents: its centre the middle of the
   envelope's height, ``b`` half that height, ``a`` its largest half-width, and each half's exponent
   the one that keeps that half's area, ``f(n) = A_half / (2 a b)`` with
   :func:`~aero_kernel.superellipse.quadrant_area_fraction`, by bisection. A target outside the
   search bracket is clamped to it and declared.
5. Several canopies on one parent fold into the same envelope.

The stored document is never changed and the measured ``contour`` is never read (a merged section
has none). :func:`merged_bodies` is the one producer (ADR 0022): the AeroSandbox conversion, the
AVL bodies and the validation's declarations all read it.
"""

import logging
import math
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import NamedTuple

import numpy as np
from aero_kernel.config import config
from aero_kernel.geometry import AirplaneGeometry, Fuselage, FuselageXSecSuperEllipse
from aero_kernel.superellipse import quadrant_area_fraction
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

__all__ = [
    "CanopyMerge",
    "SolverBodies",
    "merged_bodies",
    "outline_perimeter",
    "solver_bodies",
    "wetted_area",
]

Floats = NDArray[np.float64]


class CanopyMerge(NamedTuple):
    """What the merge of one canopy into its parent did; the content of its declaration.

    The areas and deviations are those of the parent's merged body, all its canopies together.

    Attributes:
        canopy: Key of the canopy.
        parent: Key of the body it sits on.
        canopies_on_parent: Keys of every canopy merged into the same parent, in document order.
        merged_stations: Stations at which this canopy shows and the section was refitted.
        canopy_wetted_area: Wetted area of the whole canopy, which no solver sees any more, m^2.
        wetted_area_added: Wetted area of the merged body less that of the parent alone, m^2: the
            visible part of the canopies.
        area_deviation: Largest relative difference of a refitted section's area from its
            envelope's, over the merged stations.
        perimeter_deviation: Largest relative difference of a refitted section's perimeter from
            its envelope's, over the merged stations.
        clamped_exponents: Refitted exponents clamped to the search bracket, over the merged
            stations.
        off_centre: Largest ``|y_canopy - y_parent|`` over the canopy's stations, m; 0 when the
            canopy is centred on its parent.
    """

    canopy: str
    parent: str
    canopies_on_parent: tuple[str, ...]
    merged_stations: int
    canopy_wetted_area: float
    wetted_area_added: float
    area_deviation: float
    perimeter_deviation: float
    clamped_exponents: int
    off_centre: float


class SolverBodies(NamedTuple):
    """The bodies the solvers see and what the merge did.

    Attributes:
        bodies: Every body that is not a canopy, in document order; a parent of canopies as its
            merged body.
        merges: One entry per canopy, in document order.
    """

    bodies: tuple[Fuselage, ...]
    merges: tuple[CanopyMerge, ...]


class _Settings(NamedTuple):
    """The numeric settings of the merge (kernel configuration)."""

    points: int
    tolerance: float
    n_min: float
    n_max: float


class _Fit(NamedTuple):
    """One refitted station."""

    section: FuselageXSecSuperEllipse
    shown: frozenset[str]
    area_deviation: float
    perimeter_deviation: float
    clamped: int


def _settings() -> _Settings:
    """Read the merge's grid, tolerance and exponent bracket from the kernel configuration."""
    found = config()
    cells = int(found.opt_body_merge_z_cells.value)
    return _Settings(
        points=cells + cells % 2,  # even: the middle of the height is a cell boundary
        tolerance=found.opt_body_merge_area_tolerance.value,
        n_min=found.opt_body_merge_exponent_min.value,
        n_max=found.opt_body_merge_exponent_max.value,
    )


def _lower(section: FuselageXSecSuperEllipse) -> float:
    """The exponent of the lower half: ``n_lower``, or ``n`` when the section has one exponent."""
    return section.n if section.n_lower is None else section.n_lower


def _x(section: FuselageXSecSuperEllipse) -> float:
    return section.xyz[0]


def _shows(section: FuselageXSecSuperEllipse) -> bool:
    """Whether a section encloses an area (a section of size 0 is a point or a line)."""
    return section.a > 0.0 and section.b > 0.0


def _lerp(
    low: FuselageXSecSuperEllipse, high: FuselageXSecSuperEllipse, x: float
) -> FuselageXSecSuperEllipse:
    """The section at ``x`` between two neighbours, every field linear in x."""
    t = (x - _x(low)) / (_x(high) - _x(low))

    def mix(p: float, q: float) -> float:
        return p + t * (q - p)

    xyz = (x, mix(low.xyz[1], high.xyz[1]), mix(low.xyz[2], high.xyz[2]))
    n_lower = None
    if low.n_lower is not None or high.n_lower is not None:
        n_lower = mix(_lower(low), _lower(high))
    return FuselageXSecSuperEllipse(
        xyz=xyz,
        a=mix(low.a, high.a),
        b=mix(low.b, high.b),
        n=mix(low.n, high.n),
        n_lower=n_lower,
    )


def _section_at(
    sections: Sequence[FuselageXSecSuperEllipse], x: float
) -> FuselageXSecSuperEllipse | None:
    """A body's section at ``x``: its own section there, else interpolated; ``None`` outside."""
    for section in sections:
        if _x(section) == x:
            return section
    for low, high in pairwise(sections):
        if min(_x(low), _x(high)) < x < max(_x(low), _x(high)):
            return _lerp(low, high, x)
    return None


def _half_widths(section: FuselageXSecSuperEllipse, offset: float, z: Floats) -> Floats:
    """The half-width of a section at every ``z``, measured from a line ``offset`` beside its centre.

    ``|y/a|^n + |z/b|^n = 1`` solved for ``y``, with ``n`` above the centre and ``n_lower`` below;
    zero outside the section.
    """
    if not _shows(section):
        return np.zeros_like(z)
    t = (z - section.xyz[2]) / section.b
    exponent = np.where(t >= 0.0, section.n, _lower(section))
    inside = np.abs(t) < 1.0
    reach = np.where(inside, 1.0 - np.abs(np.where(inside, t, 0.0)) ** exponent, 0.0)
    return np.where(inside, section.a * reach ** (1.0 / exponent) + offset, 0.0)


def _fill_gaps(width: Floats) -> Floats:
    """Fill an interior run of zero width with the smaller of the widest half-width below and above.

    A canopy that floats just above its parent leaves a gap in the envelope; the body the solvers
    see has none. A notch of positive width is kept.
    """
    positive = np.flatnonzero(width > 0.0)
    if positive.size == 0:
        return width
    index = np.arange(width.size)
    below = np.maximum.accumulate(width)
    above = np.maximum.accumulate(width[::-1])[::-1]
    gap = (width <= 0.0) & (index > positive[0]) & (index < positive[-1])
    return np.where(gap, np.minimum(below, above), width)


def _exponent(target: float, settings: _Settings) -> tuple[float, bool]:
    """The exponent whose quadrant area fraction is ``target``, and whether it was clamped.

    ``f`` rises strictly with ``n``; the bisection runs on ``log n`` inside the configured bracket
    and stops at the relative area tolerance or when the bracket is exhausted.
    """
    if target <= quadrant_area_fraction(settings.n_min):
        return settings.n_min, True
    if target >= quadrant_area_fraction(settings.n_max):
        return settings.n_max, True
    low, high = math.log(settings.n_min), math.log(settings.n_max)
    while True:
        middle = (low + high) / 2.0
        error = quadrant_area_fraction(math.exp(middle)) / target - 1.0
        # the bracket is exhausted when the midpoint no longer lies strictly inside it
        if abs(error) <= settings.tolerance or not low < middle < high:
            return math.exp(middle), False
        if error < 0.0:
            low = middle
        else:
            high = middle


def _quadrant_length(a: float, b: float, exponent: float, points: int) -> float:
    """The arc length of one quadrant of ``|y/a|^n + |z/b|^n = 1``, as a fine polyline."""
    theta = np.linspace(0.0, math.pi / 2.0, points)
    y = a * np.cos(theta).clip(0.0) ** (2.0 / exponent)
    z = b * np.sin(theta).clip(0.0) ** (2.0 / exponent)
    return float(np.sum(np.hypot(np.diff(y), np.diff(z))))


def outline_perimeter(section: FuselageXSecSuperEllipse, points: int | None = None) -> float:
    """The perimeter of a section in m, upper and lower half with their own exponents.

    Args:
        section: The section.
        points: Polyline points per quadrant; the merge's grid size if omitted.

    Returns:
        Twice the arc length of the upper and the lower quadrant; 0 for a point.
    """
    if points is None:
        points = _settings().points
    if section.a <= 0.0 and section.b <= 0.0:
        return 0.0
    upper = _quadrant_length(section.a, section.b, section.n, points)
    lower = _quadrant_length(section.a, section.b, _lower(section), points)
    return 2.0 * (upper + lower)


def wetted_area(sections: Sequence[FuselageXSecSuperEllipse], points: int | None = None) -> float:
    """The wetted area of a lofted body in m^2: the mean perimeter of each bay times its x length.

    Args:
        sections: The sections in loft order.
        points: Polyline points per quadrant of a perimeter; the merge's grid size if omitted.

    Returns:
        The sum over the bays; 0 for fewer than two sections.
    """
    perimeters = [outline_perimeter(section, points) for section in sections]
    return sum(
        (p + q) / 2.0 * abs(_x(high) - _x(low))
        for (p, q), (low, high) in zip(pairwise(perimeters), pairwise(sections), strict=True)
    )


def _refit(
    parent: FuselageXSecSuperEllipse,
    canopies: Mapping[str, FuselageXSecSuperEllipse],
    settings: _Settings,
) -> _Fit | None:
    """The envelope of a parent section and the canopy sections at one station, refitted.

    Returns ``None`` when no canopy shows beyond the parent there: the station keeps the parent's
    section.
    """
    sized = [s for s in (parent, *canopies.values()) if _shows(s)]
    bottom = min(s.xyz[2] - s.b for s in sized)
    top = max(s.xyz[2] + s.b for s in sized)
    step = (top - bottom) / settings.points
    z = bottom + step * (np.arange(settings.points, dtype=np.float64) + 0.5)  # cell midpoints
    centre_y = parent.xyz[1]
    own = _half_widths(parent, 0.0, z)
    width = own.copy()
    shown: set[str] = set()
    for key, canopy in canopies.items():
        reach = _half_widths(canopy, abs(canopy.xyz[1] - centre_y), z)
        if np.any(reach > own):
            shown.add(key)
        width = np.maximum(width, reach)
    if not shown:
        return None
    width = _fill_gaps(width)
    middle = settings.points // 2
    a = float(width.max())
    b = (top - bottom) / 2.0
    upper = 2.0 * step * float(np.sum(width[middle:]))
    lower = 2.0 * step * float(np.sum(width[:middle]))
    n_upper, clamped_upper = _exponent(upper / (2.0 * a * b), settings)
    n_lower, clamped_lower = _exponent(lower / (2.0 * a * b), settings)
    section = FuselageXSecSuperEllipse(
        xyz=(parent.xyz[0], centre_y, (top + bottom) / 2.0),
        a=a,
        b=b,
        n=n_upper,
        n_lower=n_lower,
    )
    area = upper + lower
    fitted_area = 2.0 * a * b * (quadrant_area_fraction(n_upper) + quadrant_area_fraction(n_lower))
    # the right half of the outline from the bottom point through the midpoints to the top point
    outline_y = np.concatenate(([0.0], width, [0.0]))
    outline_z = np.concatenate(([bottom], z, [top]))
    envelope_perimeter = 2.0 * float(np.sum(np.hypot(np.diff(outline_y), np.diff(outline_z))))
    fitted_perimeter = outline_perimeter(section, settings.points)
    return _Fit(
        section=section,
        shown=frozenset(shown),
        area_deviation=abs(fitted_area / area - 1.0),
        perimeter_deviation=abs(fitted_perimeter / envelope_perimeter - 1.0),
        clamped=int(clamped_upper) + int(clamped_lower),
    )


def _stations(
    parent: Fuselage, canopies: Sequence[Fuselage]
) -> list[tuple[FuselageXSecSuperEllipse, bool]]:
    """``P``'s sections in loft order with the canopies' stations inserted where they fall.

    Each entry is the parent's section at the station and whether it is the parent's own. A canopy
    station at the x of a parent section collapses into it; one outside the parent is dropped.
    """
    own = {_x(section) for section in parent.x_secs}
    extra = sorted(
        {_x(s) for canopy in canopies for s in canopy.x_secs} - own,
    )
    taken: set[float] = set()
    stations: list[tuple[FuselageXSecSuperEllipse, bool]] = [(parent.x_secs[0], True)]
    for low, high in pairwise(parent.x_secs):
        start, end = sorted((_x(low), _x(high)))
        inside = [x for x in extra if start < x < end and x not in taken]
        taken.update(inside)
        if _x(high) < _x(low):
            inside.reverse()
        stations += [(_lerp(low, high, x), False) for x in inside]
        stations.append((high, True))
    return stations


class _ParentMerge(NamedTuple):
    """The merged body of one parent and its per-canopy station counts."""

    body: Fuselage
    stations: dict[str, int]
    area_deviation: float
    perimeter_deviation: float
    clamped: int


def _merge_parent(
    parent: Fuselage, canopies: Mapping[str, Fuselage], settings: _Settings
) -> _ParentMerge:
    """Merge the canopies into their parent (steps 1 to 5 of the module docstring)."""
    counts = dict.fromkeys(canopies, 0)
    merged: list[FuselageXSecSuperEllipse] = []
    area_deviation = perimeter_deviation = 0.0
    clamped = 0
    for section, is_own in _stations(parent, list(canopies.values())):
        at = {key: _section_at(c.x_secs, _x(section)) for key, c in canopies.items()}
        present = {key: s for key, s in at.items() if s is not None and _shows(s)}
        fit = _refit(section, present, settings) if present else None
        if fit is None:
            if is_own:
                merged.append(section)
            continue
        merged.append(fit.section)
        area_deviation = max(area_deviation, fit.area_deviation)
        perimeter_deviation = max(perimeter_deviation, fit.perimeter_deviation)
        clamped += fit.clamped
        for key in fit.shown:
            counts[key] += 1
    body = parent.model_copy(update={"x_secs": tuple(merged)})
    return _ParentMerge(body, counts, area_deviation, perimeter_deviation, clamped)


def _off_centre(canopy: Fuselage, parent: Fuselage) -> float:
    """The largest distance in y of a canopy section's centre from its parent's at that x."""
    offsets = [
        abs(section.xyz[1] - found.xyz[1])
        for section in canopy.x_secs
        if (found := _section_at(parent.x_secs, _x(section))) is not None
    ]
    return max(offsets, default=0.0)


def merged_bodies(airplane: AirplaneGeometry) -> SolverBodies:
    """The bodies the solvers see, with what the merge did (#1355; ADR 0022, the one producer).

    Expects a validated document: every canopy has ``attached_to`` naming another body that is not
    a canopy, within whose x range it lies (canon rule ``body-attachment``).

    Args:
        airplane: The validated geometry document.

    Returns:
        Every body but the canopies in document order, a parent of canopies as its merged body,
        and one :class:`CanopyMerge` per canopy.
    """
    fuselages = airplane.fuselages or {}
    by_parent: dict[str, dict[str, Fuselage]] = {}
    for key, body in fuselages.items():
        if body.role == "canopy" and body.attached_to is not None:
            by_parent.setdefault(body.attached_to, {})[key] = body
    if not by_parent:
        return SolverBodies(tuple(fuselages.values()), ())
    settings = _settings()
    bodies: list[Fuselage] = []
    merges: list[CanopyMerge] = []
    for key, body in fuselages.items():
        if body.role == "canopy" and body.attached_to is not None:
            continue
        canopies = by_parent.get(key)
        if not canopies:
            bodies.append(body)
            continue
        merge = _merge_parent(body, canopies, settings)
        bodies.append(merge.body)
        added = wetted_area(merge.body.x_secs, settings.points)
        added -= wetted_area(body.x_secs, settings.points)
        for canopy_key, canopy in canopies.items():
            merges.append(
                CanopyMerge(
                    canopy=canopy_key,
                    parent=key,
                    canopies_on_parent=tuple(canopies),
                    merged_stations=merge.stations[canopy_key],
                    canopy_wetted_area=wetted_area(canopy.x_secs, settings.points),
                    wetted_area_added=added,
                    area_deviation=merge.area_deviation,
                    perimeter_deviation=merge.perimeter_deviation,
                    clamped_exponents=merge.clamped,
                    off_centre=_off_centre(canopy, body),
                )
            )
        logger.debug(
            "merged %d canopies into %s: %d -> %d sections",
            len(canopies),
            key,
            len(body.x_secs),
            len(merge.body.x_secs),
        )
    order = {key: index for index, key in enumerate(fuselages)}
    merges.sort(key=lambda m: order[m.canopy])
    return SolverBodies(tuple(bodies), tuple(merges))


def solver_bodies(airplane: AirplaneGeometry) -> tuple[Fuselage, ...]:
    """The bodies the solvers see: :func:`merged_bodies` without the account of the merge.

    Args:
        airplane: The validated geometry document.

    Returns:
        Every body but the canopies in document order, each parent of canopies merged.
    """
    return merged_bodies(airplane).bodies
