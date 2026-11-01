"""Canon formula ``lift-to-drag-ratio``: E = L / D, with the precondition ``drag_positive``."""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["drag_positive", "lift_to_drag_ratio"]


@precondition("lift-to-drag-ratio", "drag_positive")
def drag_positive(x: Inputs) -> CheckResult:
    """The drag must be greater than zero: the relation divides by it.

    Profile and induced drag are never negative, so a drag of zero or below (or not a number) can
    only come from a defective solver result. The canon declares the violation an error at this
    formula (``on_violation: error``): an infinite or negative glide ratio is never returned and
    nothing is substituted (ADR 0020). The bound is physical, not a tuned threshold.
    """
    drag = number(x, "d")
    if drag > 0.0:
        return CheckResult(state="held", message=f"the drag {drag} N is greater than zero")
    return CheckResult(
        state="violated",
        message=(
            f"the drag {drag} N is not greater than zero: "
            + ("not a number" if math.isnan(drag) else "physically impossible")
            + ", a defective solver result"
        ),
    )


@formula("lift-to-drag-ratio")
async def lift_to_drag_ratio(x: Inputs, ctx: Context) -> dict[str, float]:
    """The lift-to-drag ratio at the caller's operating point.

    Args:
        x: ``l`` the lift and ``d`` the drag in N (``d`` > 0 by the precondition).
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``e`` the lift-to-drag ratio (dimensionless, canon quantity ``lift-to-drag-ratio``).
    """
    return {"e": number(x, "l") / number(x, "d")}
