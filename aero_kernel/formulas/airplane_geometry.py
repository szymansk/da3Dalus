"""Canon formula ``airplane-geometry``: S_ref, b_ref, c_MAC of the main wing (ARCHITECTURE ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import airplane_of
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties, main_wing_properties
from aero_kernel.registry import formula

__all__ = ["airplane_geometry"]


def _declare_centreline(
    ctx: Context, properties: MainWingProperties, airplane: AirplaneGeometry
) -> None:
    """Declare that the reference planform was carried to the centreline (ADR 0020)."""
    name = next(w.name for w in (airplane.wings or {}).values() if w.surface_type == "main_wing")
    if properties.extended_m > 0.0:
        what, key, metres = (
            "root section extended with its chord",
            "extended_m",
            properties.extended_m,
        )
    else:
        what, key, metres = "stored side clipped", "clipped_m", properties.clipped_m
    ctx.warn(
        "reference_wing_at_centreline",
        f"The reference wing is carried to the centreline (convention of the reference planform): "
        f"the {what} by {metres * 1000:.3g} mm at y = 0 of the main wing {name!r}.",
        {"wing": name, key: metres},
    )


@formula("airplane-geometry")
async def airplane_geometry(x: Inputs, ctx: Context) -> dict[str, float]:
    """Reference area, span and mean aerodynamic chord of the main wing.

    The definition (projected onto the x-y plane, twist-independent) lives in
    :func:`aero_kernel.geometry_properties.main_wing_properties`.

    Args:
        x: ``airplane`` the geometry document.
        ctx: The formula context (unused: GEO is a plain read of the geometry, ch. 8.8).

    Returns:
        ``s_ref`` in m^2 (``wing-reference-area``), ``b_ref`` in m (``wing-span``) and ``c_mac``
        in m (``mean-aerodynamic-chord``).

    Raises:
        TypeError: If ``airplane`` is not the geometry document.
        FormulaError: From :func:`main_wing_properties`, unchanged.
    """
    airplane = airplane_of(x)
    properties = main_wing_properties(airplane)
    if properties.extended_m > 0.0 or properties.clipped_m > 0.0:
        _declare_centreline(ctx, properties, airplane)
    return {"s_ref": properties.s_ref, "b_ref": properties.b_ref, "c_mac": properties.c_mac}
