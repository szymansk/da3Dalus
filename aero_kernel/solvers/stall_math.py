"""Pure helpers of the stall problem (canon ``stall-speed``, K32)."""

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


def main_extremum(
    values: Sequence[float], *, maximum: bool, recovery_fraction: float
) -> int | None:
    """Return the index of the main extremum of a series: the stall of a lift curve.

    The rule (maintainer, 2026-11-27, gh-1423: the maximum "wo es danach richtig abstuerzt", "mit
    dem staerksten Einbruch ueber mehrere Grad dahinter"), for a maximum:

    1. The fall behind a local maximum (:func:`local_extrema`) is its value minus the lowest value
       reached behind it before the series has climbed back from that lowest value by more than
       ``recovery_fraction`` of what it had fallen so far, or up to the end of the series.
    2. The main maximum is the local maximum with the largest fall; of two with the same fall the
       first in scan order.

    A minimum is the mirror (the largest rise behind). A shoulder before the real maximum has a
    small fall because the curve recovers at once; a ledge inside a descent does not end the fall;
    a flat post-stall plateau has a small fall although it may be the highest maximum; a hump before
    the stall that is higher than the stall loses to it if the curve recovers behind the hump and
    drops behind the stall. The main maximum is therefore not always the highest one. The end of
    the series is no extremum.

    Args:
        values: The series in scan order, e.g. ``C_L`` over rising angle of attack.
        maximum: ``True`` for the main peak, ``False`` for the main trough.
        recovery_fraction: The share of a fall the series must climb back to end that fall
            (``opt_stall_recovery_fraction`` of the kernel's configuration).

    Returns:
        The index of the extremum, or ``None`` if the series does not turn inside its range.
    """
    sign = 1.0 if maximum else -1.0
    series = [sign * value for value in values]
    best: int | None = None
    best_fall = 0.0
    for index in local_extrema(series, maximum=True):
        fall = _fall_behind(series, index, recovery_fraction)
        if best is None or fall > best_fall:
            best, best_fall = index, fall
    return best


def _fall_behind(series: Sequence[float], index: int, recovery_fraction: float) -> float:
    """How far ``series`` falls behind ``index`` before it recovers by more than the fraction."""
    top = lowest = series[index]
    for value in series[index + 1 :]:
        lowest = min(lowest, value)
        if value - lowest > recovery_fraction * (top - lowest):
            break
    return top - lowest


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
    alphas_deg: Sequence[float], cl: Sequence[float], *, upright: bool, recovery_fraction: float
) -> int | None:
    """Return the sample index of the main C_L peak (upright) or trough (inverted) from alpha = 0.

    The scan starts at the sample nearest alpha = 0 and runs towards rising alpha for a peak and
    falling alpha for a trough (canon K32); the main extremum is the local maximum (minimum) of
    that side with the largest fall (rise) behind it (:func:`main_extremum`).

    Args:
        alphas_deg: Angles of attack in degrees, rising.
        cl: Lift coefficient per sample.
        upright: ``True`` for the C_L,max branch (n > 0), ``False`` for the C_L,min branch.
        recovery_fraction: The share of a fall the curve must climb back to end that fall
            (``opt_stall_recovery_fraction``).

    Returns:
        The index into the series, or ``None`` if the curve does not turn inside the range.
    """
    scan = _scan_from_zero(alphas_deg, upright=upright)
    found = main_extremum(
        [cl[k] for k in scan], maximum=upright, recovery_fraction=recovery_fraction
    )
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
