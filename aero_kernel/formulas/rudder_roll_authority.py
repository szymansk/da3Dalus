"""Canon formula ``rudder-roll-authority``: Drela's V_V B at V_md and V_mp (Design Rules, Eq. 10)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["rudder_roll_authority"]


@formula("rudder-roll-authority")
async def rudder_roll_authority(x: Inputs, ctx: Context) -> dict[str, float]:
    """The product of the vertical tail volume and the spiral parameter, at both speeds.

    Both factors are canon quantities, none recomputed (ADR 0022). Under worlds it runs once per
    assignment of ``neutral-point`` (A11). A number, no band (A10): Drela's 0.10 to 0.20 belongs to
    the evaluation.

    Args:
        x: ``v_v`` the vertical tail volume, ``b_spiral_md`` and ``b_spiral_mp`` the spiral
            parameter at the minimum-drag and the minimum-sink speed (all dimensionless).
        ctx: The formula context (unused: no solver, no caveat of its own).

    Returns:
        ``rra_md`` and ``rra_mp`` (dimensionless).
    """
    volume = number(x, "v_v")
    return {
        "rra_md": volume * number(x, "b_spiral_md"),
        "rra_mp": volume * number(x, "b_spiral_mp"),
    }
