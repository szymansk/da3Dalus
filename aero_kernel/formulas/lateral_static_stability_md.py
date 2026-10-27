"""Canon formula ``lateral-static-stability-md``: AVL lateral derivatives at the minimum-drag speed (ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.lateral_stability import lateral_stability
from aero_kernel.registry import formula

__all__ = ["lateral_static_stability_md"]


@formula("lateral-static-stability-md")
async def lateral_static_stability_md(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static lateral-directional stability at the minimum-drag speed, ``V_md``.

    See :func:`aero_kernel.formulas.lateral_stability.lateral_stability`; ``v`` is bound to the
    minimum-drag speed. Under worlds it runs once per assignment of ``neutral-point``, because the design CG is
    the moment reference (A11).

    Args:
        x: ``airplane``, ``m``, ``g``, ``rho``, ``x_cg`` and ``v`` (the minimum-drag speed in m/s).
        ctx: The formula context.

    Returns:
        ``c_l_beta``, ``c_n_beta``, ``e_spiral`` and ``t2_spiral``.

    Raises:
        FormulaError: As :func:`aero_kernel.formulas.lateral_stability.lateral_stability`.
    """
    return await lateral_stability(x, ctx)
