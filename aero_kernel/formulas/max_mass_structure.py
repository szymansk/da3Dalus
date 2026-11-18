"""Canon formula ``max-mass-structure``: the mass at which the spar no longer holds one g (ch. 8.12).

``m_max,struct = n_break,+ * m``: the break load factor scales inversely with the mass, so the mass
at which the spar breaks already at 1 g is the break load factor times the mass it was found at.
A physical limit, not a design load.
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["max_mass_structure"]


@formula("max-mass-structure")
async def max_mass_structure(x: Inputs, ctx: Context) -> dict[str, float]:
    """The largest mass the spar holds at one g: ``n_break,+ * m``.

    Args:
        x: ``n_break_pos`` the break load factor upward (1) and ``m`` the mass in kg it belongs to.
        ctx: The formula context (unused: a closed form).

    Returns:
        ``m_max_struct`` in kg.

    Raises:
        TypeError: If a number is not a number.
    """
    del ctx
    return {"m_max_struct": number(x, "n_break_pos") * number(x, "m")}
