"""Canon formula ``induced-drag-factor``: ``k = 1 / (pi e AR)``, with the precondition ``oswald_factor_positive``."""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["induced_drag_factor", "oswald_factor_positive"]


@precondition("induced-drag-factor", "oswald_factor_positive")
def oswald_factor_positive(x: Inputs) -> CheckResult:
    """The Oswald factor and the aspect ratio must be greater than zero: the relation divides by them.

    A fitted factor at or below zero is what ``parabolic-polar-fit`` declares as not physically
    meaningful; the canon declares the violation an error at this formula (``on_violation: error``),
    so no induced-drag factor is returned for it and nothing is substituted (ADR 0020). The bounds
    are algebraic, not tuned thresholds.
    """
    e_osw, ar = number(x, "e_osw"), number(x, "ar")
    if e_osw > 0.0 and ar > 0.0:
        return CheckResult(state="held", message=f"e = {e_osw} and AR = {ar} are greater than zero")
    return CheckResult(
        state="violated",
        message=(
            f"e = {e_osw} and AR = {ar}: both must be greater than zero (a non-positive Oswald "
            "factor is no induced drag)"
        ),
    )


@formula("induced-drag-factor")
async def induced_drag_factor(x: Inputs, ctx: Context) -> dict[str, float]:
    """The coefficient of ``C_L^2`` in the parabolic polar.

    Args:
        x: ``e_osw`` the Oswald factor (1) and ``ar`` the aspect ratio (1), both > 0 by the
            precondition.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``k`` (dimensionless, canon quantity ``induced-drag-factor``).
    """
    return {"k": 1.0 / (math.pi * number(x, "e_osw") * number(x, "ar"))}
