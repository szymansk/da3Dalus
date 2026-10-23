"""Canon formula ``dynamic-pressure``: q = 1/2 rho V^2 (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["dynamic_pressure"]


@formula("dynamic-pressure")
async def dynamic_pressure(x: Inputs, ctx: Context) -> dict[str, float]:
    """Dynamic pressure from air density and flight speed.

    Args:
        x: ``rho`` the air density in kg/m^3, ``v`` the flight speed in m/s.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``q`` the dynamic pressure in Pa (canon quantity ``dynamic-pressure``).
    """
    return {"q": 0.5 * number(x, "rho") * number(x, "v") ** 2}
