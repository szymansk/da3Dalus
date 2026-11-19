"""Canon formula ``motor-propeller-part-load``: battery power and current in level flight at ``V``.

Route B only (the manufacturer publishes ``R_m`` and ``I_0``; route A and the default ``I_0 = 0`` are
not built, gh-1411). The steps, with ``K_v' = 2 pi K_v / 60`` (rad/(V s)):

1. the angle of attack ``alpha`` where AeroBuildup's lift equals the weight at ``V`` (secant search),
   and the drag ``D`` there;
2. the propeller speed ``n_pl`` where ``C_T(J, n) rho n^2 D_prop^4 = D``, ``J = V / (n D_prop)``
   (the propeller table alone fixes it; bisection between neighbouring rpm blocks);
3. ``Q = C_P rho n_pl^2 D_prop^5 / (2 pi)``, ``I = I_0 + Q K_v'``, ``U_m = I R_m + 2 pi n_pl / K_v'``,
   ``P_bat = U_m I``, ``I_bat = P_bat / U_bat``;
4. ``r_T = D / T_full(V)`` with ``T_full`` the thrust at the full-throttle speed of
   ``motor-propeller-equilibrium``: a value, not a verdict (canon A10); above 1 the postcondition
   ``demand_within_full_throttle`` gives a ``warning``.
"""

import math
from collections.abc import Callable, Mapping
from itertools import pairwise
from typing import ParamSpec, TypeVar, cast

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.advance_ratio_from_speed import advance_ratio
from aero_kernel.formulas.motor_propeller_equilibrium import (
    Balance,
    declare_route,
    equilibrium,
    require_motor_values,
)
from aero_kernel.formulas.propeller_table_lookup import (
    Coefficients,
    components_of,
    table_lookup,
    table_of,
)
from aero_kernel.formulas.thrust_at_airspeed_from_coefficient import thrust
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import CheckResult, formula, postcondition

__all__ = ["demand_within_full_throttle", "motor_propeller_part_load"]

_P = ParamSpec("_P")
_R = TypeVar("_R")
_RPM_PER_HZ = 60.0


def _relation(ctx: Context, item: str, kind: Callable[_P, _R]) -> Callable[_P, _R]:
    """The embedded relation of ``item``, typed as the function it is (``kind`` names the type)."""
    del kind
    return cast("Callable[_P, _R]", ctx.embedded(item))


async def _level_flight_drag(x: Inputs, ctx: Context) -> float:
    """The drag in N at the angle of attack where AeroBuildup's lift equals the weight at ``V``.

    A secant search on ``L(alpha) - m g`` from the starting angles 0 and ``powertrain_alpha_step_deg``;
    the evaluations' caveats (regime, induced-drag factor) are forwarded, deduplicated by the engine.

    Raises:
        FormulaError: ``lift_balance_not_converged`` if the lift does not reach the weight within
            the configured number of evaluations (a speed the wing cannot hold).
    """
    airplane, air, v = airplane_of(x), air_state(x), number(x, "v")
    weight = number(x, "m") * number(x, "g")
    tolerance = config().powertrain_lift_tolerance.value
    limit = int(config().powertrain_lift_iterations.value)

    async def point(alpha: float) -> tuple[float, float]:
        evaluation = await ctx.solvers.opti.evaluate(airplane, air, v, alpha)
        forward_warnings(ctx, evaluation.warnings)
        return evaluation.forces.lift_n - weight, evaluation.forces.drag_n

    alpha_previous, alpha = 0.0, config().powertrain_alpha_step_deg.value
    miss_previous, drag = await point(alpha_previous)
    for _ in range(limit - 1):
        if abs(miss_previous) <= tolerance * weight:
            return drag
        miss, drag_here = await point(alpha)
        if abs(miss) <= tolerance * weight:
            return drag_here
        if miss == miss_previous:
            break
        alpha_previous, alpha = (
            alpha,
            alpha - miss * (alpha - alpha_previous) / (miss - miss_previous),
        )
        miss_previous = miss
    raise FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "lift_balance_not_converged",
        f"motor-propeller-part-load found no angle of attack with lift = weight ({weight:.4g} N) "
        f"at {v:.4g} m/s within {limit} evaluations.",
        "The wing may not carry the weight at this speed (weight above the maximum lift); "
        "give a higher flight speed or a lower mass.",
        detail={"v_ms": v, "weight_n": weight},
    )


def _solve_part_load_speed(
    components: Components,
    v: float,
    rho: float,
    d_prop: float,
    drag: float,
    tolerance: float,
    relations: tuple[Callable[..., float], Callable[..., Coefficients], Callable[..., float]],
) -> float:
    """The propeller speed in 1/s where the table's thrust equals the drag (bisection)."""
    advance, lookup, thrust_of = relations
    blocks = table_of(components).blocks

    def excess(n: float) -> float:
        coefficients = lookup(components, advance(v, n, d_prop), n)
        return thrust_of(coefficients.c_t, rho, n, d_prop) - drag

    seen: list[tuple[float, float | None]] = []
    for block in blocks:
        n = block.rpm / _RPM_PER_HZ
        try:
            seen.append((n, excess(n)))
        except FormulaError as error:
            if error.code != "outside_propeller_table":
                raise
            seen.append((n, None))
    for (n_low, f_low), (n_high, f_high) in pairwise(seen):
        if f_low is None or f_high is None or not f_low < 0.0 <= f_high:
            continue
        low, high = n_low, n_high
        while high - low > tolerance * high:
            middle = 0.5 * (low + high)
            if excess(middle) < 0.0:
                low = middle
            else:
                high = middle
        return 0.5 * (low + high)
    raise FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        f"the propeller table has no speed between {blocks[0].rpm:g} and {blocks[-1].rpm:g} rpm "
        f"at which its thrust equals the drag {drag:.4g} N at {v:.4g} m/s.",
        "Use a propeller whose table covers the thrust level of this flight; the kernel does not "
        "extrapolate.",
        detail={"drag_n": drag, "v_ms": v},
    )


@formula("motor-propeller-part-load")
async def motor_propeller_part_load(x: Inputs, ctx: Context) -> dict[str, float]:
    """Battery power and current of level flight at the flight speed, route B.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``components``, ``v`` in m/s, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm,
            ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are bound for route A
            and not read on route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded relations and
            declares the route.

    Returns:
        ``n_pl`` in 1/s, ``i_bat`` in A, ``p_bat`` in W and ``r_t`` (1).

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``lift_balance_not_converged``;
            ``outside_propeller_table``; ``no_thrust_at_full_throttle``; the adapter's failures.
    """
    components = components_of(x)
    i_0, r_m = require_motor_values(_optional(x, "i_0"), _optional(x, "r_m"))
    v, rho, d_prop = number(x, "v"), number(x, "rho"), number(x, "d_prop")
    k_v, u_bat = number(x, "k_v"), number(x, "u_bat")
    tolerance = config().powertrain_balance_tolerance.value
    drag = await _level_flight_drag(x, ctx)
    advance = _relation(ctx, "calc:advance-ratio-from-speed.default", advance_ratio)
    lookup = _relation(ctx, "calc:propeller-table-lookup.default", table_lookup)
    thrust_of = _relation(ctx, "calc:thrust-at-airspeed-from-coefficient.default", thrust)
    n_pl = _solve_part_load_speed(
        components, v, rho, d_prop, drag, tolerance, (advance, lookup, thrust_of)
    )
    coefficients = lookup(components, advance(v, n_pl, d_prop), n_pl)
    shaft_torque = coefficients.c_p * rho * n_pl**2 * d_prop**5 / (2.0 * math.pi)
    k_v_rad = 2.0 * math.pi * k_v / _RPM_PER_HZ
    current = i_0 + shaft_torque * k_v_rad
    terminal_voltage = current * r_m + 2.0 * math.pi * n_pl / k_v_rad
    p_bat = terminal_voltage * current
    balance: Balance = _relation(ctx, "calc:motor-propeller-equilibrium.default", equilibrium)(
        components, v, rho, k_v, i_0, r_m, u_bat, d_prop, tolerance
    )
    full = lookup(components, advance(v, balance.n_prop, d_prop), balance.n_prop)
    t_full = thrust_of(full.c_t, rho, balance.n_prop, d_prop)
    if not t_full > 0.0:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "no_thrust_at_full_throttle",
            f"motor-propeller-part-load: the drive train gives no thrust at full throttle at "
            f"{v:.4g} m/s (T_full = {t_full:.4g} N), so the thrust demand ratio is undefined.",
            "Use a propeller and motor that give thrust at this speed.",
            detail={"v_ms": v, "t_full_n": t_full},
        )
    declare_route(ctx)
    return {"n_pl": n_pl, "i_bat": p_bat / u_bat, "p_bat": p_bat, "r_t": drag / t_full}


@postcondition("motor-propeller-part-load", "demand_within_full_throttle")
def demand_within_full_throttle(x: Mapping[str, object], y: Mapping[str, object]) -> CheckResult:
    """The drag does not exceed the thrust at full throttle: ``r_T <= 1``.

    A violation is a value with a caveat (canon: ``on_violation: warning``): the speed cannot be
    held in level flight, and the other three outputs describe a demand the drive train cannot meet.
    """
    r_t = number(y, "r_t")
    if r_t <= 1.0:
        return CheckResult(state="held", message=f"the thrust demand ratio {r_t:.4g} is at most 1")
    return CheckResult(
        state="violated",
        message=(
            f"the thrust demand ratio {r_t:.4g} is above 1: the drag exceeds the thrust at full "
            "throttle, so this speed cannot be held in level flight and the battery power and "
            "current describe a demand the drive train cannot meet"
        ),
    )


def _optional(x: Inputs, name: str) -> float | None:
    """The value of an ``optional`` parameter, ``None`` if absent."""
    return None if x[name] is None else number(x, name)
