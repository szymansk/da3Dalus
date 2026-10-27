"""Canon formula ``lateral-static-stability-mp``: AVL lateral derivatives at the minimum-sink speed (ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.lateral_stability import lateral_stability
from aero_kernel.registry import formula

__all__ = ["lateral_static_stability_mp"]


@formula("lateral-static-stability-mp")
async def lateral_static_stability_mp(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static lateral-directional stability at the minimum-sink speed, ``V_mp``.

    See :func:`aero_kernel.formulas.lateral_stability.lateral_stability`; ``v`` is bound to the
    minimum-sink speed. Under worlds it runs once per assignment of ``neutral-point``, because the design CG is
    the moment reference (A11).

    Args:
        x: ``airplane``, ``m``, ``g``, ``rho``, ``x_cg`` and ``v`` (the minimum-sink speed in m/s).
        ctx: The formula context.

    Returns:
        ``c_l_beta``, ``c_n_beta``, ``e_spiral`` and ``t2_spiral``.

    Raises:
        FormulaError: As :func:`aero_kernel.formulas.lateral_stability.lateral_stability`.
    """
    return await lateral_stability(x, ctx)
