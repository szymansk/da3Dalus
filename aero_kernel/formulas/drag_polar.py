"""Canon formula ``drag-polar``: ``C_D,par = C_D0 + k C_L^2`` (ADR 0026: a display quantity, not the solver drag)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["drag_polar"]


@formula("drag-polar")
async def drag_polar(x: Inputs, ctx: Context) -> dict[str, float]:
    """The drag coefficient of the fitted parabola at a lift coefficient.

    Args:
        x: ``cd0`` the zero-lift drag coefficient (1), ``k`` the induced-drag factor (1) and ``cl``
            the lift coefficient (1).
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``cd_par`` (dimensionless, canon quantity ``drag-coefficient-parabolic``): the parabola's
        value, never the aircraft's drag, which is the solver's (ADR 0026, ADR 0022).
    """
    cl = number(x, "cl")
    return {"cd_par": number(x, "cd0") + number(x, "k") * cl * cl}
