"""Canon formula ``motor-propeller-equilibrium``: the propeller speed where motor and propeller torque meet.

Route B only (the manufacturer publishes ``R_m`` and ``I_0``): Drela's three-parameter DC motor
(``motor1`` 1.1) against the ``C_P(J)`` table of the fitted propeller. Route A (``R_m`` absent) and the
default ``I_0 = 0`` are not built (gh-1411, complete data only): an absent value is a declared failure.

With ``K_v' = 2 pi K_v / 60`` (rad/(V s)) and the speed ``n`` in 1/s the balance is

    motor:      I(n) = (U_bat - 2 pi n / K_v') / R_m,   Q_m(n) = (I(n) - I_0) / K_v'
    propeller:  Q_p(n) = C_P(J, n) rho n^2 D^5 / (2 pi),   J = V / (n D)
    balance:    Q_m(n) = Q_p(n)

``Q_m`` falls and ``Q_p`` rises with ``n`` over the usual range. The residual ``Q_m - Q_p`` is evaluated
at the rpm blocks of the table (the grid) that lie below the motor's free-run speed and that the table
covers at this airspeed; the highest neighbouring pair of covered grid points with a sign change is
bisected. A root between a covered and an uncovered grid point is not searched (no edge refinement).
"""

from itertools import pairwise

from aero_kernel.components import Components
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.propeller_table_lookup import components_of, table_of
from aero_kernel.formulas.propulsion import (
    RPM_PER_HZ,
    Balance,
    GridPoint,
    advance_ratio_of,
    balance_tolerance,
    bisect_root,
    current_at_speed,
    motor_torque,
    optional,
    propeller_torque,
    scan_grid,
    table_lookup_of,
)
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula, relation
from pydantic import JsonValue

__all__ = ["declare_route", "equilibrium", "motor_propeller_equilibrium", "require_motor_values"]


def _absent(name: str, path: str) -> FormulaError:
    """``missing_input`` for a motor value route B needs and the components do not carry."""
    return FormulaError(
        ErrorCategory.INVALID_INPUT,
        "missing_input",
        f"motor-propeller-equilibrium needs `{path}` (route B: the published winding resistance "
        "and no-load current); route A and a default are not implemented.",
        "Push the manufacturer's value with the components; the kernel does not estimate it.",
        detail={"inputs": list[JsonValue]([path])},
        parameter=name,
    )


def require_motor_values(i_0: float | None, r_m: float | None) -> tuple[float, float]:
    """The no-load current and the winding resistance route B needs.

    Raises:
        FormulaError: ``missing_input`` naming the catalogue field if one is absent.
    """
    if r_m is None:
        raise _absent("r_m", "components.motor.rm_ohm")
    if i_0 is None:
        raise _absent("i_0", "components.motor.io_no_load_a")
    return i_0, r_m


def declare_route(ctx: Context) -> None:
    """Declare route B and what its resistance leaves out (ADR 0020, canon ``Q-PT-6``)."""
    ctx.warn(
        "powertrain_route_winding_resistance",
        "Route B ran (Q-PT-6): the manufacturer's winding resistance R_m and no-load current I_0 "
        "balance the torque. R_m is the winding only; ESC and cable resistance are not in it, so "
        "the voltage loss is slightly under-estimated, and the nominal pack voltage is used "
        "(no sag under load).",
        {"route": "B"},
    )


def _no_balance(points: list[GridPoint], v: float) -> FormulaError:
    """The declared failure of a scan that found no sign change between covered grid points."""
    covered = [p for p in points if p.residual is not None]
    windmilling = [p for p in covered if p.c_p is not None and p.c_p < 0.0]
    detail: dict[str, JsonValue] = {
        "v_ms": v,
        "grid_points": len(points),
        "covered_grid_points": len(covered),
    }
    if windmilling:
        return FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "propeller_windmilling",
            f"motor-propeller-equilibrium: at {v:.4g} m/s the propeller's power coefficient is "
            f"negative on {len(windmilling)} of {len(covered)} covered grid points (the airstream "
            "drives the propeller), so the torque balance of a driven propeller has no solution; "
            "windmilling is not modelled.",
            "Give a speed at which the propeller is driven by the motor.",
            detail=detail,
        )
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        "motor-propeller-equilibrium: no balance found on the rpm grid points the table covers at "
        f"{v:.4g} m/s ({len(covered)} of {len(points)} grid points, below the motor's free-run "
        "speed): the motor torque never crosses the propeller torque between two covered points. "
        "A balance between a covered and an uncovered point is not searched.",
        "Use a propeller whose table covers the speed this motor turns it at; the kernel does not "
        "extrapolate.",
        detail=detail,
    )


@relation("motor-propeller-equilibrium")
def equilibrium(
    ctx: Context,
    components: Components,
    v: float,
    rho: float,
    k_v: float,
    i_0: float | None,
    r_m: float | None,
    u_bat: float,
    d_prop: float,
) -> Balance:
    """The balance of the motor and the propeller at the airspeed (route B).

    The relation embedded by the propulsion embedders and called by the formula below (ADR 0022).
    It reaches the advance ratio and the table lookup through ``ctx.embedded``, so the context must
    belong to a formula whose canon entry embeds them (this one, or an embedder of this one).

    Args:
        ctx: The formula context that hands out the embedded relations.
        components: The pushed components (the propeller table).
        v: Flight speed in m/s (zero for the static point).
        rho: Air density in kg/m^3.
        k_v: Motor voltage constant in rpm/V.
        i_0: No-load current in A.
        r_m: Winding resistance in ohm.
        u_bat: Pack voltage in V (nominal; sag under load is not modelled).
        d_prop: Propeller diameter in m.

    Returns:
        The propeller speed and the torque at the balance.

    Raises:
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``outside_propeller_table``
            if no covered grid points bracket a balance; ``propeller_windmilling`` if the propeller
            is driven by the airstream there.
    """
    i_0, r_m = require_motor_values(i_0, r_m)
    advance, lookup = advance_ratio_of(ctx), table_lookup_of(ctx)

    def coefficient_power(n: float) -> float:
        return lookup(components, advance(v, n, d_prop), n).c_p

    def residual(n: float) -> float:
        current = current_at_speed(n, k_v, u_bat, r_m)
        return motor_torque(current, i_0, k_v) - propeller_torque(
            coefficient_power(n), rho, n, d_prop
        )

    def state(n: float) -> tuple[float, float]:
        return residual(n), coefficient_power(n)

    blocks = table_of(components).blocks
    n_top = min(blocks[-1].rpm / RPM_PER_HZ, k_v * u_bat / RPM_PER_HZ)
    grid = [b.rpm / RPM_PER_HZ for b in blocks if b.rpm / RPM_PER_HZ < n_top] + [n_top]
    points = scan_grid(state, grid)
    for low, high in reversed(list(pairwise(points))):
        if low.residual is None or high.residual is None or not low.residual > 0.0 >= high.residual:
            continue
        n_balance = bisect_root(residual, low.n, high.n, balance_tolerance())
        return Balance(
            n_balance, propeller_torque(coefficient_power(n_balance), rho, n_balance, d_prop)
        )
    raise _no_balance(points, v)


@formula("motor-propeller-equilibrium")
async def motor_propeller_equilibrium(x: Inputs, ctx: Context) -> dict[str, float]:
    """Solve the torque balance of the motor and the fitted propeller at the flight speed.

    Args:
        x: ``components``, ``v`` in m/s, ``rho`` in kg/m^3, ``k_v`` in rpm/V, ``i_0`` in A,
            ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and ``eta_mot`` are
            bound for route A and not read on route B.
        ctx: The formula context; it declares the route with a ``notice``.

    Returns:
        ``n_prop`` in 1/s and ``q_m`` in N m.

    Raises:
        TypeError: If ``components`` is not the components document.
        FormulaError: From :func:`equilibrium`, unchanged.
    """
    balance = equilibrium(
        ctx,
        components_of(x),
        number(x, "v"),
        number(x, "rho"),
        number(x, "k_v"),
        optional(x, "i_0"),
        optional(x, "r_m"),
        number(x, "u_bat"),
        number(x, "d_prop"),
    )
    declare_route(ctx)
    return {"n_prop": balance.n_prop, "q_m": balance.q_m}
