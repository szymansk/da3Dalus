"""Canon formula ``static-thrust-to-weight``: ``T_0 / W`` with ``T_0`` the thrust at ``V = 0``.

The formula embeds the propulsion relations (``embeds`` in the canon): the torque balance at
``V = 0``, the advance ratio, the table lookup and the thrust from the coefficient. It reads no
thrust value and holds no second implementation of any of them (ADR 0022). The weight is positive
by the canon (``aircraft-mass`` and ``gravity`` are ``positive: true``).
"""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.motor_propeller_equilibrium import declare_route
from aero_kernel.formulas.propeller_table_lookup import components_of
from aero_kernel.formulas.propulsion import (
    advance_ratio_of,
    equilibrium_of,
    optional,
    table_lookup_of,
    thrust_of,
)
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["static_thrust_to_weight"]

_STATIC_SPEED_MS = 0.0  # the definition of "static": V = 0


@formula("static-thrust-to-weight")
async def static_thrust_to_weight(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static thrust over the weight, from the motor-propeller balance at ``V = 0``.

    Args:
        x: ``w`` the weight in N, ``components``, ``rho`` in kg/m^3, ``k_v`` in rpm/V, ``i_0`` in A,
            ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are
            bound for route A and not read on route B.
        ctx: The formula context; it hands out the embedded relations.

    Returns:
        ``t0_w`` (1), canon quantity ``static-thrust-to-weight``.

    Raises:
        TypeError: If ``components`` is not the components document.
        FormulaError: The failures of the embedded relations, unchanged.
    """
    components = components_of(x)
    rho, d_prop = number(x, "rho"), number(x, "d_prop")
    balance = equilibrium_of(ctx)(
        ctx,
        components,
        _STATIC_SPEED_MS,
        rho,
        number(x, "k_v"),
        optional(x, "i_0"),
        optional(x, "r_m"),
        number(x, "u_bat"),
        d_prop,
    )
    j = advance_ratio_of(ctx)(_STATIC_SPEED_MS, balance.n_prop, d_prop)
    c_t = table_lookup_of(ctx)(components, j, balance.n_prop).c_t
    t_static = thrust_of(ctx)(c_t, rho, balance.n_prop, d_prop)
    declare_route(ctx)
    return {"t0_w": t_static / number(x, "w")}
