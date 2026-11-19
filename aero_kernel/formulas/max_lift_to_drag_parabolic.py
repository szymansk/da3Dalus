"""Canon formula ``max-lift-to-drag-parabolic``: ``E_max,probe = 1/2 sqrt(pi e AR / C_D0)``.

The Probe of ``max-lift-to-drag-ratio`` (ADR 0026): its own quantity ``max-lift-to-drag-probe``
``checks`` the optimisation's value and is never substituted for it.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["max_lift_to_drag_parabolic", "parabola_defined"]


@precondition("max-lift-to-drag-parabolic", "parabola_defined")
def parabola_defined(x: Inputs) -> CheckResult:
    """``C_D0``, ``e`` and ``AR`` must be greater than zero, else the parabola has no maximum ``C_L / C_D``.

    The canon declares the violation an error at this formula (``on_violation: error``); nothing is
    substituted (ADR 0020). The bounds are algebraic, not tuned thresholds.
    """
    cd0, e_osw, ar = number(x, "cd0"), number(x, "e_osw"), number(x, "ar")
    if cd0 > 0.0 and e_osw > 0.0 and ar > 0.0:
        return CheckResult(state="held", message="C_D0, e and AR are greater than zero")
    return CheckResult(
        state="violated",
        message=(
            f"C_D0 = {cd0}, e = {e_osw} and AR = {ar}: all three must be greater than zero, "
            "else the parabola has no maximum glide ratio"
        ),
    )


@formula("max-lift-to-drag-parabolic")
async def max_lift_to_drag_parabolic(x: Inputs, ctx: Context) -> dict[str, float]:
    """The maximum ``C_L / C_D`` of the parabola ``C_D0 + C_L^2 / (pi AR e)``.

    Args:
        x: ``e_osw`` the Oswald factor (1), ``ar`` the aspect ratio (1) and ``cd0`` the zero-lift
            drag coefficient (1), all > 0 by the precondition.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``e_max_probe`` (dimensionless, canon quantity ``max-lift-to-drag-probe``).
    """
    arg = math.pi * number(x, "e_osw") * number(x, "ar") / number(x, "cd0")
    return {"e_max_probe": 0.5 * math.sqrt(arg)}
