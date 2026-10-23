"""Canon formula ``static-margin``: SM = (x_NP - x_CG) / c_MAC (ARCHITECTURE ch. 8.13, A10)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["static_margin"]


@formula("static-margin")
async def static_margin(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static margin: the distance of the neutral point behind the CG, in mean chords.

    A number, not a verdict: no band, no flag, no target (A10). Under worlds it runs once per
    assignment of ``neutral-point`` (the world follows the value edge).

    Args:
        x: ``x_np`` the neutral point in m, ``x_cg`` the centre of gravity in m (both in the geometry
            frame, aft positive), ``c_mac`` the mean aerodynamic chord in m.
        ctx: The formula context (unused: no solver, no caveat of its own).

    Returns:
        ``sm`` dimensionless; positive when the neutral point is behind the CG.
    """
    return {"sm": (number(x, "x_np") - number(x, "x_cg")) / number(x, "c_mac")}
