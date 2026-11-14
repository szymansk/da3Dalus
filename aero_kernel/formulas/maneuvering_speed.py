"""Canon formula ``maneuvering-speed``: the stall problem bound at ``n = n_lim`` (ch. 8.5, 8.12).

The formula passes the airplane, the mass, the limit load factor and the ISA air state to the OPT
adapter, which solves the same problem as ``stall-speed`` (shared code): the smallest speed at which
the wing still carries ``n_lim m g``, with ``C_L,max`` at the Reynolds number of that speed.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.flap_validity import warn_flap_validity
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["maneuvering_speed"]


@formula("maneuvering-speed")
async def maneuvering_speed(x: Inputs, ctx: Context) -> dict[str, float]:
    """The smallest speed at which the airplane carries the limit load ``n_lim m g``.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``n_lim``
            the limit load factor, and the ISA air state ``rho`` in kg/m^3, ``mu`` in Pa s and
            ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` solves the problem.

    Returns:
        ``v_a`` in m/s.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``not_converged``).
    """
    stall = await ctx.solvers.opti.stall(
        airplane_of(x), number(x, "m"), number(x, "g"), number(x, "n_lim"), air_state(x)
    )
    forward_warnings(ctx, stall.warnings)
    warn_flap_validity(ctx, airplane_of(x), stall.solution.diagnostics)
    return {"v_a": stall.solution.v_s}
