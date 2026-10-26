"""Canon formula ``horizontal-tail-arm``: l_H,CG = x_h,25 - x_cg,design (ARCHITECTURE ch. 8.5, 8.13; gh-1272)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.tail_arm import tail_arm_from_cg
from aero_kernel.registry import formula

__all__ = ["horizontal_tail_arm"]


@formula("horizontal-tail-arm")
async def horizontal_tail_arm(x: Inputs, ctx: Context) -> dict[str, float]:
    """The arm of the horizontal tail, measured from the design CG as Drela defines it.

    Under worlds it runs once per assignment of ``neutral-point``, because the design CG is one
    (A11): the arm is an interval, never a number combined across worlds. A length, no verdict (A10).

    Args:
        x: ``airplane`` the geometry and ``x_cg`` the design CG in m (``centre-of-gravity-design``).
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``l_h_cg`` in m, from the design CG to the quarter-chord MAC of the horizontal tail.

    Raises:
        FormulaError: ``unsupported_layout`` unless there is exactly one ``horizontal_tail``.
    """
    return {"l_h_cg": await tail_arm_from_cg(x, ctx, ("horizontal_tail",), "horizontal tail")}
