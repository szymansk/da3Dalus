"""Canon formula ``battery-mass-from-capacity``: ``m_bat,pred = E_req / E*``."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["battery_mass_from_capacity"]


@formula("battery-mass-from-capacity")
async def battery_mass_from_capacity(x: Inputs, ctx: Context) -> dict[str, float]:
    """The mass of a battery pack that stores the required energy at the given specific energy.

    ``E*`` is the *pack* specific energy (a cell value gives a cell mass, too light for a pack);
    the caller states it with its basis, the formula divides. ``E* > 0`` is the canon's
    ``positive: true`` of ``battery-specific-energy``, checked at the input.

    Args:
        x: ``e_req`` the required energy in Wh, ``e_star`` the specific energy in Wh/kg.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``m_bat_pred`` in kg, canon quantity ``predicted-battery-mass``.
    """
    del ctx
    return {"m_bat_pred": number(x, "e_req") / number(x, "e_star")}
