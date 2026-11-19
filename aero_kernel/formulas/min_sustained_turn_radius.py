"""Canon formula ``min-sustained-turn-radius``: the tightest level turn the airplane can hold at full throttle.

A sustained turn is level at constant speed: ``L = n m g`` and ``T >= D(V, n)``. The entry minimises
``r = V^2 / (g sqrt(n^2 - 1))`` over ``V``, ``alpha``, ``n``, ``n_prop`` with ``1 <= n <= n_lim``. The same
search as :mod:`aero_kernel.formulas.max_sustained_turn_rate` with the objective ``-r``: the highest sustained
load factor per speed (the drag solve at the load factor ``n``, the full-throttle thrust, bisection), then the
minimum of ``r`` over the speed (scan, golden section). The limit that binds, ``thrust``, ``wing`` or
``structure``, is declared with the notice ``powered_limit_declared``.
"""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.powered_flight import PoweredFlight, sustained_turn
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula

__all__ = ["min_sustained_turn_radius"]


def turn_radius(g: float, v: float, n: float) -> float:
    """The radius of a coordinated level turn in m: ``V^2 / (g sqrt(n^2 - 1))`` (Sadraey sec. 12.6.2)."""
    return v * v / (g * math.sqrt(n * n - 1.0))


@formula("min-sustained-turn-radius")
async def min_sustained_turn_radius(x: Inputs, ctx: Context) -> dict[str, float]:
    """The minimum sustained turn radius at full throttle and the speed it is flown at.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``n_lim`` the limit load factor, ``k_v`` in rpm/V, ``i_0`` in A,
            ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound
            for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations, declares
            the route and the limit that binds. Warnings of the answer's evaluation are forwarded,
            those of the iterates are not.

    Returns:
        ``r_min`` in m and ``v_r`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if no speed holds a turn at full throttle (also
            ``n_lim`` not above 1); ``not_converged``; the failures of the
            drive train (``missing_input``, ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)
    gravity = number(x, "g")
    v_r, limit = await sustained_turn(
        flight, number(x, "n_lim"), lambda v, n: -turn_radius(gravity, v, n)
    )
    return {"r_min": turn_radius(gravity, v_r, limit.n), "v_r": v_r}
