"""Canon formula ``aspect-ratio``: AR = b^2 / S (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["aspect_ratio"]


@formula("aspect-ratio")
async def aspect_ratio(x: Inputs, ctx: Context) -> dict[str, float]:
    """Aspect ratio of the reference wing.

    Args:
        x: ``s_ref`` the reference area in m^2, ``b_ref`` the span in m.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``ar`` dimensionless (canon quantity ``aspect-ratio``).
    """
    return {"ar": number(x, "b_ref") ** 2 / number(x, "s_ref")}
