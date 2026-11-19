"""Canon formula ``motor-propeller-equilibrium``: the propeller speed where motor and propeller torque meet.

Route B only (the manufacturer publishes ``R_m`` and ``I_0``): Drela's three-parameter DC motor
(``motor1`` 1.1) against the ``C_P(J)`` table of the fitted propeller. Route A (``R_m`` absent) and the
default ``I_0 = 0`` are not built (gh-1411, complete data only): an absent value is a declared failure.

With ``K_v' = 2 pi K_v / 60`` (rad/(V s)) and the speed ``n`` in 1/s the balance is

    motor:      I(n) = (U_bat - 2 pi n / K_v') / R_m,   Q_m(n) = (I(n) - I_0) / K_v'
    propeller:  Q_p(n) = C_P(J, n) rho n^2 D^5 / (2 pi),   J = V / (n D)
    balance:    Q_m(n) = Q_p(n)

``Q_m`` falls and ``Q_p`` rises with ``n`` over the usual range, so the root is found by bisection
on the interval between two neighbouring rpm blocks where the sign of ``Q_m - Q_p`` changes.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import pairwise

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.advance_ratio_from_speed import advance_ratio
from aero_kernel.formulas.propeller_table_lookup import components_of, table_lookup, table_of
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula, relation
from pydantic import JsonValue

__all__ = [
    "Balance",
    "declare_route",
    "equilibrium",
    "motor_propeller_equilibrium",
    "require_motor_values",
]

_RPM_PER_HZ = 60.0


@dataclass(frozen=True)
class Balance:
    """The solved balance point.

    Attributes:
        n_prop: Propeller speed in 1/s.
        q_m: Torque at the balance in N m (motor torque, equal to the propeller torque).
    """

    n_prop: float
    q_m: float


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


def _propeller_torque(
    components: Components, v: float, rho: float, d_prop: float, n_prop: float
) -> float:
    """``Q_p = C_P(J, n) rho n^2 D^5 / (2 pi)`` in N m."""
    j = advance_ratio(v, n_prop, d_prop)
    c_p = table_lookup(components, j, n_prop).c_p
    return c_p * rho * n_prop**2 * d_prop**5 / (2.0 * math.pi)


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


def _no_balance(detail: dict[str, JsonValue], why: str) -> FormulaError:
    """The declared failure of a balance the table does not contain."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "outside_propeller_table",
        f"motor-propeller-equilibrium found no balance inside the propeller table: {why}.",
        "Use a propeller whose table covers the speed this motor turns it at; the kernel does not "
        "extrapolate.",
        detail=detail,
    )


@relation("motor-propeller-equilibrium")
def equilibrium(
    components: Components,
    v: float,
    rho: float,
    k_v: float,
    i_0: float | None,
    r_m: float | None,
    u_bat: float,
    d_prop: float,
    tolerance: float,
) -> Balance:
    """The balance of the motor and the propeller at the airspeed (route B).

    The relation embedded by the propulsion embedders and called by the formula below (ADR 0022).

    Args:
        components: The pushed components (the propeller table).
        v: Flight speed in m/s (zero for the static point).
        rho: Air density in kg/m^3.
        k_v: Motor voltage constant in rpm/V.
        i_0: No-load current in A.
        r_m: Winding resistance in ohm.
        u_bat: Pack voltage in V (nominal; sag under load is not modelled).
        d_prop: Propeller diameter in m.
        tolerance: Relative width of the speed interval at which the bisection stops (1).

    Returns:
        The propeller speed and the torque at the balance.

    Raises:
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``outside_propeller_table``
            if the table contains no balance or a point the search needs.
    """
    i_0, r_m = require_motor_values(i_0, r_m)
    k_v_rad = 2.0 * math.pi * k_v / _RPM_PER_HZ

    def residual(n: float) -> float:
        current = (u_bat - 2.0 * math.pi * n / k_v_rad) / r_m
        return (current - i_0) / k_v_rad - _propeller_torque(components, v, rho, d_prop, n)

    blocks = table_of(components).blocks
    free_run = k_v * u_bat / _RPM_PER_HZ
    n_top = min(blocks[-1].rpm / _RPM_PER_HZ, free_run)
    grid = [b.rpm / _RPM_PER_HZ for b in blocks if b.rpm / _RPM_PER_HZ < n_top] + [n_top]
    seen = _scan(residual, grid)
    for (n_low, f_low), (n_high, f_high) in reversed(list(pairwise(seen))):
        if f_low is None or f_high is None or not f_low > 0.0 >= f_high:
            continue
        low, high = n_low, n_high
        while high - low > tolerance * high:
            middle = 0.5 * (low + high)
            if residual(middle) > 0.0:
                low = middle
            else:
                high = middle
        n_balance = 0.5 * (low + high)
        return Balance(n_balance, _propeller_torque(components, v, rho, d_prop, n_balance))
    raise _no_balance(
        {
            "rpm_table_min": blocks[0].rpm,
            "rpm_table_max": blocks[-1].rpm,
            "rpm_free_run": free_run * _RPM_PER_HZ,
        },
        f"between {blocks[0].rpm:g} rpm and {n_top * _RPM_PER_HZ:g} rpm (the smaller of the table's "
        f"last block and the motor's free-run speed) the motor torque never crosses the propeller "
        "torque at a point the table covers",
    )


def _scan(
    residual: Callable[[float], float], grid: list[float]
) -> list[tuple[float, float | None]]:
    """The residual at the grid points; ``None`` where the table does not cover the point."""
    found: list[tuple[float, float | None]] = []
    for n in grid:
        try:
            found.append((n, residual(n)))
        except FormulaError as error:
            if error.code != "outside_propeller_table":
                raise
            found.append((n, None))
    return found


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
        components_of(x),
        number(x, "v"),
        number(x, "rho"),
        number(x, "k_v"),
        _optional(x, "i_0"),
        _optional(x, "r_m"),
        number(x, "u_bat"),
        number(x, "d_prop"),
        config().powertrain_balance_tolerance.value,
    )
    declare_route(ctx)
    return {"n_prop": balance.n_prop, "q_m": balance.q_m}


def _optional(x: Inputs, name: str) -> float | None:
    """The value of an ``optional`` parameter, ``None`` if absent."""
    value = x[name]
    if value is None:
        return None
    return number(x, name)
