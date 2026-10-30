"""Canon formula ``lift-coefficient-required``: C_L,req = n m g / (q S_ref) (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["lift_coefficient_required"]


@formula("lift-coefficient-required")
async def lift_coefficient_required(x: Inputs, ctx: Context) -> dict[str, float]:
    """The lift coefficient the lift balance demands at a load factor and a dynamic pressure.

    The value is a demand: whether the wing can deliver it (C_L,max) is the evaluation's question,
    not this formula's (canon A10).

    Args:
        x: ``n_load`` the load factor (1), ``m`` the mass in kg, ``g`` the gravity in m/s^2,
            ``q`` the dynamic pressure in Pa, ``s_ref`` the reference area in m^2.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``cl_req`` (1) (canon quantity ``lift-coefficient``).
    """
    lift_n = number(x, "n_load") * number(x, "m") * number(x, "g")
    return {"cl_req": lift_n / (number(x, "q") * number(x, "s_ref"))}
