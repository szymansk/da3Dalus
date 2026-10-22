"""Canon formula ``weight-from-mass``: W = m g (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["weight_from_mass"]


@formula("weight-from-mass")
async def weight_from_mass(x: Inputs, ctx: Context) -> dict[str, float]:
    """Weight from mass and gravity.

    Args:
        x: ``m`` the aircraft mass in kg, ``g`` the gravity in m/s^2.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``w`` the weight in N (canon quantity ``weight``).
    """
    return {"w": number(x, "m") * number(x, "g")}
