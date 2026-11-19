"""Canon formula ``motor-propeller-part-load``: battery power and current in level flight at ``V``.

Route B only (the manufacturer publishes ``R_m`` and ``I_0``; route A and the default ``I_0 = 0`` are
not built, gh-1411). The steps, with ``K_v' = 2 pi K_v / 60`` (rad/(V s)):

1. the angle of attack ``alpha`` where AeroBuildup's lift equals the weight at ``V`` (secant search on
   the rising part of the lift curve), and the drag ``D`` there;
2. the propeller speed ``n_pl`` where ``C_T(J, n) rho n^2 D_prop^4 = D``, ``J = V / (n D_prop)``
   (the propeller table alone fixes it; bisection between neighbouring covered points: the rpm blocks
   and the coverage edges between a covered and an uncovered block, gh-1417);
3. ``Q = C_P rho n_pl^2 D_prop^5 / (2 pi)``, ``I = I_0 + Q K_v'``, ``U_m = I R_m + 2 pi n_pl / K_v'``,
   ``P_bat = U_m I``, ``I_bat = P_bat / U_bat``;
4. ``r_T = D / T_full(V)`` with ``T_full`` the thrust at the full-throttle speed of
   ``motor-propeller-equilibrium``: a value, not a verdict (canon A10); above 1 the postcondition
   ``demand_within_full_throttle`` gives a ``warning``.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from aero_kernel.components import Components
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import declare_route, require_motor_values
from aero_kernel.formulas.propeller_table_lookup import components_of, table_of
from aero_kernel.formulas.propulsion import (
    RPM_PER_HZ,
    PartLoad,
    advance_ratio_of,
    balance_tolerance,
    bisect_root,
    covered_pairs,
    current_for_torque,
    full_throttle_thrust,
    level_flight_at,
    optional,
    part_load_of,
    propeller_torque,
    scan_grid,
    table_lookup_of,
    terminal_voltage,
    thrust_of,
)
from aero_kernel.formulas.values import forward_warnings, number
from aero_kernel.registry import CheckResult, formula, postcondition, relation
from aero_kernel.schema import KernelWarning

__all__ = [
    "SpeedPoint",
    "demand_within_full_throttle",
    "energy_over_power",
    "forward_part_load_caveats",
    "motor_propeller_part_load",
    "part_load",
    "part_load_at",
    "solve_part_load_speed",
]

_SECONDS_PER_HOUR = 3600.0  # s per h: converts the energy in Wh to J


def solve_part_load_speed(
    ctx: Context,
    components: Components,
    v: float,
    rho: float,
    d_prop: float,
    drag: float,
) -> float:
    """The propeller speed in 1/s where the table's thrust equals the drag (bisection).

    The drag minus the thrust is evaluated at the table's rpm blocks that cover this airspeed and at the
    coverage edge between a covered and an uncovered block (gh-1417); the lowest neighbouring pair of
    covered points with a sign change is bisected.
    """
    advance, lookup, thrust = advance_ratio_of(ctx), table_lookup_of(ctx), thrust_of(ctx)

    def shortfall(n: float) -> float:
        """Drag minus thrust: negative where the propeller out-pulls the drag."""
        return drag - thrust(lookup(components, advance(v, n, d_prop), n).c_t, rho, n, d_prop)

    blocks = table_of(components).blocks
    points = scan_grid(lambda n: (shortfall(n), 0.0), [b.rpm / RPM_PER_HZ for b in blocks])
    for low, high in covered_pairs(points):
        if low.residual is None or high.residual is None or not low.residual > 0.0 >= high.residual:
            continue
        return bisect_root(shortfall, low.n, high.n, balance_tolerance())
    grid = [p for p in points if not p.edge]
    covered = sum(p.residual is not None for p in grid)
    raise FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        f"motor-propeller-part-load found no speed where the table covers the advance ratio at "
        f"{v:.4g} m/s ({covered} of {len(grid)} grid points covered, {len(points) - len(grid)} "
        f"coverage edge(s) located) at which the propeller thrust equals the drag {drag:.4g} N: the "
        f"thrust minus the drag does not change sign between two covered points or between a "
        f"coverage edge and the covered grid point next to it, so the balance, if there is one, lies "
        f"where the table has no data.",
        "Use a propeller whose table covers the thrust level of this flight; the kernel does not "
        "extrapolate.",
        detail={
            "drag_n": drag,
            "v_ms": v,
            "covered_grid_points": covered,
            "coverage_edges": len(points) - len(grid),
        },
    )


@relation("motor-propeller-part-load")
def part_load(
    ctx: Context,
    components: Components,
    v: float,
    rho: float,
    k_v: float,
    i_0: float,
    r_m: float,
    u_bat: float,
    d_prop: float,
    drag: float,
) -> PartLoad:
    """The drive train's part-load point at the airspeed ``v`` against the drag ``drag`` in N.

    The relation embedded by the formulas that need the battery power at a speed (ADR 0022): it
    reaches the other propulsion relations through ``ctx.embedded`` and declares nothing itself;
    the caller declares the route (:func:`declare_route`) and forwards the caveats it chooses.

    Args:
        ctx: The formula context that hands out the embedded relations.
        components: The pushed components (motor, battery, propeller with its table).
        v: Airspeed in m/s.
        rho: Air density in kg/m^3.
        k_v: Voltage constant in rpm/V.
        i_0: No-load current in A.
        r_m: Winding resistance in ohm.
        u_bat: Pack voltage in V.
        d_prop: Propeller diameter in m.
        drag: The drag of the level-flight point at ``v`` in N.

    Returns:
        The propeller speed, battery current, battery power and thrust demand ratio.

    Raises:
        FormulaError: ``outside_propeller_table``; ``no_thrust_at_full_throttle``; the failures of
            the embedded relations.
    """
    advance, lookup = advance_ratio_of(ctx), table_lookup_of(ctx)
    n_pl = solve_part_load_speed(ctx, components, v, rho, d_prop, drag)
    c_p = lookup(components, advance(v, n_pl, d_prop), n_pl).c_p
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
    return PartLoad(n_pl=n_pl, i_bat=p_bat / u_bat, p_bat=p_bat, r_t=drag / t_full)


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
    v = number(x, "v")
    found = await level_flight_at(x, ctx, v)
    forward_warnings(ctx, found.warnings)
    point = part_load(
        ctx,
        components,
        v,
        number(x, "rho"),
        number(x, "k_v"),
        i_0,
        r_m,
        number(x, "u_bat"),
        number(x, "d_prop"),
        found.point.drag_n,
    )
    declare_route(ctx)
    return {"n_pl": point.n_pl, "i_bat": point.i_bat, "p_bat": point.p_bat, "r_t": point.r_t}


@dataclass(frozen=True)
class SpeedPoint:
    """The part-load point at one speed, with the caveats of its level-flight solve.

    Attributes:
        v: The speed in m/s.
        point: The part-load point.
        warnings: The caveats of the level-flight solve at ``v``.
    """

    v: float
    point: PartLoad
    warnings: tuple[KernelWarning, ...]


async def part_load_at(x: Inputs, ctx: Context, v: float) -> SpeedPoint:
    """The part-load point at ``v`` for an embedder: the level-flight solve, then the embedded relation.

    The one glue between the aerodynamic step and the embedded relation, for the formulas that embed
    ``motor-propeller-part-load`` (ADR 0022). Nothing is declared: an embedder that evaluates
    many speeds forwards only the caveats of the speeds its answer rests on.

    Args:
        x: The embedder's inputs: ``airplane``, ``m``, ``g``, ``rho``, ``mu``, ``a``, ``components``,
            ``k_v``, ``i_0``, ``r_m``, ``u_bat``, ``d_prop``.
        ctx: The embedder's context.
        v: The speed in m/s.

    Returns:
        The part-load point with the caveats of the level-flight solve.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; the failures of the
            level-flight solve and of the embedded relation, unchanged.
    """
    components = components_of(x)
    i_0, r_m = require_motor_values(optional(x, "i_0"), optional(x, "r_m"))
    found = await level_flight_at(x, ctx, v)
    point = part_load_of(ctx)(
        ctx,
        components,
        v,
        number(x, "rho"),
        number(x, "k_v"),
        i_0,
        r_m,
        number(x, "u_bat"),
        number(x, "d_prop"),
        found.point.drag_n,
    )
    return SpeedPoint(v=v, point=point, warnings=found.warnings)


def forward_part_load_caveats(
    ctx: Context, answered: Sequence[SpeedPoint], e_bat_wh: float
) -> None:
    """Report the caveats of the speeds an embedder's answer rests on, each once.

    What the engine does for the formula's own postcondition, the embedder does for the embedded
    relation (ch. 8.12: the handle runs no postcondition yet): a speed with ``r_T > 1`` gets the
    ``warning`` ``postcondition_violated`` of ``demand_within_full_throttle``. The level-flight caveats
    of the speeds are forwarded without repeats, and the route is declared once.

    Args:
        ctx: The embedder's context.
        answered: The speeds of the answer.
        e_bat_wh: The rated pack energy in Wh the answer used; the route notice says so.
    """
    seen: set[tuple[str, str]] = set()
    for speed in answered:
        for warning in speed.warnings:
            if (warning.code, warning.message) not in seen:
                seen.add((warning.code, warning.message))
                ctx.warn(warning.code, warning.message, warning.detail)
        verdict = demand_within_full_throttle({}, {"r_t": speed.point.r_t})
        if verdict.state == "violated":
            ctx.warn(
                "postcondition_violated",
                f"The postcondition `demand_within_full_throttle` of `motor-propeller-part-load` is "
                f"violated at {speed.v:.4g} m/s: {verdict.message}",
                {"postcondition": "demand_within_full_throttle", "v_ms": speed.v},
            )
    declare_route(ctx, e_bat_wh)


def energy_over_power(e_bat_wh: float, p_bat_w: float, v: float) -> float:
    """The time in s the rated energy lasts at the battery power: ``3600 E_bat / P_bat``.

    Raises:
        FormulaError: ``non_positive_battery_power`` if the drive train draws no power at ``v``
            (``P_bat <= 0``): no flight time follows, and a value would be a substitute.
    """
    if not p_bat_w > 0.0:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "non_positive_battery_power",
            f"the battery power at {v:.4g} m/s is {p_bat_w:.4g} W: the drive train draws no power "
            "there, so no flight time follows.",
            "Check the propeller table and the motor values for this speed.",
            detail={"v_ms": v, "p_bat_w": p_bat_w},
        )
    return _SECONDS_PER_HOUR * e_bat_wh / p_bat_w


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
