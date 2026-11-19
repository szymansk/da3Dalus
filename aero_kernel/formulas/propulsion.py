"""What the powertrain formulas share: unit constants, the motor circuit, the typed relation accessors.

The embedders never import a relation function to call it: they obtain it from the context
(``ctx.embedded``, ARCHITECTURE ch. 8.12) through the accessors below, which only give the item its
type. The result types of the relations live here so that the formulas need not import each other.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.values import air_state, airplane_of, number
from aero_kernel.solvers.opti import LevelFlightPoint

__all__ = [
    "RPM_PER_HZ",
    "Balance",
    "Coefficients",
    "GridPoint",
    "PartLoad",
    "advance_ratio_of",
    "balance_tolerance",
    "bisect_root",
    "current_at_speed",
    "current_for_torque",
    "equilibrium_of",
    "level_flight_at",
    "motor_torque",
    "optional",
    "part_load_of",
    "propeller_torque",
    "scan_grid",
    "table_lookup_of",
    "terminal_voltage",
    "thrust_of",
]

RPM_PER_HZ = 60.0  # rev/min per rev/s: a unit conversion
_ADVANCE_RATIO = "calc:advance-ratio-from-speed.default"
_TABLE_LOOKUP = "calc:propeller-table-lookup.default"
_THRUST = "calc:thrust-at-airspeed-from-coefficient.default"
_EQUILIBRIUM = "calc:motor-propeller-equilibrium.default"
_PART_LOAD = "calc:motor-propeller-part-load.default"


@dataclass(frozen=True)
class Coefficients:
    """The propeller coefficients at one point of the table.

    Attributes:
        c_t: Thrust coefficient (1).
        c_p: Power coefficient (1).
    """

    c_t: float
    c_p: float


@dataclass(frozen=True)
class Balance:
    """The solved balance point.

    Attributes:
        n_prop: Propeller speed in 1/s.
        q_m: Torque at the balance in N m (motor torque, equal to the propeller torque).
    """

    n_prop: float
    q_m: float


@dataclass(frozen=True)
class PartLoad:
    """The part-load point of level flight at one speed.

    Attributes:
        n_pl: Propeller speed in 1/s.
        i_bat: Battery current in A.
        p_bat: Battery power in W.
        r_t: Thrust demand ratio, the drag over the full-throttle thrust (1).
    """

    n_pl: float
    i_bat: float
    p_bat: float
    r_t: float


class PartLoadRelation(Protocol):
    """The signature of the ``motor-propeller-part-load`` relation: the drive train at a given drag."""

    def __call__(
        self,
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
        """Solve the part-load point at the airspeed ``v`` against the drag ``drag`` in N."""
        ...


class EquilibriumRelation(Protocol):
    """The signature of the ``motor-propeller-equilibrium`` relation."""

    def __call__(
        self,
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
        """Solve the balance at the airspeed ``v``."""
        ...


def advance_ratio_of(ctx: Context) -> Callable[[float, float, float], float]:
    """The embedded ``advance-ratio-from-speed`` relation: ``(v, n_prop, d_prop) -> J``."""
    return cast("Callable[[float, float, float], float]", ctx.embedded(_ADVANCE_RATIO))


def table_lookup_of(ctx: Context) -> Callable[[Components, float, float], Coefficients]:
    """The embedded ``propeller-table-lookup`` relation: ``(components, j, n_prop) -> coefficients``."""
    return cast("Callable[[Components, float, float], Coefficients]", ctx.embedded(_TABLE_LOOKUP))


def thrust_of(ctx: Context) -> Callable[[float, float, float, float], float]:
    """The embedded thrust relation: ``(c_t, rho, n_prop, d_prop) -> T``."""
    return cast(
        "Callable[[float, float, float, float], float]",
        ctx.embedded(_THRUST),
    )


def equilibrium_of(ctx: Context) -> EquilibriumRelation:
    """The embedded ``motor-propeller-equilibrium`` relation."""
    return cast("EquilibriumRelation", ctx.embedded(_EQUILIBRIUM))


def part_load_of(ctx: Context) -> PartLoadRelation:
    """The embedded ``motor-propeller-part-load`` relation."""
    return cast("PartLoadRelation", ctx.embedded(_PART_LOAD))


async def level_flight_at(x: Inputs, ctx: Context, v: float) -> LevelFlightPoint:
    """The level-flight point at the speed ``v``: the kernel's one lift-equals-weight solve.

    ``OptiAdapter.level_flight_point`` (the machinery of the level-flight polar: an alpha sweep plus
    secant steps bounded by the first lift peak, tolerance and step limit ``opt_level_*`` in
    ``config.yaml``). The caveats stay in the result: the caller forwards those of the answer only.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in m/s.
        ctx: The formula context that holds the solver adapters.
        v: The speed in m/s.

    Returns:
        The point (angle, drag, lift) and its caveats.

    Raises:
        FormulaError: ``not_converged`` from the adapter if the weight is not carried before the
            first lift peak at this speed.
    """
    return await ctx.solvers.opti.level_flight_point(
        airplane_of(x), number(x, "m"), number(x, "g"), air_state(x), v
    )


def balance_tolerance() -> float:
    """The relative interval width at which the balance searches stop (``config.yaml``)."""
    return config().powertrain_balance_tolerance.value


def optional(x: Inputs, name: str) -> float | None:
    """The value of an ``optional`` parameter, ``None`` if absent."""
    return None if x[name] is None else number(x, name)


def propeller_torque(c_p: float, rho: float, n_prop: float, d_prop: float) -> float:
    """``Q = C_P rho n^2 D^5 / (2 pi)`` in N m."""
    return c_p * rho * n_prop**2 * d_prop**5 / (2.0 * math.pi)


def _k_v_rad(k_v: float) -> float:
    """The speed constant ``K_v' = 2 pi K_v / 60`` in rad/(V s) of ``K_v`` in rpm/V."""
    return 2.0 * math.pi * k_v / RPM_PER_HZ


def current_at_speed(n_prop: float, k_v: float, u_bat: float, r_m: float) -> float:
    """The motor current in A at the speed: ``(U - 2 pi n / K_v') / R_m``."""
    return (u_bat - 2.0 * math.pi * n_prop / _k_v_rad(k_v)) / r_m


def motor_torque(current: float, i_0: float, k_v: float) -> float:
    """The motor shaft torque in N m at a current: ``Q_m = (I - I_0) / K_v'``."""
    return (current - i_0) / _k_v_rad(k_v)


def current_for_torque(q: float, i_0: float, k_v: float) -> float:
    """The motor current in A for a shaft torque: ``I = I_0 + Q K_v'`` (Drela ``motor1`` 1.1)."""
    return i_0 + q * _k_v_rad(k_v)


def terminal_voltage(current: float, r_m: float, n_prop: float, k_v: float) -> float:
    """The motor terminal voltage in V: ``I R_m + 2 pi n / K_v'``."""
    return current * r_m + 2.0 * math.pi * n_prop / _k_v_rad(k_v)


@dataclass(frozen=True)
class GridPoint:
    """The residual and the power coefficient at one grid speed; ``None`` where uncovered.

    Attributes:
        n: The grid speed in 1/s.
        residual: The residual of the balance there, or ``None`` if the table does not cover it.
        c_p: The power coefficient there, or ``None`` if the table does not cover it.
    """

    n: float
    residual: float | None
    c_p: float | None


def scan_grid(state: Callable[[float], tuple[float, float]], grid: list[float]) -> list[GridPoint]:
    """The (residual, ``C_P``) at the grid speeds; a point the table does not cover is kept as such."""
    found: list[GridPoint] = []
    for n in grid:
        try:
            residual, c_p = state(n)
        except FormulaError as error:
            if error.code != "outside_propeller_table":
                raise
            found.append(GridPoint(n, None, None))
        else:
            found.append(GridPoint(n, residual, c_p))
    return found


def bisect_root(
    residual: Callable[[float], float], low: float, high: float, tolerance: float
) -> float:
    """The root of a residual that is positive at ``low`` and not positive at ``high``.

    Stops when the interval is narrower than ``tolerance`` of ``high`` (the configured
    ``powertrain_balance_tolerance``).
    """
    while high - low > tolerance * high:
        middle = 0.5 * (low + high)
        if residual(middle) > 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)
