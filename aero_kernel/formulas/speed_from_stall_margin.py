"""Canon formula ``speed-from-stall-margin``: V = k_S V_S,cfg (ARCHITECTURE ch. 8.5, 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["speed_from_stall_margin"]


@formula("speed-from-stall-margin")
async def speed_from_stall_margin(x: Inputs, ctx: Context) -> dict[str, float]:
    """A named operating-point speed as a margin over the stall speed of its configuration.

    One implementation for the three applications (``approach``, ``touchdown``, ``takeoff``): the
    canon binds the configuration's stall speed and the margin target per application. No
    postcondition: the margin is a target, the product is a definition.

    Args:
        x: ``v_s_cfg`` the stall speed of the configuration in m/s, ``k_s`` the margin (1).
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``v`` in m/s (canon quantities ``approach-speed``, ``touchdown-speed``, ``takeoff-speed``).
    """
    return {"v": number(x, "k_s") * number(x, "v_s_cfg")}
