"""Canon formula ``airplane-geometry``: S_ref, b_ref, c_MAC of the main wing (ARCHITECTURE ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import airplane_of
from aero_kernel.registry import formula

__all__ = ["airplane_geometry"]


@formula("airplane-geometry")
async def airplane_geometry(x: Inputs, ctx: Context) -> dict[str, float]:
    """Reference area, span and mean aerodynamic chord of the main wing, as AeroSandbox measures them.

    The wing is chosen by ``surface_type`` ``main_wing``, never by list position. The values are
    ``Wing.area(type="planform", include_centerline_distance=True)``,
    ``Wing.span(type="yz", include_centerline_distance=True)`` and
    ``Wing.mean_aerodynamic_chord()`` (maintainer, 2026-10-25, gh-1262). Area and span both include
    the gap at the centreline; the flags are set in code, never left to ASB's defaults.

    Args:
        x: ``airplane`` the geometry document.
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``s_ref`` in m^2 (``wing-reference-area``), ``b_ref`` in m (``wing-span``) and ``c_mac``
        in m (``mean-aerodynamic-chord``).

    Raises:
        TypeError: If ``airplane`` is not the geometry document.
        FormulaError: From the adapter, unchanged (``tool_unavailable``,
            ``unsupported_configuration``).
    """
    properties = await ctx.solvers.geometry.main_wing_reference(airplane_of(x))
    return {"s_ref": properties.s_ref, "b_ref": properties.b_ref, "c_mac": properties.c_mac}
