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

Warnings of the evaluations along the search are not forwarded; the answer is evaluated once more and its
warnings (flap, regime, the drag notice) are the formula's. Where the optimum lies on a limit the entry
names, the formula declares it with the notice ``powered_limit_declared``.
"""

import math
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass

from aero_kernel.components import Components
from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import declare_route
from aero_kernel.formulas.propeller_table_lookup import components_of
from aero_kernel.formulas.propulsion import full_throttle_thrust, optional
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.solvers.opti import WING_LIFT_LIMIT
from pydantic import JsonValue

__all__ = [
    "LEVEL_FLIGHT",
    "RIGHT_ANGLE",
    "VERTICAL_FLIGHT",
    "Optimum",
    "PoweredFlight",
    "TurnLimit",
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

Objective = Callable[[float], Awaitable[float | None]]


def no_feasible_speed(what: str) -> FormulaError:
    """The declared failure of a state the airplane cannot fly at any speed at full throttle."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "no_feasible_speed",
        what,
        "the thrust is below the drag everywhere, the wing cannot carry the lift, or the load factor "
        "limit leaves no turn; use a stronger drive train or give a higher limit load factor",
    )


def _not_converged(message: str, hint: str, **detail: JsonValue) -> FormulaError:
    return FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", message, hint, detail=dict(detail)
    )


class PoweredFlight:
    """The thrust and the drag of one airplane with one drive train, at any flight state.

    Built from the inputs of a powered-performance formula (the airplane, mass, gravity, air and the
    drive-train values of its canon entry). Evaluations along a search return values; ``answer`` is the
    one evaluation whose warnings the formula forwards.
    """

    def __init__(self, x: Inputs, ctx: Context) -> None:
        """Read the inputs once.

        Raises:
            TypeError: If ``airplane`` or ``components`` is not the document.
        """
        self.x, self.ctx = x, ctx
        self.components: Components = components_of(x)
        self.weight = number(x, "m") * number(x, "g")
        self._thrust: dict[float, float] = {}

    def thrust(self, v: float) -> float:
        """The thrust in N at full throttle at the airspeed ``v`` (``motor-propeller-equilibrium``).

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
        peak (the speed is below the stall for this load factor): the wing limit, a bound of the
        problem and not an error.

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

    async def answer(self, v: float, n_load: float) -> None:
        """Evaluate the answer state once more and forward its warnings; declare the drive-train route."""
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


async def golden_maximum(f: Objective, low: float, high: float) -> tuple[float, float]:
    """The argument and the value of the maximum of ``f`` inside ``[low, high]`` (golden section).

    ``f`` returns ``None`` where it is not defined (not flyable); ``None`` ranks below every value,
    so the search leaves it behind. The maximum is assumed to be the only one inside the interval. The
    result is the best point the search evaluated, so it is always a point where ``f`` is defined, also
    where the maximum lies on the edge of the defined region.

    Raises:
        FormulaError: ``not_converged`` if the interval is not narrower than
            ``powered_optimum_tolerance`` of its upper end within ``powered_search_max_steps`` steps, or
            ``f`` is undefined at every point the search evaluated.
    """
    tolerance = config().powered_optimum_tolerance.value
    steps = int(config().powered_search_max_steps.value)
    best: list[tuple[float, float]] = []

    async def value(v: float) -> float:
        found = await f(v)
        if found is None:
            return -math.inf
        best.append((v, found))
        return found

    x_a, x_b = high - _GOLDEN * (high - low), low + _GOLDEN * (high - low)
    f_a, f_b = await value(x_a), await value(x_b)
    for _ in range(steps):
        if high - low <= tolerance * high:
            if not best:
                break
            return max(best, key=lambda point: point[1])
        if f_a >= f_b:
            high, x_b, f_b = x_b, x_a, f_a
            x_a = high - _GOLDEN * (high - low)
            f_a = await value(x_a)
        else:
            low, x_a, f_a = x_a, x_b, f_b
            x_b = low + _GOLDEN * (high - low)
            f_b = await value(x_b)
    raise _not_converged(
        f"the search for the optimum did not narrow below {tolerance:.3g} of the speed in {steps} steps, "
        "or found no flyable speed",
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
        on_wing_limit: Whether the speed lies on the edge of the speeds the airplane can fly the state
            at (the wing cannot carry the lift just below it): the stall corner of the state.
    """

    v: float
    value: float
    on_wing_limit: bool


async def maximise_over_speed(f: Objective) -> Optimum:
    """The maximum of ``f`` over the airspeed: upward scan, then golden section around the best point.

    The upward scan skips the speeds where ``f`` is ``None`` before its first value and stops at the first
    ``None`` after it, so the feasible speeds are taken as one interval. The maximum is refined between the
    neighbours of the best scan point. If ``f`` is ``None`` just below the optimum, the optimum is on the
    edge of the flyable speeds (the stall corner of the state) and the result says so.

    Raises:
        FormulaError: ``no_feasible_speed`` if ``f`` is ``None`` at every scan speed (or the propeller
            table ends before any speed was feasible); ``not_converged`` from the search.
    """
    speeds: list[float] = []
    values: list[float] = []
    for v in scan_speeds():
        try:
            found = await f(v)
        except FormulaError as error:
            if values or error.code != "outside_propeller_table":
                raise
            raise no_feasible_speed(
                f"the thrust is below what the state needs at every speed the propeller table "
                f"covers (the table ends before {v:.4g} m/s)"
            ) from error
        if found is None:
            if values:
                break
            continue
        speeds.append(v)
        values.append(found)
    if not values:
        raise no_feasible_speed(
            "the airplane cannot fly this state at any speed of the scan at full throttle "
            f"(from {config().powered_speed_scan_start.value:g} m/s in steps of "
            f"{config().powered_speed_scan_step.value:g} m/s up to the scan limit)"
        )
    best = max(range(len(values)), key=values.__getitem__)
    step = config().powered_speed_scan_step.value
    # The lower end stays above half the speed: a relative width never narrows towards zero.
    low = max(speeds[best] - step, 0.5 * speeds[best])
    v_best, value = await golden_maximum(f, low, speeds[best] + step)
    probe = v_best * (1.0 - 10.0 * config().powered_optimum_tolerance.value)
    return Optimum(v_best, value, await f(probe) is None)


async def climb_angle(flight: PoweredFlight, v: float) -> float | None:
    """The steepest steady climb angle in rad at the speed ``v``, at full throttle; ``None`` if there is none.

    The force balances of the exact steady climb: along the path ``T - D(V, cos gamma) = m g sin gamma``
    and across it ``L = m g cos gamma``, so the drag is the one at the load factor ``cos gamma`` and the
    wing must be able to carry that lift. The excess ``F(gamma) = T - D - m g sin gamma`` falls with
    ``gamma``; the climb angle is its root, ``pi/2`` (vertical, the declared bound of the entry) where
    ``F`` is not negative there. Below the stall of level flight only the angles steep enough for the wing
    to carry ``m g cos gamma`` exist, so the bracket is found by bisection that treats "the wing cannot
    carry it" as "too shallow", and is then refined by Illinois regula falsi. ``None`` where no angle
    is both flyable and held by the thrust.

    The search assumes ``F`` has one root on the angles the wing can carry (the lift of a steeper climb is
    smaller, so the induced drag is too, and the weight component grows).

    Raises:
        FormulaError: As :meth:`PoweredFlight.thrust` and :meth:`PoweredFlight.required_drag`.
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
        return None
    low = (0.0, f_level) if f_level is not None else None
    shallow, steep = 0.0, RIGHT_ANGLE
    tolerance = config().powered_optimum_tolerance.value
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
        return None
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


async def sustained_load_factor(flight: PoweredFlight, v: float, n_lim: float) -> TurnLimit | None:
    """The highest load factor ``n`` in ``[1, n_lim]`` that the airplane holds in a level turn at ``v``.

    A sustained turn is level at constant speed: ``L = n m g`` and ``T >= D(V, n)``, with the drag at
    the load factor ``n`` and the wing on the branch before the stall. Feasibility falls with ``n``
    (more lift: more induced drag, and the stall), so the highest feasible ``n`` is found by bisection
    on ``[1, n_lim]`` to ``powered_optimum_tolerance``; the answer is the feasible end. ``None`` where
    level flight itself is not held (the wing or the thrust).

    Raises:
        FormulaError: As :meth:`PoweredFlight.thrust` and :meth:`PoweredFlight.drag`.
    """

    async def verdict(n: float) -> str | None:
        """``None`` if the turn at ``n`` is held, else the limit that stops it."""
        drag = await flight.drag(v, n)
        if drag is None:
            return "wing"
        return None if flight.thrust(v) >= drag else "thrust"

    if await verdict(LEVEL_FLIGHT) is not None:
        return None
    stop = await verdict(n_lim)
    if stop is None:
        return TurnLimit(n_lim, "structure")
    low, high, tolerance = LEVEL_FLIGHT, n_lim, config().powered_optimum_tolerance.value
    while high - low > tolerance * high:
        middle = 0.5 * (low + high)
        found = await verdict(middle)
        if found is None:
            low = middle
        else:
            high, stop = middle, found
    return TurnLimit(low, stop)


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
            of :meth:`PoweredFlight.thrust`.
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
    slower speed) are declared with the notice ``powered_limit_declared``.
    """
    v, vertical = optimum.v, gamma >= RIGHT_ANGLE
    await flight.answer(v, VERTICAL_FLIGHT if vertical else math.cos(gamma))
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
        declare_limit(
            flight.ctx,
            "wing",
            f"The optimum lies on the stall corner: at {v:.4g} m/s the wing carries the lift of the "
            "climb at its maximum before the stall, and a slower speed would need more lift than the "
            "wing gives. The climb is limited by the wing at this speed, not by the thrust.",
            {"v_ms": v},
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

    async def at_speed(v: float) -> float | None:
        found = await sustained_load_factor(flight, v, n_lim)
        if found is None or found.n <= LEVEL_FLIGHT:
            return None
        return objective(v, found.n)

    v = (await maximise_over_speed(at_speed)).v
    limit = await sustained_load_factor(flight, v, n_lim)
    if limit is None:  # pragma: no cover - the maximum is evaluated at a speed that held a turn
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
