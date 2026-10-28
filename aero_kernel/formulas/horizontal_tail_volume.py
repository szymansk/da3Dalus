"""Canon formula ``horizontal-tail-volume``: V_H = S_H l_H,CG / (S_ref c_MAC) (ARCHITECTURE ch. 8.5, 8.13)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.tail_arm import tail_key
from aero_kernel.formulas.values import airplane_of, number
from aero_kernel.registry import formula

__all__ = ["horizontal_tail_volume"]


@formula("horizontal-tail-volume")
async def horizontal_tail_volume(x: Inputs, ctx: Context) -> dict[str, float]:
    """The horizontal tail volume coefficient, Drela Eq. 3 with the reference chord ``c_MAC``.

    ``S_H`` is AeroSandbox's gross planform area of the one surface typed ``horizontal_tail``
    (``Wing.area(type="planform", include_centerline_distance=True)``), asked of the GEO adapter.
    For the one surface typed ``v_tail`` it is the effective area ``S_h,eff = sum S_i cos^2(nu_i)``
    over its panels (maintainer 2026-10-27, #1208).
    ``S_ref`` and ``c_MAC`` are those of ``airplane-geometry`` and the arm is
    ``horizontal-tail-arm``: none is recomputed here (ADR 0022). Drela writes the average chord
    ``S/b``; the canon uses ``c_MAC`` (maintainer 2026-10-27, #1273), declared in the entry. Under
    worlds it runs once per assignment of ``neutral-point``, because the arm depends on the design
    CG (A11). A number, no band (A10).

    Args:
        x: ``airplane`` the geometry, ``s_ref`` in m^2, ``c_mac`` in m and ``l_h_cg`` the arm in m.
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``v_h`` (dimensionless).

    Raises:
        FormulaError: ``unsupported_layout`` unless there is exactly one ``horizontal_tail`` or ``v_tail``; from
            the adapter, unchanged.
    """
    airplane = airplane_of(x)
    key = tail_key(airplane, ("horizontal_tail", "v_tail"), "horizontal tail")
    area = await ctx.solvers.geometry.horizontal_tail_area(airplane, key)
    return {"v_h": area * number(x, "l_h_cg") / (number(x, "s_ref") * number(x, "c_mac"))}
