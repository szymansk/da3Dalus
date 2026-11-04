"""Canon formula ``aerobuildup-evaluation``: L and the kernel's D of AeroBuildup at (V, alpha) (#1346).

One numeric AeroBuildup run at the caller's operating point in the bound ISA air state (#1201); tool
AB, run by the OPT adapter, which owns every AeroBuildup call (ADR 0022). The airplane is converted
once, by the adapter's ``to_asb_airplane`` (the fuselage equivalent-section rule of #1307 included).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["aerobuildup_evaluation"]


@formula("aerobuildup-evaluation")
async def aerobuildup_evaluation(x: Inputs, ctx: Context) -> dict[str, float]:
    """Lift and drag of the airplane at ``(V, alpha)``.

    Args:
        x: ``airplane`` the geometry, ``v`` the flight speed in m/s, ``alpha`` the angle of attack
            in degrees, and the ISA air state ``rho`` in kg/m^3, ``mu`` in Pa s and ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` runs AeroBuildup.

    Returns:
        ``l`` the lift in N as AeroBuildup returns it, ``d`` the kernel's drag in N
        (``solvers.aerobuildup.kernel_drag``: ``D_profile + k_e,D0 * D_induced``, #1346).

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``invalid_input``,
            ``unsupported_configuration``).
    """
    evaluation = await ctx.solvers.opti.evaluate(
        airplane_of(x), air_state(x), number(x, "v"), number(x, "alpha")
    )
    forward_warnings(ctx, evaluation.warnings)
    return {"l": evaluation.forces.lift_n, "d": evaluation.forces.drag_n}
