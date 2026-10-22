"""Canon formula ``airplane-geometry``: S_ref, b_ref, c_MAC of the main wing (ARCHITECTURE ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import formula

__all__ = ["airplane_geometry"]


@formula("airplane-geometry")
async def airplane_geometry(x: Inputs, ctx: Context) -> dict[str, float]:
    """Reference area, span and mean aerodynamic chord of the main wing.

    The definition (projected onto the x-y plane, twist-independent) lives in
    :meth:`aero_kernel.solvers.geometry.GeometryAdapter.main_wing_properties`.

    Args:
        x: ``airplane`` the geometry document.
        ctx: The formula context; ``ctx.solvers.geometry`` is the GEO adapter.

    Returns:
        ``s_ref`` in m^2 (``wing-reference-area``), ``b_ref`` in m (``wing-span``) and ``c_mac``
        in m (``mean-aerodynamic-chord``).

    Raises:
        TypeError: If ``airplane`` is not the geometry document.
        FormulaError: From the adapter, unchanged.
    """
    airplane = x["airplane"]
    if not isinstance(airplane, AirplaneGeometry):
        msg = f"parameter 'airplane' must be the geometry, got {type(airplane).__name__}"
        raise TypeError(msg)
    properties = await ctx.solvers.geometry.main_wing_properties(airplane)
    return {"s_ref": properties.s_ref, "b_ref": properties.b_ref, "c_mac": properties.c_mac}
