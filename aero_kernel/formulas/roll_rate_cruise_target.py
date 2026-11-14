"""Canon formula ``roll-rate-cruise-target``: the steady roll at the cruise-speed target (ch. 8.5, 8.8).

The same steady roll as ``roll-rate`` in the same two method worlds (A11), on the clean airplane at
``V_cruise,target``; it exists only when that target is given. The ``avl`` world beyond AVL's stated
range ``|p b / 2V| <= 0.10`` declares itself outside its validity and leaves the interval.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.roll_rate import steady_roll_rate
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["roll_rate_cruise_target"]


@formula("roll-rate-cruise-target")
async def roll_rate_cruise_target(x: Inputs, ctx: Context) -> dict[str, float]:
    """The roll rate at the aileron deflection ``delta_a`` and the cruise-speed target.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, the ISA air
            state ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in m/s, ``b_ref`` the span in m,
            ``v_cruise_target`` the cruise-speed target in m/s and ``delta_a`` the aileron
            deflection in degrees (positive = roll to the right).
        ctx: The formula context; ``ctx.world`` is the world, ``ctx.solvers`` the adapters.

    Returns:
        ``p`` in deg/s, positive for a roll to the right.

    Raises:
        TypeError: If a number is not a number or ``ctx.world`` is not a world of this formula.
        FormulaError: From the adapter, unchanged.
    """
    rate = await steady_roll_rate(x, ctx, number(x, "v_cruise_target"))
    return {"p": math.degrees(rate)}
