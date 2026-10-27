"""Canon formula ``lateral-static-stability-app``: AVL lateral derivatives at the approach speed (ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.lateral_stability import lateral_stability
from aero_kernel.registry import formula

__all__ = ["lateral_static_stability_app"]


@formula("lateral-static-stability-app")
async def lateral_static_stability_app(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static lateral-directional stability at the approach speed, ``V_app``.

    See :func:`aero_kernel.formulas.lateral_stability.lateral_stability`; ``v`` is bound to the
    approach speed. Under worlds it runs once per assignment of ``neutral-point``, because the design CG is
    the moment reference (A11).

    Args:
        x: ``airplane``, ``m``, ``g``, ``rho``, ``x_cg`` and ``v`` (the approach speed in m/s).
        ctx: The formula context.

    Returns:
        ``c_l_beta``, ``c_n_beta``, ``e_spiral`` and ``t2_spiral``.

    Raises:
        FormulaError: As :func:`aero_kernel.formulas.lateral_stability.lateral_stability`.
    """
    return await lateral_stability(x, ctx)
