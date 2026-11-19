"""Canon formula ``advance-ratio-from-speed``: ``J = V / (n_prop D_prop)`` (Brandt & Selig 2011, II.F)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula, relation

__all__ = ["advance_ratio", "advance_ratio_from_speed"]


@relation("advance-ratio-from-speed")
def advance_ratio(v: float, n_prop: float, d_prop: float) -> float:
    """The advance ratio: the distance flown per revolution over the diameter.

    The relation embedded by the propulsion embedders and called by the formula below, so there
    is one implementation (ADR 0022).

    Args:
        v: Flight speed in m/s (zero is the static point).
        n_prop: Propeller speed in 1/s, > 0.
        d_prop: Propeller diameter in m, > 0.

    Returns:
        ``J`` (1).

    Raises:
        FormulaError: ``invalid_input`` if the propeller does not turn (``n_prop D_prop <= 0``): the
            advance ratio of a stopped propeller is undefined.
    """
    swept = n_prop * d_prop
    if not swept > 0.0:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "non_positive_value",
            f"advance-ratio-from-speed needs n_prop * D_prop > 0, got {swept} m/s.",
            "Give a turning propeller: a positive propeller speed and diameter.",
            parameter="n_prop",
        )
    return v / swept


@formula("advance-ratio-from-speed")
async def advance_ratio_from_speed(x: Inputs, ctx: Context) -> dict[str, float]:
    """Read the advance ratio at the flight speed.

    Args:
        x: ``v`` in m/s, ``n_prop`` in 1/s, ``d_prop`` in m.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``j`` (1), canon quantity ``advance-ratio``.
    """
    del ctx
    return {"j": advance_ratio(number(x, "v"), number(x, "n_prop"), number(x, "d_prop"))}
