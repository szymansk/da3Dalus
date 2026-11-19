"""Canon formula ``mass-envelope``: what narrows with the take-off mass, and the masses at which it closes.

The entry poses a family of problems swept over the mass ``m``: the stall speed, the maximum level speed
and the best rate of climb at each mass, and the two masses at which flight stops. The kernel solves what
the entry says by what it is, from the pieces that exist (ARCHITECTURE ch. 8.5, 8.12):

- ``V_S(m)``: the stall problem (``OptiAdapter.stall``) at the mass, with the check of ``stall-speed``
  (``optimum_at_first_cl_peak``) on every solve;
- ``V_max(m)``: the upper root of the excess ``T - D`` over the speed, searched upward from the speed of the
  best excess (Illinois regula falsi, the same ``T`` and ``D`` as ``max-level-speed``). The speeds with an
  excess shrink to a window narrower than the scan step of ``max-level-speed`` as the mass nears
  ``m_max,level``, which that scan would miss; the best excess is known here, so the search starts at it;
- ``ROC_max(m)``: the maximum of ``V sin(gamma)`` over the speeds with a climb (``powered_flight.climb_angle``,
  the problem of ``best-rate-of-climb``), over the window of those speeds that the best excess gives, for
  the same reason (the scan of ``best-rate-of-climb`` would miss a narrow window);
- ``m_max,level``: the largest mass for which some speed has ``T(V) - D(V) >= 0`` in level flight with
  ``L = m g``. The best excess over the speed, ``G(m) = max_V (T - D)``, falls with the mass and is zero at
  ``m_max,level``; the mass is its root (an upward scan of the mass to a bracket, then Illinois regula
  falsi, :func:`aero_kernel.formulas.powered_flight.illinois_root`). At that mass the thrust equals the drag
  at the best speed and no climb is left: ``V_S``, ``V_max`` and the rate of climb meet there;
- ``m_max,TO``: the root of ``T(V_TO) - D(V_TO)`` over the mass, with ``V_TO(m) = V_S,TO(m) V_TO / V_S,TO``
  (the take-off reserve of the current mass kept), the take-off configuration and ``L = m g``.

The thrust and the drag are the shared ones of ``powered_flight`` (:class:`PoweredFlight`: the drive-train
relations and ``OptiAdapter.level_flight_point``); this module writes the mass loop and the two root
searches, no physics. The three optimisation formulas of the entry's ``embeds`` are used as the shared
functions of their modules, not through ``Context.embedded``, which hands out only the registered
relations (the four propulsion relations; ARCHITECTURE ch. 8.12 defers the relation form of an embedded
optimisation).

**The sweep** starts at the current mass and goes up in steps of ``mass_envelope_step`` of it until the
level flight is lost; the samples are the curves, closed by the root itself. A current mass at which the
state is already not held is the declared failure ``no_feasible_speed`` (the largest mass then lies below
it; a downward search is not built). A root not reached in ``mass_envelope_max_steps`` steps is
``not_converged``.

**Warnings forwarded** (ADR 0020): those of the answer of each scalar only, the level-flight state at
``m_max,level`` and the take-off state at ``m_max,TO`` (with the flap-validity declaration of its stall
solve), the route notice and the skipped speeds once. The warnings of the other evaluations (the samples of
the curves, the iterates of the searches) are not forwarded.
"""

import math
from collections.abc import Awaitable, Callable, Mapping

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs, Value
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.flap_validity import warn_flap_validity
from aero_kernel.formulas.powered_flight import (
    LEVEL_FLIGHT,
    Optimum,
    PoweredFlight,
    Unflyable,
    climb_angle,
    declare_limit,
    golden_maximum,
    illinois_root,
    maximise_over_speed,
    no_feasible_speed,
)
from aero_kernel.formulas.stall_speed import first_extremum_check
from aero_kernel.formulas.values import air_state, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import CheckResult, formula, precondition
from aero_kernel.schema import Curve, CurvePair
from aero_kernel.solvers.opti import Stall

__all__ = ["mass_envelope", "takeoff_speed_above_stall_speed"]

Root = tuple[float, float]  # a mass in kg and the function value there in N
_NEAR_EDGE = 1e-12  # m/s, keeps the penalty of a speed inside the window strictly negative


@precondition("mass-envelope", "takeoff_speed_above_stall_speed")
def takeoff_speed_above_stall_speed(x: Mapping[str, object]) -> CheckResult:
    """The take-off speed must be above the take-off stall speed, which must be above 0.

    The sweep keeps the take-off reserve ``V_TO / V_S,TO`` of the current mass; a reserve of 1 or less
    puts the lift-off at or below the stall, where no lift-off point exists.
    """
    v_s_to, v_to = number(x, "v_s_to"), number(x, "v_to")
    if 0.0 < v_s_to < v_to:
        return CheckResult(
            state="held",
            message=f"the take-off speed {v_to} m/s is above the stall speed {v_s_to} m/s",
        )
    return CheckResult(
        state="violated",
        message=(
            f"the take-off speed {v_to} m/s is not above the take-off stall speed {v_s_to} m/s, "
            "which must be above zero; the take-off reserve V_TO / V_S,TO must exceed 1"
        ),
    )


def _not_held_at_current(what: str, mass: float) -> FormulaError:
    """The declared failure of a state that is already lost at the current mass."""
    return no_feasible_speed(
        f"{what} is not held at the current mass of {mass:.4g} kg, so the largest mass lies below it; "
        "the sweep goes upward from the current mass and a downward search is not built"
    )


def _no_bracket(what: str, mass: float, steps: int) -> FormulaError:
    """``not_converged``: the state is still held at the last mass of the upward scan."""
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"{what} is still held at {mass:.4g} kg, the last mass of the scan ({steps} steps)",
        "report the case; the scan limit (mass_envelope_max_steps) ends the search",
        detail={"mass_kg": mass, "steps": steps},
    )


def _stall_off_peak(result: CheckResult, mass: float, what: str) -> FormulaError:
    """The stall optimum is not the first C_L peak at a mass of the sweep (the embedded check of ``stall-speed``)."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "postcondition_violated",
        f"at the mass {mass:.4g} kg the stall solve of {what} violates optimum_at_first_cl_peak: "
        f"{result.message}",
        "the stall speed of this mass is not on the branch before the first lift peak; report the case",
        detail={"embedded": what, "mass_kg": mass},
    )


class Envelope:
    """The mass loop of one call: flights and stall solves at a mass, the two searches over the mass."""

    def __init__(self, x: Inputs, ctx: Context) -> None:
        self.x, self.ctx = x, ctx
        self.mass = number(x, "m_current")
        self.gravity = number(x, "g")
        self.reserve = number(x, "v_to") / number(x, "v_s_to")
        settings = config()
        self.step = settings.mass_envelope_step.value
        self.steps = round(settings.mass_envelope_max_steps.value)
        self._levels: dict[float, tuple[PoweredFlight, Optimum]] = {}  # the best excess per mass

    def at(self, mass: float, *, takeoff: bool = False) -> Inputs:
        """``x`` of the shared powered-flight code at ``mass`` and, for the take-off, its configuration."""
        found: dict[str, Value | None] = {**self.x, "m": mass}
        if takeoff:
            found["airplane"] = self.x["airplane_to"]
        return found

    def flight(self, mass: float, *, takeoff: bool = False) -> PoweredFlight:
        """The thrust and drag of the airplane at ``mass``."""
        return PoweredFlight(self.at(mass, takeoff=takeoff), self.ctx)

    def airplane(self, *, takeoff: bool) -> AirplaneGeometry:
        """The geometry of the configuration."""
        value = self.x["airplane_to" if takeoff else "airplane"]
        if not isinstance(value, AirplaneGeometry):
            msg = "the airplane of the sweep must be the geometry document"
            raise TypeError(msg)
        return value

    async def stall(self, mass: float, *, takeoff: bool) -> Stall:
        """The stall problem at ``mass`` with the embedded check of ``stall-speed`` on its optimum."""
        stall = await self.ctx.solvers.opti.stall(
            self.airplane(takeoff=takeoff), mass, self.gravity, LEVEL_FLIGHT, air_state(self.x)
        )
        solution = stall.solution
        checked = first_extremum_check(
            solution.polar, solution.alpha_s, solution.cl_max, upright=True
        )
        if checked.state != "held":
            raise _stall_off_peak(
                checked, mass, "stall-speed.takeoff" if takeoff else "stall-speed.clean"
            )
        return stall

    async def best_excess(self, mass: float) -> tuple[PoweredFlight, Optimum]:
        """The largest ``T - D`` over the speed in level flight at ``mass``, and the speed of it (kept per mass)."""
        if mass not in self._levels:
            flight = self.flight(mass)

            async def excess(v: float) -> float | Unflyable:
                drag = await flight.drag(v, LEVEL_FLIGHT)
                return Unflyable.WING if drag is None else flight.thrust(v) - drag

            self._levels[mass] = (flight, await maximise_over_speed(excess, flight))
        return self._levels[mass]

    async def level_function(self, mass: float) -> float:
        """``G(m)``: the best excess thrust over the drag in level flight, in N."""
        return (await self.best_excess(mass))[1].value

    async def takeoff_function(self, mass: float) -> float:
        """``H(m)``: thrust minus drag at ``V_TO(m)`` in the take-off configuration, in N."""
        v_to = self.reserve * (await self.stall(mass, takeoff=True)).solution.v_s
        flight = self.flight(mass, takeoff=True)
        return flight.thrust(v_to) - await flight.required_drag(v_to, LEVEL_FLIGHT)

    async def bracket(
        self, f: Callable[[float], Awaitable[float]], what: str
    ) -> tuple[Root, Root, int]:
        """The first two masses of the upward scan between which ``f`` changes from positive to not positive.

        Returns:
            The last mass with a positive value and the first without (each with its value), and the
            number of masses of the scan that held (the first is the current mass).

        Raises:
            FormulaError: ``no_feasible_speed`` where ``f`` is not positive at the current mass;
                ``not_converged`` where it is still positive at the last mass of the scan.
        """
        previous: Root = (self.mass, await f(self.mass))
        if previous[1] <= 0.0:
            raise _not_held_at_current(what, self.mass)
        for k in range(1, self.steps + 1):
            mass = self.mass * (1.0 + k * self.step)
            current: Root = (mass, await f(mass))
            if current[1] <= 0.0:
                return previous, current, k
            previous = current
        raise _no_bracket(what, previous[0], self.steps)

    async def root(self, f: Callable[[float], Awaitable[float]], what: str) -> tuple[float, int]:
        """The mass at which ``f`` is zero and the number of scan masses below it."""
        low, high, held = await self.bracket(f, what)
        scale = self.mass * self.gravity
        return await illinois_root(f, low, high, scale), held

    async def level_speed_above(self, flight: PoweredFlight, v_best: float) -> float:
        """``V_max``: the upper root of ``T - D`` over the speed, searched upward from ``v_best`` in m/s.

        Raises:
            FormulaError: ``not_converged`` if the thrust still exceeds the drag at the scan limit;
                ``outside_propeller_table`` where the table ends first (from the thrust).
        """

        async def excess(v: float) -> float:
            return flight.thrust(v) - await flight.required_drag(v, LEVEL_FLIGHT)

        settings = config()
        step, limit = (
            settings.powered_speed_scan_step.value,
            settings.powered_speed_scan_limit.value,
        )
        low, speed = (v_best, await excess(v_best)), v_best + step
        while speed <= limit:
            value = await excess(speed)
            if value <= 0.0:
                return await illinois_root(excess, low, (speed, value), flight.weight)
            low, speed = (speed, value), speed + step
        raise _no_bracket("the level-flight excess thrust", limit, round(limit / step))

    async def climb_rate(self, flight: PoweredFlight, v_best: float, v_max: float) -> float:
        """``ROC_max`` in m/s: the best ``V sin(gamma)`` of the steady climb (the problem of ``best-rate-of-climb``).

        The speeds with a climb are searched where they are known to be: from ``V_max`` down to the lowest
        scan step below the speed of the best excess at which a climb still exists (the climb needs less
        lift than level flight, so it can go below the level stall speed), and one step further, where the
        edge of the climbs lies. The golden section needs a value at every probe, so where there is no climb
        the objective is the negative distance to the window of the speeds that have one (it rises toward
        it and stays below every rate); the maximum is a rate. The window is not scanned from the global
        start: near ``m_max,level`` it is narrower than the scan step and that scan would miss it.
        """
        step = config().powered_speed_scan_step.value

        async def rate(v: float) -> float | Unflyable:
            gamma = await climb_angle(flight, v)
            return gamma if isinstance(gamma, Unflyable) else v * math.sin(gamma)

        low = v_best
        while low > step and not isinstance(await rate(low - step), Unflyable):
            low -= step

        async def extended(v: float) -> float:
            found = await rate(v)
            if not isinstance(found, Unflyable):
                return found
            return -max(low - v, v - v_max, _NEAR_EDGE)

        return (await golden_maximum(extended, max(low - step, 0.0), v_max)).value

    async def sample(self, mass: float) -> tuple[float, float, float]:
        """``V_S``, ``V_max`` and ``ROC_max`` at one mass of the sweep."""
        v_s = (await self.stall(mass, takeoff=False)).solution.v_s
        flight, best = await self.best_excess(mass)
        v_max = await self.level_speed_above(flight, best.v)
        return v_s, v_max, await self.climb_rate(flight, best.v, v_max)

    async def curves(self, held: int, root: float, v_best: float) -> tuple[CurvePair, Curve]:
        """The speed range and the best rate of climb over the masses of the sweep, closed by the root.

        At the root the thrust equals the drag at the best speed only: ``V_max`` is that speed and the
        rate of climb is zero.
        """
        masses = [self.mass * (1.0 + k * self.step) for k in range(held)]
        samples = [await self.sample(mass) for mass in masses]
        v_s_root = (await self.stall(root, takeoff=False)).solution.v_s
        masses.append(root)
        stall = [s[0] for s in samples] + [v_s_root]
        top = [s[1] for s in samples] + [v_best]
        climb = [s[2] for s in samples] + [0.0]
        return CurvePair(x=tuple(masses), lower=tuple(stall), upper=tuple(top)), Curve(
            x=tuple(masses), y=tuple(climb)
        )

    async def declare_level(self, root: float) -> float:
        """Evaluate and declare the level-flight answer at ``m_max,level``; the speed of the best excess."""
        flight, optimum = await self.best_excess(root)
        point = await flight.answer(optimum.v, LEVEL_FLIGHT)
        if optimum.on_wing_limit:
            declare_limit(
                self.ctx,
                "wing",
                f"The best excess thrust at {root:.4g} kg lies at the stall corner, {optimum.v:.4g} m/s "
                f"(C_L = {point.cl:.3g}): the wing, not the thrust, ends the speed range there.",
                {"mass_kg": root, "v_ms": optimum.v, "cl": point.cl},
            )
        return optimum.v

    async def declare_takeoff(self, root: float) -> None:
        """Evaluate and declare the take-off answer at ``m_max,TO``: its stall solve and its drag."""
        stall = await self.stall(root, takeoff=True)
        forward_warnings(self.ctx, stall.warnings)
        warn_flap_validity(self.ctx, self.airplane(takeoff=True), stall.solution.diagnostics)
        flight = self.flight(root, takeoff=True)
        await flight.answer(self.reserve * stall.solution.v_s, LEVEL_FLIGHT, declare=False)


@formula("mass-envelope")
async def mass_envelope(x: Inputs, ctx: Context) -> dict[str, float | Curve | CurvePair]:
    """The speed range and the best rate of climb over the mass, and the two largest masses.

    Args:
        x: ``airplane`` and ``airplane_to`` the clean and the take-off configuration, ``m_current`` the
            current mass in kg (the start of the sweep), ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in
            Pa s, ``a`` in m/s, ``v_s_to`` and ``v_to`` in m/s (the take-off reserve of the current mass),
            ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in
            m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded propulsion relations and
            declares the route, the skipped speeds and the bounds the answers lie on.

    Returns:
        ``speed_range`` (``V_S`` and ``V_max`` over the mass, in m/s over kg), ``roc_curve`` (the best
        rate of climb in m/s over kg), ``m_max_level`` and ``m_max_to`` in kg. The curves are values
        inside the kernel: a request for them is ``non_scalar_result`` (ARCHITECTURE ch. 8.3).

    Raises:
        TypeError: If ``airplane``, ``airplane_to`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` where level flight or the lift-off is not held at the current
            mass; ``not_converged`` where a state is still held at the last mass of the scan;
            ``postcondition_violated`` where a stall solve of the sweep is not at the first lift peak;
            the failures of the searches and the drive train (``outside_propeller_table``,
            ``missing_input``).
    """
    sweep = Envelope(x, ctx)
    m_level, held = await sweep.root(sweep.level_function, "level flight")
    v_best = await sweep.declare_level(m_level)
    m_to, _ = await sweep.root(sweep.takeoff_function, "the lift-off")
    await sweep.declare_takeoff(m_to)
    speed_range, roc_curve = await sweep.curves(held, m_level, v_best)
    return {
        "speed_range": speed_range,
        "roc_curve": roc_curve,
        "m_max_level": m_level,
        "m_max_to": m_to,
    }
