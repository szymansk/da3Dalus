"""Pure helpers of the stall problem (canon ``stall-speed``, K32)."""

from collections.abc import Sequence

__all__ = ["first_extremum", "first_extremum_from_zero"]


def first_extremum(values: Sequence[float], *, maximum: bool) -> int | None:
    """Return the index of the first local extremum of a series scanned from its start.

    A maximum is a sample not lower than its predecessor and higher than its successor (a plateau
    counts at its last sample); a minimum is the mirror. The first or last sample is never an
    extremum, because a boundary sample is no turning point (ADR 0020).

    Args:
        values: The series in scan order, e.g. ``C_L`` over rising angle of attack.
        maximum: ``True`` for the first peak, ``False`` for the first trough.

    Returns:
        The index of the extremum, or ``None`` if the series does not turn inside its range.
    """
    sign = 1.0 if maximum else -1.0
    for index in range(1, len(values) - 1):
        before, here, after = (sign * values[i] for i in (index - 1, index, index + 1))
        if here >= before and here > after:
            return index
    return None


def first_extremum_from_zero(
    alphas_deg: Sequence[float], cl: Sequence[float], *, upright: bool
) -> int | None:
    """Return the sample index of the first C_L peak (upright) or trough (inverted) from alpha = 0.

    The scan starts at the sample nearest alpha = 0 and runs towards rising alpha for a peak and
    falling alpha for a trough (canon K32).

    Args:
        alphas_deg: Angles of attack in degrees, rising.
        cl: Lift coefficient per sample.
        upright: ``True`` for the C_L,max branch (n > 0), ``False`` for the C_L,min branch.

    Returns:
        The index into the series, or ``None`` if the curve does not turn inside the range.
    """
    if not alphas_deg:
        return None
    start = min(range(len(alphas_deg)), key=lambda k: abs(alphas_deg[k]))
    scan = list(range(start, len(alphas_deg))) if upright else list(range(start, -1, -1))
    found = first_extremum([cl[k] for k in scan], maximum=upright)
    return None if found is None else scan[found]
