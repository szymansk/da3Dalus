"""Canon formula ``mean-geometric-chord``: c_bar = S / b (ARCHITECTURE ch. 8.12)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["mean_geometric_chord"]


@formula("mean-geometric-chord")
async def mean_geometric_chord(x: Inputs, ctx: Context) -> dict[str, float]:
    """Mean geometric chord of the reference wing.

    Args:
        x: ``s_ref`` the reference area in m^2, ``b_ref`` the span in m.
        ctx: The formula context (unused: no solver, no caveat).

    Returns:
        ``c_bar`` in m (canon quantity ``mean-geometric-chord``).
    """
    return {"c_bar": number(x, "s_ref") / number(x, "b_ref")}
