"""Canon formula ``minimum-sink-speed-from-polar``: the least sink rate as an optimisation.

The formula passes the airplane, the mass, the load factor and the ISA air state to the OPT adapter,
which brackets the first C_L peak and minimises the sink power ``D V`` subject to the lift balance in
the process pool (the same procedure as ``minimum-drag-speed-from-polar``, shared code). The Reynolds
coupling sits inside the constraint, because AeroBuildup forms the Reynolds number from ``V``.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["minimum_sink_speed_from_polar"]


@formula("minimum-sink-speed-from-polar")
async def minimum_sink_speed_from_polar(x: Inputs, ctx: Context) -> dict[str, float]:
    """The speed at which the airplane carries ``n m g`` with the least sink rate.

    Args:
        x: ``airplane`` the geometry, ``m`` the mass in kg, ``g`` the gravity in m/s^2, ``n_load``
            the load factor (1 in level flight), and the ISA air state ``rho`` in kg/m^3, ``mu`` in
            Pa s and ``a`` in m/s.
        ctx: The formula context; ``ctx.solvers.opti`` solves the problem.

    Returns:
        ``v_mp`` in m/s, ``alpha_mp`` the angle of attack in degrees and ``cl_mp`` the lift
        coefficient at the optimum.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``not_converged``; a bound
            of ``V`` or the lower bound of alpha active at the optimum is ``not_converged``).

    Warnings: ``minimum_sink_stall_limited`` (``practice``) if the optimum is the stall boundary:
        the sink power is still falling at the first C_L peak, and the value is returned there.
    """
    sink = await ctx.solvers.opti.min_sink(
        airplane_of(x), number(x, "m"), number(x, "g"), number(x, "n_load"), air_state(x)
    )
    forward_warnings(ctx, sink.warnings)
    solution = sink.solution
    return {"v_mp": solution.v_mp, "alpha_mp": solution.alpha_mp, "cl_mp": solution.cl_mp}
