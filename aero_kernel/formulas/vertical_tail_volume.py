"""Canon formula ``vertical-tail-volume``: V_V = S_V l_V,CG / (S_ref b_ref) (ARCHITECTURE ch. 8.5, 8.13)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.tail_arm import tail_key
from aero_kernel.formulas.values import airplane_of, number
from aero_kernel.registry import formula

__all__ = ["vertical_tail_volume"]


@formula("vertical-tail-volume")
async def vertical_tail_volume(x: Inputs, ctx: Context) -> dict[str, float]:
    """The vertical tail volume coefficient, Sadraey Eq. 6.74 with Drela's arm from the design CG.

    ``S_V`` is AeroSandbox's planform area of the one surface typed ``vertical_tail`` or ``v_tail``
    (a V-tail's fin share ``S sin^2(nu)``), asked of the GEO adapter. ``S_ref`` and ``b_ref`` are
    those of ``airplane-geometry`` and the arm is ``vertical-tail-arm``: none is recomputed here
    (ADR 0022). Under worlds it runs once per assignment of ``neutral-point``, because the arm
    depends on the design CG (A11). A number, no band (A10).

    Args:
        x: ``airplane`` the geometry, ``s_ref`` in m^2, ``b_ref`` in m and ``l_v_cg`` the arm in m.
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``v_v`` (dimensionless).

    Raises:
        FormulaError: ``unsupported_layout`` unless there is exactly one ``vertical_tail`` or
            ``v_tail``; from the adapter, unchanged.
    """
    airplane = airplane_of(x)
    key = tail_key(airplane, ("vertical_tail", "v_tail"), "vertical tail")
    fin = await ctx.solvers.geometry.fin_area(airplane, key)
    return {"v_v": fin * number(x, "l_v_cg") / (number(x, "s_ref") * number(x, "b_ref"))}
