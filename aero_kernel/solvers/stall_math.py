"""Pure helpers of the stall problem (canon ``stall-speed``, K32)."""

import math
from collections.abc import Sequence

__all__ = [
    "first_crossing_below",
    "local_extrema",
    "local_extrema_from_zero",
    "main_extremum",
    "main_extremum_from_zero",
]


def local_extrema(values: Sequence[float], *, maximum: bool) -> list[int]:
    """Return the indices of the local extrema of a series, in scan order.

    A local maximum is a sample not lower than its predecessor and higher than its successor (a
    plateau counts at its last sample); a minimum is the mirror. The first or last sample is never
    an extremum, because a boundary sample is no turning point (ADR 0020).

    Args:
        values: The series in scan order, e.g. ``C_L`` over rising angle of attack.
        maximum: ``True`` for the maxima, ``False`` for the minima.

    Returns:
        The indices, empty if the series does not turn inside its range.
    """
    sign = 1.0 if maximum else -1.0
    found: list[int] = []
    for index in range(1, len(values) - 1):
        before, here, after = (sign * values[i] for i in (index - 1, index, index + 1))
        if here >= before and here > after:
            found.append(index)
    return found


def main_extremum(values: Sequence[float], *, maximum: bool) -> int | None:
    """Return the index of the main extremum of a series: the stall of a lift curve.

    The rule (maintainer, 2026-11-27, gh-1423: "Das hoechste Maximum mit dem staerksten Einbruch
    ueber mehrere Grad dahinter", scanning the curve from the left), for a maximum:

    1. A local maximum (:func:`local_extrema`) is a candidate only if it is higher than every local
       maximum before it in scan order (a record maximum): after a higher maximum a lower one is no
       maximum of the scan.
    2. The fall behind a candidate is its value minus the lowest value between it and the first
       later sample that lies above it, or the end of the series if none does.
    3. The main maximum is the candidate with the largest fall; of two with the same fall the first
       in scan order.

    A minimum is the mirror (record minima, the largest rise behind). There is no threshold and no
    width: a shoulder before the real maximum has a small fall because the curve soon rises above
    it, and a flat post-stall plateau has a small fall although it may be the highest maximum. The
    end of the series is no extremum.

    Args:
        values: The series in scan order, e.g. ``C_L`` over rising angle of attack.
        maximum: ``True`` for the main peak, ``False`` for the main trough.

    Returns:
        The index of the extremum, or ``None`` if the series does not turn inside its range.
    """
    sign = 1.0 if maximum else -1.0
    series = [sign * value for value in values]
    best: int | None = None
    best_fall = 0.0
    record = -math.inf
    for index in local_extrema(series, maximum=True):
        if series[index] <= record:
            continue
        record = series[index]
        fall = _fall_behind(series, index)
        if best is None or fall > best_fall:
            best, best_fall = index, fall
    return best


def _fall_behind(series: Sequence[float], index: int) -> float:
    """How far ``series`` falls behind ``index`` before it is above ``series[index]`` again."""
    lowest = series[index]
    for value in series[index + 1 :]:
        if value > series[index]:
            break
        lowest = min(lowest, value)
    return series[index] - lowest


def _scan_from_zero(alphas_deg: Sequence[float], *, upright: bool) -> list[int]:
    """The sample indices from the sample nearest alpha = 0 towards rising (falling) alpha."""
    if not alphas_deg:
        return []
    start = min(range(len(alphas_deg)), key=lambda k: abs(alphas_deg[k]))
    return list(range(start, len(alphas_deg))) if upright else list(range(start, -1, -1))


def local_extrema_from_zero(
    alphas_deg: Sequence[float], cl: Sequence[float], *, upright: bool
) -> list[int]:
    """Return the sample indices of the C_L peaks (upright) or troughs (inverted) from alpha = 0.

    Args:
        alphas_deg: Angles of attack in degrees, rising.
        cl: Lift coefficient per sample.
        upright: ``True`` for the peaks above alpha = 0, ``False`` for the troughs below it.

    Returns:
        The indices into the series in scan order, empty if the curve does not turn on that side.
    """
    scan = _scan_from_zero(alphas_deg, upright=upright)
    return [scan[k] for k in local_extrema([cl[k] for k in scan], maximum=upright)]


def main_extremum_from_zero(
    alphas_deg: Sequence[float], cl: Sequence[float], *, upright: bool
) -> int | None:
    """Return the sample index of the main C_L peak (upright) or trough (inverted) from alpha = 0.

    The scan starts at the sample nearest alpha = 0 and runs towards rising alpha for a peak and
    falling alpha for a trough (canon K32); the main extremum is the record maximum (minimum) of
    that side with the largest fall (rise) behind it (:func:`main_extremum`).

    Args:
        alphas_deg: Angles of attack in degrees, rising.
        cl: Lift coefficient per sample.
        upright: ``True`` for the C_L,max branch (n > 0), ``False`` for the C_L,min branch.

    Returns:
        The index into the series, or ``None`` if the curve does not turn inside the range.
    """
    scan = _scan_from_zero(alphas_deg, upright=upright)
    found = main_extremum([cl[k] for k in scan], maximum=upright)
    return None if found is None else scan[found]


def first_crossing_below(
    alphas_deg: Sequence[float], cl: Sequence[float], alpha_start_deg: float, level: float
) -> float | None:
    """Return the angle where ``C_L`` first falls to ``level`` past a start sample (canon ``stall-break``).

    The scan runs forward from the sample at ``alpha_start_deg`` (the stall angle); the first sample
    with ``C_L <= level`` and its predecessor bracket the crossing, which is interpolated linearly
    between them. A sample on the level is the crossing itself.

    Args:
        alphas_deg: Angles of attack in degrees, rising.
        cl: Lift coefficient per sample.
        alpha_start_deg: The angle to start from; must be one of ``alphas_deg``.
        level: The lift coefficient to fall to.

    Returns:
        The interpolated angle in degrees, or ``None`` if the start is no sample or the series never
        falls to the level (the event is not bracketed; no sample is substituted, ADR 0020).
    """
    if alpha_start_deg not in alphas_deg:
        return None
    start = list(alphas_deg).index(alpha_start_deg)
    for k in range(start + 1, len(alphas_deg)):
        if cl[k] <= level:
            before, after = cl[k - 1], cl[k]
            share = (before - level) / (before - after) if before > after else 1.0
            return alphas_deg[k - 1] + share * (alphas_deg[k] - alphas_deg[k - 1])
    return None
