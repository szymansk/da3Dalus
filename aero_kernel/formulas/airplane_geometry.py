"""Canon formula ``airplane-geometry``: S_ref, b_ref, c_MAC of the main wing (ARCHITECTURE ch. 8.5)."""

from collections.abc import Mapping

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import airplane_of
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["airplane_geometry"]


@precondition("airplane-geometry", "main_wing_has_spanwise_extent")
def main_wing_has_spanwise_extent(x: Mapping[str, object]) -> CheckResult:
    """The main wing extends further in y than in z over its stored sections (canon entry).

    A vertical surface typed ``main_wing`` is refused before AeroSandbox measures it: ASB takes a
    slant planform for one. The threshold (y-extent > z-extent, a mean inclination below 45 deg) is
    the proposal of #1253 and awaits the maintainer's approval.
    """
    airplane = airplane_of(x)
    for wing in (airplane.wings or {}).values():
        if wing.surface_type != "main_wing":
            continue
        ys = [section.xyz_le[1] for section in wing.x_secs]
        zs = [section.xyz_le[2] for section in wing.x_secs]
        y_extent, z_extent = max(ys) - min(ys), max(zs) - min(zs)
        if y_extent <= z_extent:
            return CheckResult(
                state="violated",
                message=(
                    f"the main wing {wing.name!r} extends {y_extent:.4g} m in y and {z_extent:.4g} m "
                    "in z, so it is a vertical surface; check its surface type (a fin or a V-tail "
                    "is not a main wing)"
                ),
            )
    return CheckResult(state="held", message="the main wing extends further in y than in z")


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
