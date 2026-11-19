"""Canon formula ``minimum-drag-speed-closed-form``: ``V_md,probe = sqrt(2 (W/S) / (rho sqrt(C_D0 / k)))``.

The Probe of ``minimum-drag-speed`` (ADR 0026): its own quantity ``minimum-drag-speed-probe``
``checks`` the optimisation's value and is never substituted for it.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["minimum_drag_speed_closed_form", "parabola_defined"]


@precondition("minimum-drag-speed-closed-form", "parabola_defined")
def parabola_defined(x: Inputs) -> CheckResult:
    """``C_D0``, ``k``, ``rho`` and ``W/S`` must be greater than zero, else there is no minimum-drag speed.

    The canon declares the violation an error at this formula (``on_violation: error``); nothing is
    substituted (ADR 0020). The bounds are algebraic, not tuned thresholds.
    """
    values = {name: number(x, name) for name in ("cd0", "k", "rho", "w_s")}
    if all(value > 0.0 for value in values.values()):
        return CheckResult(state="held", message="C_D0, k, rho and W/S are greater than zero")
    return CheckResult(
        state="violated",
        message=(
            f"C_D0 = {values['cd0']}, k = {values['k']}, rho = {values['rho']} and "
            f"W/S = {values['w_s']}: all four must be greater than zero, else the parabola has "
            "no minimum-drag speed"
        ),
    )


@formula("minimum-drag-speed-closed-form")
async def minimum_drag_speed_closed_form(x: Inputs, ctx: Context) -> dict[str, float]:
    """The speed at which the parabola ``C_D0 + k C_L^2`` carries the weight with the least drag.

    Args:
        x: ``w_s`` the wing loading in N/m^2, ``rho`` the air density in kg/m^3, ``cd0`` the
            zero-lift drag coefficient (1) and ``k`` the induced-drag factor (1), all > 0 by the
            precondition.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``v_md_probe`` in m/s (canon quantity ``minimum-drag-speed-probe``).
    """
    cl_md = math.sqrt(number(x, "cd0") / number(x, "k"))
    return {"v_md_probe": math.sqrt(2.0 * number(x, "w_s") / (number(x, "rho") * cl_md))}
