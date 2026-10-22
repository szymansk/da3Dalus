"""Canon formula ``air-density-isa``: air density of the exact ISA (ARCHITECTURE ch. 8.8, K30)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["air_density_isa"]


@formula("air-density-isa")
async def air_density_isa(x: Inputs, ctx: Context) -> dict[str, float]:
    """Air density at an altitude, from the ATM adapter.

    Args:
        x: ``h`` the altitude in m.
        ctx: The formula context; ``ctx.solvers.atmosphere`` is the ISA tool.

    Returns:
        ``rho`` the air density in kg/m^3 (``air-density``), ``mu`` the dynamic viscosity in Pa s
        (``dynamic-viscosity``) and ``a`` the speed of sound in m/s (``speed-of-sound``), all of
        the ISA at the altitude.

    Raises:
        FormulaError: From the adapter, unchanged (``tool_unavailable``, or ``invalid_input``
            for an altitude outside the ISA range).
    """
    air = await ctx.solvers.atmosphere.state(number(x, "h"))
    return {"rho": air.density, "mu": air.dynamic_viscosity, "a": air.speed_of_sound}
