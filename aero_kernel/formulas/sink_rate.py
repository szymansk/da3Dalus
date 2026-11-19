"""Canon formula ``sink-rate``: ``w = V C_D,par / C_L``, the small-glide-angle form of a steady glide.

The form drops ``cos(gamma)`` from ``sin(gamma) = tan(gamma) cos(gamma)`` and takes ``L = W`` instead
of ``W cos(gamma)``; both overstate the sink rate. Below the glide-ratio floor of the canon rule
``small-glide-angle`` the formula declares it (a precondition check cannot read a rule parameter,
ARCHITECTURE ch. 8.12), with the two exact overstatements, and still returns the value.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["drag_coefficient_positive", "lift_coefficient_positive", "sink_rate"]

RULE = "small-glide-angle"


@precondition("sink-rate", "lift_coefficient_positive")
def lift_coefficient_positive(x: Inputs) -> CheckResult:
    """The lift coefficient must be greater than zero: the relation divides by it.

    At ``C_L <= 0`` there is no steady glide. The canon declares the violation an error at this
    formula (``on_violation: error``); nothing is substituted (ADR 0020). The bound is physical,
    not a tuned threshold.
    """
    cl = number(x, "cl")
    if cl > 0.0:
        return CheckResult(state="held", message=f"C_L = {cl} is greater than zero")
    return CheckResult(
        state="violated",
        message=f"C_L = {cl} is not greater than zero: there is no steady glide at this point",
    )


@precondition("sink-rate", "drag_coefficient_positive")
def drag_coefficient_positive(x: Inputs) -> CheckResult:
    """The drag coefficient of the parabola must be greater than zero: a glide with no drag has no sink rate.

    A parabola with a non-positive ``C_D`` at this ``C_L`` is not physically meaningful (it can come
    from a non-physical fit); the canon declares the violation an error at this formula
    (``on_violation: error``), so no zero or negative sink rate is returned and nothing is
    substituted (ADR 0020). The bound is physical, not a tuned threshold.
    """
    cd = number(x, "cd")
    if cd > 0.0:
        return CheckResult(state="held", message=f"C_D = {cd} is greater than zero")
    return CheckResult(
        state="violated",
        message=f"C_D = {cd} is not greater than zero: the parabola has no drag at this point",
    )


@formula("sink-rate")
async def sink_rate(x: Inputs, ctx: Context) -> dict[str, float]:
    """The vertical descent rate of a steady glide at a speed, from the polar's drag and lift coefficients.

    Args:
        x: ``v`` the flight speed in m/s, ``cl`` the lift coefficient and ``cd`` the drag coefficient of the
            parabola (both 1 and > 0 by the preconditions).
        ctx: The formula context; ``ctx.solvers.rules`` holds the glide-ratio floor.

    Returns:
        ``w_sink`` in m/s (canon quantity ``sink-rate``).

    Warnings: ``small_glide_angle`` if ``C_L / C_D`` is below the floor ``min_glide_ratio`` of the
        rule ``small-glide-angle``; the value is returned all the same.
    """
    speed, cl, cd = number(x, "v"), number(x, "cl"), number(x, "cd")
    floor = ctx.solvers.rules.value(RULE, "min_glide_ratio")
    glide_ratio = cl / cd
    if glide_ratio < floor:
        gamma = math.atan(cd / cl)
        from_tan = 1.0 / math.cos(gamma) - 1.0
        from_lift = 1.0 / math.sqrt(math.cos(gamma)) - 1.0
        ctx.warn(
            "small_glide_angle",
            f"The glide ratio C_L/C_D = {glide_ratio:.3g} is below {floor:g}: the sink rate is "
            "the small-glide-angle form. It overstates the sink rate by "
            f"{100.0 * from_tan:.2g} % (tan for sin) and by a further {100.0 * from_lift:.2g} % "
            "(L = W for L = W cos(gamma), through the speed).",
            {
                "glide_ratio": glide_ratio,
                "glide_angle_deg": math.degrees(gamma),
                "from_tan_for_sin": from_tan,
                "from_lift_equals_weight": from_lift,
                "floor": floor,
            },
        )
    return {"w_sink": speed * cd / cl}
