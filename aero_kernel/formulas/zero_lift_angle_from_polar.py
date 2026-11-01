"""Canon formula ``zero-lift-angle-from-polar``: the root of C_L(V, alpha) and the slope there.

``alpha_0`` solves ``C_L(V, alpha) = 0`` with IPOPT over AeroBuildup, started at 0 deg with no angle
range; ``C_Lalpha`` is ``dC_L/dalpha`` at ``(V, alpha_0)`` by automatic differentiation of the same
model function, per radian. Two applications bind ``v`` to the speed of an optimum (``best_glide``:
``minimum-drag-speed``, ``minimum_sink``: ``minimum-sink-speed``); one implementation serves both
(ARCHITECTURE ch. 8.5).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["zero_lift_angle_from_polar"]


@formula("zero-lift-angle-from-polar")
async def zero_lift_angle_from_polar(x: Inputs, ctx: Context) -> dict[str, float]:
    """The zero-lift angle of attack and the lift-curve slope at it, at the bound speed.

    Args:
        x: ``airplane`` the geometry, ``v`` the speed of the application's optimum in m/s, and the
            ISA air state ``rho`` in kg/m^3, ``mu`` in Pa s and ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` solves the root.

    Returns:
        ``alpha_0`` in degrees and ``cl_alpha`` in 1/rad.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``invalid_input``,
            ``unsupported_configuration``, ``not_converged``).
    """
    found = await ctx.solvers.opti.zero_lift(airplane_of(x), air_state(x), number(x, "v"))
    forward_warnings(ctx, found.warnings)
    return {"alpha_0": found.solution.alpha_0_deg, "cl_alpha": found.solution.cl_alpha_per_rad}
