"""Canon formula ``motor-propeller-part-load``: battery power and current in level flight at ``V``.

Route B only (the manufacturer publishes ``R_m`` and ``I_0``; route A and the default ``I_0 = 0`` are
not built, gh-1411). The steps, with ``K_v' = 2 pi K_v / 60`` (rad/(V s)):

1. the angle of attack ``alpha`` where AeroBuildup's lift equals the weight at ``V`` (secant search on
   the rising part of the lift curve), and the drag ``D`` there;
2. the propeller speed ``n_pl`` where ``C_T(J, n) rho n^2 D_prop^4 = D``, ``J = V / (n D_prop)``
   (the propeller table alone fixes it; bisection between neighbouring covered rpm blocks);
3. ``Q = C_P rho n_pl^2 D_prop^5 / (2 pi)``, ``I = I_0 + Q K_v'``, ``U_m = I R_m + 2 pi n_pl / K_v'``,
   ``P_bat = U_m I``, ``I_bat = P_bat / U_bat``;
4. ``r_T = D / T_full(V)`` with ``T_full`` the thrust at the full-throttle speed of
   ``motor-propeller-equilibrium``: a value, not a verdict (canon A10); above 1 the postcondition
   ``demand_within_full_throttle`` gives a ``warning``.
"""

from collections.abc import Mapping
from itertools import pairwise

from aero_kernel.components import Components
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import declare_route, require_motor_values
from aero_kernel.formulas.propeller_table_lookup import components_of, table_of
from aero_kernel.formulas.propulsion import (
    RPM_PER_HZ,
    advance_ratio_of,
    balance_tolerance,
    bisect_root,
    current_for_torque,
    full_throttle_thrust,
    optional,
    propeller_torque,
    scan_grid,
    table_lookup_of,
    terminal_voltage,
    thrust_of,
)
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import CheckResult, formula, postcondition

__all__ = ["demand_within_full_throttle", "motor_propeller_part_load"]

_LEVEL_FLIGHT = 1.0  # the load factor of level flight: L = W (definition of n = L / W)


async def _level_flight_drag(x: Inputs, ctx: Context) -> float:
    """The drag in N of the level-flight point at ``V``: AeroBuildup's lift equals the weight there.

    The kernel's one lift-equals-weight solve (``OptiAdapter.level_flight_point``, the machinery of the
    level-flight polar): an alpha sweep plus secant steps bounded by the first lift peak, with the
    tolerance and step limit of ``config.yaml`` (``opt_level_*``). Its caveats are forwarded.

    Raises:
        FormulaError: ``not_converged`` from the adapter if the weight is not carried before the
            first lift peak at this speed.
    """
    found = await ctx.solvers.opti.level_flight_point(
        airplane_of(x), number(x, "m"), number(x, "g"), air_state(x), number(x, "v"), _LEVEL_FLIGHT
    )
    forward_warnings(ctx, found.warnings)
    return found.point.drag_n


def _solve_part_load_speed(
    ctx: Context,
    components: Components,
    v: float,
    rho: float,
    d_prop: float,
    drag: float,
) -> float:
    """The propeller speed in 1/s where the table's thrust equals the drag (bisection).

    The thrust minus the drag is evaluated at the table's rpm blocks that cover this airspeed; the
    lowest neighbouring pair of covered blocks with a sign change is bisected.
    """
    advance, lookup, thrust = advance_ratio_of(ctx), table_lookup_of(ctx), thrust_of(ctx)

    def shortfall(n: float) -> float:
        """Drag minus thrust: negative where the propeller out-pulls the drag."""
        return drag - thrust(lookup(components, advance(v, n, d_prop), n).c_t, rho, n, d_prop)

    blocks = table_of(components).blocks
    points = scan_grid(lambda n: (shortfall(n), 0.0), [b.rpm / RPM_PER_HZ for b in blocks])
    for low, high in pairwise(points):
        if low.residual is None or high.residual is None or not low.residual > 0.0 >= high.residual:
            continue
        return bisect_root(shortfall, low.n, high.n, balance_tolerance())
    covered = sum(p.residual is not None for p in points)
    raise FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        f"motor-propeller-part-load found no speed on the rpm grid points the table covers at "
        f"{v:.4g} m/s ({covered} of {len(points)} grid points) at which the propeller thrust equals "
        f"the drag {drag:.4g} N. A balance between a covered and an uncovered point is not searched.",
        "Use a propeller whose table covers the thrust level of this flight; the kernel does not "
        "extrapolate.",
        detail={"drag_n": drag, "v_ms": v, "covered_grid_points": covered},
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
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``;
            ``outside_propeller_table``; ``no_thrust_at_full_throttle``; the adapter's failures (``not_converged``).
    """
    components = components_of(x)
    i_0, r_m = require_motor_values(optional(x, "i_0"), optional(x, "r_m"))
    v, rho, d_prop = number(x, "v"), number(x, "rho"), number(x, "d_prop")
    k_v, u_bat = number(x, "k_v"), number(x, "u_bat")
    drag = await _level_flight_drag(x, ctx)
    n_pl = _solve_part_load_speed(ctx, components, v, rho, d_prop, drag)
    c_p = table_lookup_of(ctx)(components, advance_ratio_of(ctx)(v, n_pl, d_prop), n_pl).c_p
    current = current_for_torque(propeller_torque(c_p, rho, n_pl, d_prop), i_0, k_v)
    p_bat = terminal_voltage(current, r_m, n_pl, k_v) * current
    t_full = full_throttle_thrust(ctx, components, v, rho, k_v, i_0, r_m, u_bat, d_prop)
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
