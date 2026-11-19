"""Canon formula ``max-sustained-turn-rate``: the fastest level turn the airplane can hold at full throttle.

A sustained turn is level at constant speed: ``L = n m g`` and ``T >= D(V, n)``. The entry maximises
``omega = g sqrt(n^2 - 1) / V`` over ``V``, ``alpha``, ``n``, ``n_prop`` with ``1 <= n <= n_lim``. The lift
balance fixes ``alpha`` (the drag solve at the load factor ``n``, before the stall) and the torque balance
``n_prop`` (the full-throttle thrust); for each speed the highest load factor the thrust and the wing allow
is found by bisection (:func:`aero_kernel.formulas.powered_flight.sustained_load_factor`) and ``omega`` is
maximised over the speed (scan, golden section). Which limit binds at the optimum, ``thrust``, ``wing`` or
``structure``, is declared with the notice ``powered_limit_declared``.
"""

import math
from collections.abc import Mapping

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.powered_flight import PoweredFlight, sustained_turn
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["limit_load_factor_above_one", "max_sustained_turn_rate"]


@precondition("max-sustained-turn-rate", "limit_load_factor_above_one")
@precondition("min-sustained-turn-radius", "limit_load_factor_above_one")
def limit_load_factor_above_one(x: Mapping[str, object]) -> CheckResult:
    """The limit load factor must be above 1: a sustained turn needs ``1 < n <= n_lim``.

    The one implementation of the check of both sustained-turn entries.
    """
    n_lim = number(x, "n_lim")
    if n_lim > 1.0:
        return CheckResult(state="held", message=f"the limit load factor {n_lim:g} is above 1")
    return CheckResult(
        state="violated",
        message=(
            f"the limit load factor {n_lim:g} is not above 1, so no level turn is allowed "
            "(a turn needs a load factor above 1); give a higher limit load factor"
        ),
    )


def turn_rate(g: float, v: float, n: float) -> float:
    """The rate of a coordinated level turn in rad/s: ``g sqrt(n^2 - 1) / V`` (Sadraey sec. 12.6.2)."""
    return g * math.sqrt(n * n - 1.0) / v


@formula("max-sustained-turn-rate")
async def max_sustained_turn_rate(x: Inputs, ctx: Context) -> dict[str, float]:
    """The maximum sustained turn rate at full throttle and the speed it is flown at.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``n_lim`` the limit load factor, ``k_v`` in rpm/V, ``i_0`` in A,
            ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound
            for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations, declares
            the route and the limit that binds. Warnings of the answer's evaluation are forwarded,
            those of the iterates are not.

    Returns:
        ``omega_max`` in deg/s and ``v_omega`` in m/s.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` if no speed holds a turn at full throttle (also
            ``n_lim`` not above 1); ``not_converged``; the failures of the
            drive train (``missing_input``, ``outside_propeller_table``).
    """
    flight = PoweredFlight(x, ctx)
    gravity = number(x, "g")
    v_omega, limit = await sustained_turn(
        flight, number(x, "n_lim"), lambda v, n: turn_rate(gravity, v, n)
    )
    return {"omega_max": math.degrees(turn_rate(gravity, v_omega, limit.n)), "v_omega": v_omega}
