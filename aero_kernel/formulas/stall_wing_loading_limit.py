"""Canon formula ``stall-wing-loading-limit``: (W/S)_max = 1/2 rho V_S,target^2 C_L,max.

Sadraey Eq. 4.31 (ARCHITECTURE ch. 8.12).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["stall_wing_loading_limit"]


@formula("stall-wing-loading-limit")
async def stall_wing_loading_limit(x: Inputs, ctx: Context) -> dict[str, float]:
    """The highest wing loading that still meets a stall-speed target.

    The canon binds ``rho`` to the ISA density at the set altitude (never a fixed sea-level value)
    and applies the formula only when the stall-speed target is given (``at_stall_speed_target``).

    Args:
        x: ``rho`` the air density in kg/m^3, ``v_s_target`` the stall-speed target in m/s,
            ``cl_max`` the maximum lift coefficient (1).
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``ws_max_stall`` in N/m^2 (canon quantity ``wing-loading-limit-stall``).
    """
    return {
        "ws_max_stall": 0.5 * number(x, "rho") * number(x, "v_s_target") ** 2 * number(x, "cl_max")
    }
