"""Canon formula ``vertical-tail-arm``: l_V,CG = x_v,25 - x_cg,design (ARCHITECTURE ch. 8.5, 8.13; gh-1272)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.tail_arm import tail_arm_from_cg
from aero_kernel.registry import formula

__all__ = ["vertical_tail_arm"]


@formula("vertical-tail-arm")
async def vertical_tail_arm(x: Inputs, ctx: Context) -> dict[str, float]:
    """The arm of the fin or V-tail, measured from the design CG as Drela defines it.

    Under worlds it runs once per assignment of ``neutral-point``, because the design CG is one
    (A11). For a V-tail the arm is to the V-tail's own quarter-chord MAC; what it projects to is
    the business of the tail volume (#1208). A length, no verdict (A10).

    Args:
        x: ``airplane`` the geometry and ``x_cg`` the design CG in m (``centre-of-gravity-design``).
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``l_v_cg`` in m, from the design CG to the quarter-chord MAC of the vertical tail.

    Raises:
        FormulaError: ``unsupported_layout`` unless there is exactly one ``vertical_tail`` or
            ``v_tail``.
    """
    return {"l_v_cg": await tail_arm_from_cg(x, ctx, ("vertical_tail", "v_tail"), "vertical tail")}
