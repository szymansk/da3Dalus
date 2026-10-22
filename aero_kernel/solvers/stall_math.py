"""Pure helpers of the stall problem (canon ``stall-speed``, K32)."""

from collections.abc import Sequence

__all__ = ["first_extremum"]


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
