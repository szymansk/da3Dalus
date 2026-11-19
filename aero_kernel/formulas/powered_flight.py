"""What the six powered-performance formulas share (gh-1414): the thrust and drag at a flight state, and the searches.

The formulas ``max-level-speed``, ``dive-speed``, ``best-rate-of-climb``, ``best-angle-of-climb``,
``max-sustained-turn-rate`` and ``min-sustained-turn-radius`` pose the same question at different
flight states: at the speed ``V``, with the drive train at full throttle, what thrust is available and
what drag does the airplane have at the lift the state needs? This module holds the one answer to each:

- the thrust available, ``T(V)``: :func:`aero_kernel.formulas.propulsion.full_throttle_thrust`;
- the drag at the lift ``n m g``: ``OptiAdapter.level_flight_point`` with the load factor ``n`` (level
  flight ``1``, a turn ``n``, a climb ``cos(gamma)``, a vertical dive ``0``), the kernel's one
  lift-equals-weight solve over AeroBuildup, on the branch before the stall.

The entries pose their problems as optimisations over ``V``, ``alpha``, ``gamma`` / ``n`` and ``n_prop``.
The motor-propeller balance is a bisection on the propeller table and cannot enter an IPOPT problem, so
the kernel solves each problem by what it is: the variables ``alpha`` (lift equals ``n m g``) and
``n_prop`` (torque balance) are eliminated by the two existing solves, and what is left is a one-dimensional
root or maximum over ``V`` (and a root over ``gamma`` or a bound over ``n`` inside it). The searches are the
upward scan of the airspeed, Illinois regula falsi for roots and golden section for a maximum; their
numerical settings are in ``config.yaml`` (``powered_*``).

What the searches assume (stated in the canon entries, #1414): one maximum of the objective over the speed
(golden section), one hump of ``T - D`` over the speed for the level speed, and features no narrower than the
scan step (two features closer together than the step can be missed).

A speed at which a state cannot be evaluated is never dropped silently. The result of an evaluation is a
value or an :class:`Unflyable`: ``WING`` (the wing cannot carry the lift before its first lift peak),
``THRUST`` (the thrust is below the drag) or ``TABLE`` (the propeller table ends). Speeds skipped below the
first feasible speed are declared with the notice ``powered_speeds_skipped``; the table edge is a bound of
the search (an interior optimum is returned, an optimum on the bound is the declared failure
``outside_propeller_table``). Any other failure of an evaluation (a sweep without a lift peak, a zero-lift
angle outside the sweep) surfaces as ``not_converged``: it is not a stall.

Warnings of the evaluations along the search are not forwarded; the answer is evaluated once more and its
warnings (flap, regime, the drag notice) are the formula's. Where the optimum lies on a limit the entry
names, the formula declares it with the notice ``powered_limit_declared``.
"""

import math
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from enum import StrEnum

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import declare_route
from aero_kernel.formulas.propeller_table_lookup import components_of
from aero_kernel.formulas.propulsion import full_throttle_thrust, optional
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.solvers.opti import WING_LIFT_LIMIT, LevelPoint
from pydantic import JsonValue

__all__ = [
    "LEVEL_FLIGHT",
    "RIGHT_ANGLE",
    "TABLE_FAILURE",
    "VERTICAL_FLIGHT",
    "GoldenResult",
    "Optimum",
    "PoweredFlight",
    "TurnLimit",
    "Unflyable",
    "climb_angle",
    "declare_limit",
    "finish_climb",
    "golden_maximum",
    "illinois_root",
    "maximise_over_speed",
    "no_feasible_speed",
    "scan_speeds",
    "sustained_load_factor",
    "sustained_turn",
    "vertical_upper_edge",
]

LEVEL_FLIGHT = 1.0  # the load factor of level flight: L = W (definition of n = L / W)
VERTICAL_FLIGHT = 0.0  # the load factor of a flight path without lift: L = 0
RIGHT_ANGLE = 0.5 * math.pi  # the bound gamma <= pi/2 of the climb problems (rad)
TABLE_FAILURE = "outside_propeller_table"  # the error code of the end of the propeller table


class Unflyable(StrEnum):
    """Why a state has no value at a speed (a bound of the search, not a defect).

    Attributes:
        WING: the wing cannot carry the lift of the state before its first lift peak.
        THRUST: the thrust at full throttle is below what the state needs.
        TABLE: the propeller table ends before this speed.
    """

    WING = "wing"
    THRUST = "thrust"
    TABLE = "table"


Objective = Callable[[float], Awaitable[float | Unflyable]]

_SKIP_TEXT = {
    Unflyable.WING: "the wing cannot carry the lift of the state before its first lift peak",
    Unflyable.THRUST: "the thrust at full throttle is below what the state needs",
    Unflyable.TABLE: "the propeller table ends",
}


def no_feasible_speed(what: str) -> FormulaError:
    """The declared failure of a state the airplane cannot fly at any speed at full throttle."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "no_feasible_speed",
        what,
        "see the reason in the message: a stronger drive train helps where the thrust is short, a lighter "
        "airplane or a larger wing where the wing cannot carry the lift",
    )


def never_flyable(reasons: set[Unflyable]) -> FormulaError:
    """``no_feasible_speed`` naming what stopped the state at every speed of the scan."""
    start = config().powered_speed_scan_start.value
    limit = config().powered_speed_scan_limit.value
    why = " and ".join(sorted(_SKIP_TEXT[r] for r in reasons)) or "no speed was evaluated"
    return no_feasible_speed(
        f"the state has no value at any speed of the scan ({start:g} to {limit:g} m/s): {why}"
    )


def _not_converged(message: str, hint: str, **detail: JsonValue) -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", message, hint, detail=dict(detail)
    )


class PoweredFlight:
    """The thrust and the drag of one airplane with one drive train, at any flight state.

    Built from the inputs of a powered-performance formula (the airplane, mass, gravity, air and the
    drive-train values of its canon entry). Evaluations along a search return values; ``answer`` is the
    one evaluation whose warnings the formula forwards, and the place where the speeds skipped by the
    search are declared.

    Attributes:
        lowest_level_speed: The lowest evaluated speed at which level flight was possible, in m/s
            (``None`` until a level point was evaluated): an upper bound of the level-flight stall speed.
    """

    def __init__(self, x: Inputs, ctx: Context) -> None:
        """Read the inputs once.

        Raises:
            TypeError: If ``airplane`` or ``components`` is not the document.
        """
        self.x, self.ctx = x, ctx
        self.components: Components = components_of(x)
        self.weight = number(x, "m") * number(x, "g")
        self.lowest_level_speed: float | None = None
        self._thrust: dict[float, float] = {}
        self._skipped: list[tuple[float, Unflyable]] = []

    def thrust(self, v: float) -> float:
        """The thrust in N at full throttle at the airspeed ``v`` (``motor-propeller-equilibrium``); kept per speed.

        Raises:
            FormulaError: The failures of the drive-train relations (``missing_input``,
                ``outside_propeller_table``, ``propeller_windmilling``), unchanged.
        """
        if v not in self._thrust:
            x = self.x
            self._thrust[v] = full_throttle_thrust(
                self.ctx,
                self.components,
                v,
                number(x, "rho"),
                number(x, "k_v"),
                optional(x, "i_0"),
                optional(x, "r_m"),
                number(x, "u_bat"),
                number(x, "d_prop"),
            )
        return self._thrust[v]

    async def drag(self, v: float, n_load: float) -> float | None:
        """The drag in N at speed ``v`` and lift ``n m g``; ``None`` where the wing cannot carry that lift.

        ``None`` is the answer of an airplane whose lift curve does not reach the lift before its first
        peak (``limit`` = ``wing_lift`` of the adapter's failure): the wing limit, a bound of the problem.
        Every other failure of the adapter (a sweep without a peak, a zero-lift angle outside the sweep,
        a secant that does not settle) is raised: it is not a stall.

        Raises:
            FormulaError: The adapter's failures other than the wing limit (``not_converged``).
        """
        try:
            found = await self.ctx.solvers.opti.level_flight_point(
                airplane_of(self.x),
                number(self.x, "m"),
                number(self.x, "g"),
                air_state(self.x),
                v,
                n_load,
            )
        except FormulaError as error:
            if error.detail.get("limit") == WING_LIFT_LIMIT:
                return None
            raise
        if n_load == LEVEL_FLIGHT and (
            self.lowest_level_speed is None or v < self.lowest_level_speed
        ):
            self.lowest_level_speed = v
        return found.point.drag_n

    async def required_drag(self, v: float, n_load: float) -> float:
        """The drag at a state that must be flyable (inside a bracket); the wing limit is a failure here.

        Raises:
            FormulaError: ``not_converged`` if the wing cannot carry the lift.
        """
        value = await self.drag(v, n_load)
        if value is None:
            raise _not_converged(
                f"the wing cannot carry the lift n = {n_load:.4g} at {v:.4g} m/s inside a bracketed search",
                "the lift curve changed its branch between two points of the search; report the case",
                v_ms=v,
                n_load=n_load,
            )
        return value

    def note_skipped(self, v: float, reason: Unflyable) -> None:
        """Remember a speed the search passed over, to declare it with the answer."""
        self._skipped.append((v, reason))

    async def answer(self, v: float, n_load: float) -> LevelPoint:
        """Evaluate the answer state once more, forward its warnings, declare the route and the skipped speeds.

        Returns:
            The level-flight point of the answer (angle of attack, ``C_L``, ``C_D``, forces).
        """
        found = await self.ctx.solvers.opti.level_flight_point(
            airplane_of(self.x),
            number(self.x, "m"),
            number(self.x, "g"),
            air_state(self.x),
            v,
            n_load,
        )
        forward_warnings(self.ctx, found.warnings)
        declare_route(self.ctx)
        self._declare_skipped()
        return found.point

    def _declare_skipped(self) -> None:
        """One notice for the speeds the search skipped: the count, the range and the reasons (ADR 0020)."""
        if not self._skipped:
            return
        speeds = [v for v, _ in self._skipped]
        reasons = sorted({reason for _, reason in self._skipped})
        self.ctx.warn(
            "powered_speeds_skipped",
            f"{len(speeds)} speeds from {min(speeds):.4g} to {max(speeds):.4g} m/s were skipped by the "
            f"upward scan, below the first speed with a value: "
            + "; ".join(_SKIP_TEXT[r] for r in reasons)
            + ".",
            {
                "count": len(speeds),
                "v_min_ms": min(speeds),
                "v_max_ms": max(speeds),
                "reasons": [str(r) for r in reasons],
            },
        )


def scan_speeds() -> Iterator[float]:
    """The speeds of the upward scan: start, start + step, ... up to the limit (``config.yaml``)."""
    settings = config()
    start = settings.powered_speed_scan_start.value
    step = settings.powered_speed_scan_step.value
    limit = settings.powered_speed_scan_limit.value
    k = 0
    while start + k * step <= limit:
        yield start + k * step
        k += 1


async def illinois_root(
    f: Callable[[float], Awaitable[float]],
    low: tuple[float, float],
    high: tuple[float, float],
    scale: float,
) -> float:
    """The root of ``f`` between two points of opposite sign (Illinois regula falsi).

    Args:
        f: The function.
        low: ``(x, f(x))`` of one end of the bracket.
        high: ``(x, f(x))`` of the other end; the signs of the two values differ (or one is zero).
        scale: The residual is accepted at ``powered_root_tolerance * scale`` (the weight in N).

    Raises:
        FormulaError: ``not_converged`` if the residual is not within tolerance after
            ``powered_search_max_steps`` steps.
    """
    tolerance = config().powered_root_tolerance.value * scale
    (x_low, f_low), (x_high, f_high) = low, high
    if abs(f_low) <= tolerance:
        return x_low
    if abs(f_high) <= tolerance:
        return x_high
    side = 0
    steps = int(config().powered_search_max_steps.value)
    for _ in range(steps):
        x_new = (x_low * f_high - x_high * f_low) / (f_high - f_low)
        f_new = await f(x_new)
        if abs(f_new) <= tolerance:
            return x_new
        if (f_new > 0.0) == (f_high > 0.0):
            x_high, f_high = x_new, f_new
            f_low = f_low / 2.0 if side == 1 else f_low
            side = 1
        else:
            x_low, f_low = x_new, f_new
            f_high = f_high / 2.0 if side == -1 else f_high
            side = -1
    raise _not_converged(
        f"the root search did not reach a residual of {tolerance:.3g} N within {steps} steps",
        "report the case; the force balance is not smooth in the searched variable",
        x_low=x_low,
        x_high=x_high,
    )


_GOLDEN = 0.5 * (math.sqrt(5.0) - 1.0)  # the golden-section ratio, 0.618...


@dataclass(frozen=True)
class GoldenResult:
    """The maximum found by the golden section and what bounds its final bracket from above.

    Attributes:
        v: The argument of the best evaluated point.
        value: The objective there.
        above: What the evaluated point that set the upper edge of the final bracket returned, if it
            was not a value (a ``TABLE`` there: the maximum lies against the end of the propeller
            table); ``None`` if it was a value or the edge is the end of the starting interval.
    """

    v: float
    value: float
    above: Unflyable | None


async def golden_maximum(f: Objective, low: float, high: float) -> GoldenResult:
    """The maximum of ``f`` inside ``[low, high]`` (golden section), with what bounds the final bracket.

    ``f`` returns an :class:`Unflyable` where it has no value; that ranks below every value, so the search
    leaves it behind. The maximum is assumed to be the only one inside the interval. The result is the best
    point the search evaluated (always a value). The final bracket is narrower than
    ``powered_optimum_tolerance`` of the scan step; if its upper edge was set by an evaluation without a
    value (``TABLE``), the maximum lies against the end of the propeller table.

    Raises:
        FormulaError: ``not_converged`` if the interval does not narrow within ``powered_search_max_steps``
            steps, or ``f`` has no value at every point the search evaluated.
    """
    step = config().powered_speed_scan_step.value
    tolerance = config().powered_optimum_tolerance.value * step
    steps = int(config().powered_search_max_steps.value)
    best: list[tuple[float, float]] = []
    high_kind: Unflyable | None = None

    async def value(v: float) -> tuple[float, Unflyable | None]:
        found = await f(v)
        if isinstance(found, Unflyable):
            return -math.inf, found
        best.append((v, found))
        return found, None

    x_a, x_b = high - _GOLDEN * (high - low), low + _GOLDEN * (high - low)
    (f_a, kind_a), (f_b, kind_b) = await value(x_a), await value(x_b)
    for _ in range(steps):
        if high - low <= tolerance:
            if not best:
                break
            v_best, top = max(best, key=lambda point: point[1])
            return GoldenResult(v_best, top, high_kind)
        if f_a >= f_b:
            high, x_b, f_b, kind_b, high_kind = x_b, x_a, f_a, kind_a, kind_b
            x_a = high - _GOLDEN * (high - low)
            f_a, kind_a = await value(x_a)
        else:
            low, x_a, f_a, kind_a = x_a, x_b, f_b, kind_b
            x_b = low + _GOLDEN * (high - low)
            f_b, kind_b = await value(x_b)
    raise _not_converged(
        f"the search for the optimum did not narrow below {tolerance:.3g} m/s in {steps} steps, "
        "or found no point with a value",
        "report the case; the objective is not unimodal over the speed",
        low=low,
        high=high,
    )


@dataclass(frozen=True)
class Optimum:
    """The maximum of an objective over the airspeed.

    Attributes:
        v: The speed in m/s.
        value: The objective there.
        on_wing_limit: Whether the scan point one step below the best scan point is one where the wing
            cannot carry the lift: the optimum lies within the resolution of the search (one scan step)
            of the stall corner of the state.
    """

    v: float
    value: float
    on_wing_limit: bool


def table_failure(speed: float, what: str) -> FormulaError:
    """The declared failure of a search whose answer lies at or beyond the end of the propeller table."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        TABLE_FAILURE,
        f"{what}: the propeller table ends before {speed:.4g} m/s, so the full-throttle thrust is not "
        "available there (no extrapolation).",
        "Use a propeller whose table covers the speeds of this flight; the kernel does not extrapolate.",
        detail={"v_ms": speed},
    )


async def maximise_over_speed(f: Objective, flight: PoweredFlight) -> Optimum:
    """The maximum of ``f`` over the airspeed: upward scan, then golden section around the best point.

    The upward scan skips the speeds without a value before its first value (declared with the answer) and
    ends at the first speed without one after it, so the feasible speeds are taken as one interval. The
    maximum is refined between the neighbours of the best scan point. The end of the propeller table is a
    bound of the scan: an optimum bracketed below it is returned; one that sits on it (the nearest
    evaluated point above is beyond the table) is the declared failure ``outside_propeller_table``. A
    ``WING`` scan point just below the best scan point puts the optimum at the stall corner to the
    resolution of the scan (:attr:`Optimum.on_wing_limit`).

    Raises:
        FormulaError: ``no_feasible_speed`` if no scan speed has a value; ``outside_propeller_table``
            for an optimum on the table edge; ``not_converged`` from the search.
    """
    speeds: list[float] = []
    values: list[float] = []
    below: dict[float, Unflyable | None] = {}  # the kind of the scan point below each valued one
    previous_kind: Unflyable | None = None
    reasons: set[Unflyable] = set()
    table_edge: float | None = None
    guarded = _table_as_result(f)
    for v in scan_speeds():
        found = await guarded(v)
        if isinstance(found, Unflyable):
            reasons.add(found)
            if values:
                table_edge = v if found is Unflyable.TABLE else None
                break
            if found is not Unflyable.TABLE:
                flight.note_skipped(v, found)
                previous_kind = found
                continue
            break
        speeds.append(v)
        values.append(found)
        below[v] = previous_kind
        previous_kind = None
    if not values:
        raise never_flyable(reasons)
    best = max(range(len(values)), key=values.__getitem__)
    step = config().powered_speed_scan_step.value
    low = max(speeds[best] - step, config().powered_speed_scan_start.value)
    result = await golden_maximum(guarded, low, speeds[best] + step)
    if result.above is Unflyable.TABLE:
        raise table_failure(
            table_edge if table_edge is not None else result.v,
            f"the optimum lies on the end of the table (best value at {result.v:.4g} m/s)",
        )
    return Optimum(result.v, result.value, below[speeds[best]] is Unflyable.WING)


def _table_as_result(f: Objective) -> Objective:
    """``f`` with the end of the propeller table (``outside_propeller_table``) as the result ``TABLE``."""

    async def guarded(v: float) -> float | Unflyable:
        try:
            return await f(v)
        except FormulaError as error:
            if error.code == TABLE_FAILURE:
                return Unflyable.TABLE
            raise

    return guarded


async def climb_angle(flight: PoweredFlight, v: float) -> float | Unflyable:
    """The steepest steady climb angle in rad at the speed ``v``, at full throttle, or why there is none.

    The force balances of the exact steady climb: along the path ``T - D(V, cos gamma) = m g sin gamma``
    and across it ``L = m g cos gamma``, so the drag is the one at the load factor ``cos gamma`` and the
    wing must be able to carry that lift. The excess ``F(gamma) = T - D - m g sin gamma`` falls with
    ``gamma``; the climb angle is its root, ``pi/2`` (vertical, the declared bound of the entry) where
    ``F`` is not negative there. Below the stall of level flight only the angles steep enough for the wing
    to carry ``m g cos gamma`` exist, so the bracket is found by bisection that treats "the wing cannot
    carry it" as "too shallow", and is then refined by Illinois regula falsi. ``THRUST`` where level flight
    is held but the thrust is below its drag; ``WING`` where no angle the thrust holds is one the wing can
    carry.

    The search assumes ``F`` has one root on the angles the wing can carry (the lift of a steeper climb is
    smaller, so the induced drag is too, and the weight component grows).

    Raises:
        FormulaError: As :meth:`PoweredFlight.thrust` and :meth:`PoweredFlight.required_drag`; a failure
            of the adapter that is not the wing limit (also at the zero-lift point) is raised, not skipped.
    """
    thrust, weight = flight.thrust(v), flight.weight

    async def excess(gamma: float) -> float | None:
        n_load = VERTICAL_FLIGHT if gamma >= RIGHT_ANGLE else math.cos(gamma)
        drag = await flight.drag(v, n_load)
        return None if drag is None else thrust - drag - weight * math.sin(gamma)

    async def required(gamma: float) -> float:
        found = await excess(gamma)
        if found is None:
            raise _not_converged(
                f"the wing cannot carry the lift of the climb angle {math.degrees(gamma):.4g} deg at "
                f"{v:.4g} m/s inside a bracketed search",
                "the lift curve changed its branch between two points of the search; report the case",
                v_ms=v,
            )
        return found

    f_top = await required(RIGHT_ANGLE)
    if f_top >= 0.0:
        return RIGHT_ANGLE
    f_level = await excess(0.0)
    if f_level is not None and f_level < 0.0:
        return Unflyable.THRUST
    low = (0.0, f_level) if f_level is not None else None
    shallow, steep = 0.0, RIGHT_ANGLE
    tolerance = config().powered_load_factor_tolerance.value
    while low is None and steep - shallow > tolerance * steep:
        middle = 0.5 * (shallow + steep)
        found = await excess(middle)
        if found is None:
            shallow = middle
        elif found >= 0.0:
            low = (middle, found)
        else:
            steep = middle
    if low is None:
        return Unflyable.WING
    return await illinois_root(required, low, (RIGHT_ANGLE, f_top), weight)


@dataclass(frozen=True)
class TurnLimit:
    """The highest load factor of a sustained level turn at one speed and what stops it.

    Attributes:
        n: The load factor (1).
        limit: ``thrust`` (``T = D``), ``wing`` (the lift before the stall) or ``structure``
            (``n = n_lim``).
    """

    n: float
    limit: str


async def sustained_load_factor(
    flight: PoweredFlight, v: float, n_lim: float
) -> TurnLimit | Unflyable:
    """The highest load factor ``n`` in ``[1, n_lim]`` that the airplane holds in a level turn at ``v``.

    A sustained turn is level at constant speed: ``L = n m g`` and ``T >= D(V, n)``, with the drag at
    the load factor ``n`` and the wing on the branch before the stall. Feasibility falls with ``n``
    (more lift: more induced drag, and the stall), so the highest feasible ``n`` is found by bisection
    on ``[1, n_lim]`` to ``powered_load_factor_tolerance`` (much tighter than the speed search, so the
    objective is not a staircase at the resolution of the speed); the answer is the feasible end. The
    result is ``WING`` or ``THRUST`` where level flight itself is not held.

    Raises:
        FormulaError: As :meth:`PoweredFlight.thrust` and :meth:`PoweredFlight.drag`.
    """

    async def verdict(n: float) -> Unflyable | None:
        """``None`` if the turn at ``n`` is held, else the limit that stops it."""
        drag = await flight.drag(v, n)
        if drag is None:
            return Unflyable.WING
        return None if flight.thrust(v) >= drag else Unflyable.THRUST

    level = await verdict(LEVEL_FLIGHT)
    if level is not None:
        return level
    stop = await verdict(n_lim)
    if stop is None:
        return TurnLimit(n_lim, "structure")
    low, high = LEVEL_FLIGHT, n_lim
    tolerance = config().powered_load_factor_tolerance.value
    while high - low > tolerance * high:
        middle = 0.5 * (low + high)
        found = await verdict(middle)
        if found is None:
            low = middle
        else:
            high, stop = middle, found
    return TurnLimit(low, str(stop))


def declare_limit(ctx: Context, limit: str, what: str, detail: dict[str, JsonValue]) -> None:
    """Declare the limit an optimum lies on (the entry's "declared active bound", ADR 0020)."""
    ctx.warn("powered_limit_declared", what, {"limit": limit, **detail})


async def vertical_upper_edge(flight: PoweredFlight, v: float) -> float:
    """The highest speed at which the climb is still vertical, searched upward from a vertical speed ``v``.

    The climb is vertical where ``T - D(V, alpha_0) - m g >= 0`` (the thrust carries the weight and the
    zero-lift drag). The edge is the root of that excess: the upward scan brackets it from ``v``,
    Illinois regula falsi refines it.

    Raises:
        FormulaError: ``not_converged`` if the climb is still vertical at the scan limit; the failures
            of :meth:`PoweredFlight.thrust` (the end of the propeller table before the edge is
            ``outside_propeller_table``).
    """

    async def excess(speed: float) -> float:
        drag = await flight.required_drag(speed, VERTICAL_FLIGHT)
        return flight.thrust(speed) - drag - flight.weight

    low = (v, await excess(v))
    step, limit = config().powered_speed_scan_step.value, config().powered_speed_scan_limit.value
    speed = v + step
    while speed <= limit:
        value = await excess(speed)
        if value < 0.0:
            return await illinois_root(excess, low, (speed, value), flight.weight)
        low = (speed, value)
        speed += step
    raise _not_converged(
        f"the climb is still vertical at the scan limit of {limit:g} m/s",
        "report the case; the scan limit ends the search",
        v_ms=low[0],
    )


async def finish_climb(flight: PoweredFlight, optimum: Optimum, gamma: float) -> None:
    """Evaluate the answer of a climb at ``(optimum.v, gamma)`` and declare the bound it lies on.

    The state of the answer is the load factor ``cos(gamma)``, ``0`` for the vertical climb. The vertical
    climb (the entry's one declared exception) and the stall corner (the wing cannot carry the lift of a
    slower speed) are declared with the notice ``powered_limit_declared``; the corner notice carries the
    numbers needed to read a climb speed below the level stall speed.
    """
    v, vertical = optimum.v, gamma >= RIGHT_ANGLE
    point = await flight.answer(v, VERTICAL_FLIGHT if vertical else math.cos(gamma))
    if vertical:
        declare_limit(
            flight.ctx,
            "gamma_90_deg",
            "The climb is vertical at this speed: the flight-path angle is at its bound of 90 deg "
            "(canon: the declared exception of 'no bound active at the optimum'). The airplane "
            "climbs vertically over a range of speeds, so the speed reported is not a single "
            "optimum of the range.",
            {"v_ms": v},
        )
    elif optimum.on_wing_limit:
        detail: dict[str, JsonValue] = {
            "v_ms": v,
            "cl": point.cl,
            "gamma_deg": math.degrees(gamma),
            "cos_gamma": math.cos(gamma),
        }
        level = flight.lowest_level_speed
        if level is not None:
            detail["lowest_evaluated_level_flight_speed_ms"] = level
        declare_limit(
            flight.ctx,
            "wing",
            f"The optimum lies on the stall corner: at {v:.4g} m/s on a climb of "
            f"{math.degrees(gamma):.4g} deg the wing carries the lift m g cos(gamma) = "
            f"{math.cos(gamma):.3g} m g at C_L = {point.cl:.3g}, and a slower speed would need more lift "
            "than the wing gives. The climb is limited by the wing at this speed, not by the thrust; the "
            "speed may lie below the level-flight stall speed because a steep path needs less lift"
            + (
                f" (level flight was possible down to {level:.4g} m/s among the evaluated speeds)."
                if level
                else "."
            ),
            detail,
        )


async def sustained_turn(
    flight: PoweredFlight, n_lim: float, objective: Callable[[float, float], float]
) -> tuple[float, TurnLimit]:
    """The speed of the best sustained level turn by ``objective(v, n)`` (larger is better), and its limit.

    For every speed the highest sustained load factor (:func:`sustained_load_factor`), then the maximum
    of ``objective`` over the speed (:func:`maximise_over_speed`). The answer is evaluated once more
    at its speed and load factor, and the limit that stops the turn there is declared: ``thrust``,
    ``wing`` or ``structure`` (the entry's termination clause, ADR 0020).

    Raises:
        FormulaError: As :func:`maximise_over_speed`.
    """

    async def at_speed(v: float) -> float | Unflyable:
        found = await sustained_load_factor(flight, v, n_lim)
        if isinstance(found, Unflyable):
            return found
        if found.n <= LEVEL_FLIGHT:
            return Unflyable.THRUST
        return objective(v, found.n)

    v = (await maximise_over_speed(at_speed, flight)).v
    limit = await sustained_load_factor(flight, v, n_lim)
    if isinstance(
        limit, Unflyable
    ):  # pragma: no cover - the maximum is evaluated at a speed that held a turn
        raise _not_converged("the optimum turn is not flyable", "report the case", v_ms=v)
    await flight.answer(v, limit.n)
    declare_limit(
        flight.ctx,
        limit.limit,
        _LIMIT_TEXT[limit.limit].format(v=v, n=limit.n),
        {"v_ms": v, "n": limit.n},
    )
    return v, limit


_LIMIT_TEXT = {
    "thrust": "The thrust limits the turn: at {v:.4g} m/s the full-throttle thrust equals the drag at "
    "the load factor {n:.4g}. At the corner where the thrust limit and the wing limit meet, which is "
    "where the optimum usually lies, the label names the one the search met first; both bind there.",
    "wing": "The wing limits the turn: at {v:.4g} m/s the optimum sits at the lift maximum of the polar "
    "(load factor {n:.4g}); the airplane holds the turn only at the edge of the stall. At the corner "
    "where the thrust limit and the wing limit meet, which is where the optimum usually lies, the "
    "label names the one the search met first; both bind there.",
    "structure": "The structure limits the turn: the load factor is at the given limit load factor "
    "{n:.4g} at {v:.4g} m/s, so the user's limit, not the aerodynamics, ends the turn.",
}
