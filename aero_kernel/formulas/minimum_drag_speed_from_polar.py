"""Canon formula ``minimum-drag-speed-from-polar``: best glide as an optimisation (ch. 8.5, 8.12).

The formula passes the airplane, the mass, the load factor and the ISA air state to the OPT adapter,
which brackets the first C_L peak and minimises the drag subject to the lift balance in the process
pool (the same procedure as ``stall-speed``, shared code; no postcondition, decided W9).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["minimum_drag_speed_from_polar"]


@formula("minimum-drag-speed-from-polar")
async def minimum_drag_speed_from_polar(x: Inputs, ctx: Context) -> dict[str, float]:
    """The speed at which the airplane carries ``n m g`` with the least drag, and the glide ratio there.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``n_load``
            the load factor (1 in level flight), and the ISA air state ``rho`` in kg/m^3, ``mu`` in
            Pa s and ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` solves the problem.

    Returns:
        ``v_md`` in m/s, ``e_max`` the lift-to-drag ratio there, ``alpha_md`` the angle of attack
        in degrees and ``cl_md`` the lift coefficient at the optimum.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``not_converged``).
    """
    glide = await ctx.solvers.opti.best_glide(
        airplane_of(x), number(x, "m"), number(x, "g"), number(x, "n_load"), air_state(x)
    )
    forward_warnings(ctx, glide.warnings)
    solution = glide.solution
    return {
        "v_md": solution.v_md,
        "e_max": solution.e_max,
        "alpha_md": solution.alpha_md,
        "cl_md": solution.cl_md,
    }
