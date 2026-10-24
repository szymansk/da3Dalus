"""Canon formula ``cg-for-target-margin``: x_CG,SM = x_NP - SM_target c_MAC (ARCHITECTURE ch. 8.13, A10)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["cg_for_target_margin"]


@formula("cg-for-target-margin")
async def cg_for_target_margin(x: Inputs, ctx: Context) -> dict[str, float]:
    """The centre of gravity that gives the target static margin: a design target, not a result.

    The static margin read the other way (ADR 0011): the CG follows from the wanted stability, and the
    designer places the parts so that the real CG lands here. A number, not a verdict: no band and no
    default target (A10). Under worlds it runs once per assignment of ``neutral-point``.

    Args:
        x: ``x_np`` the neutral point in m (geometry frame, aft positive), ``sm_target`` the wanted
            static margin (dimensionless), ``c_mac`` the mean aerodynamic chord in m.
        ctx: The formula context (unused: no solver, no caveat of its own).

    Returns:
        ``x_cg_sm`` in m, ahead of the neutral point by ``sm_target`` mean chords.
    """
    return {"x_cg_sm": number(x, "x_np") - number(x, "sm_target") * number(x, "c_mac")}
