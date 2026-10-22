"""Canon formula ``wing-loading``: W/S = m g / S (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["wing_loading"]


@formula("wing-loading")
async def wing_loading(x: Inputs, ctx: Context) -> dict[str, float]:
    """Wing loading from mass, gravity and reference area.

    Args:
        x: ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``s_ref`` the reference area in m^2.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``w_s`` in N/m^2 (canon quantity ``wing-loading``).
    """
    return {"w_s": number(x, "m") * number(x, "g") / number(x, "s_ref")}
