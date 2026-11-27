"""Canon formula ``mass-envelope``: the largest masses at which level flight and the lift-off are held.

The entry poses two problems over the mass ``m``; the kernel solves them by what they are, from the pieces
that exist (ARCHITECTURE ch. 8.5, 8.12):

- ``m_max,level``: the largest mass for which some speed has ``T(V) - D(V) >= 0`` in level flight with
  ``L = m g`` (the speed scan starts at the clean stall speed of that mass, the stall solve at the mass,
  as in ``max-level-speed`` since gh-1419). The best excess over the speed, ``G(m) = max_V (T - D)``, falls with the mass and is zero at
  ``m_max,level``; the mass is its root. At that mass the thrust equals the drag at the best speed and no
  climb is left;
- the curves over the mass: ``V_S(m)`` (the stall solve), ``V_max(m)`` and ``ROC_max(m)`` at
  ``mass_envelope_curve_points`` equally spaced masses from the current mass up to ``m_max,level``, closed
  by the root. ``V_max`` and ``ROC_max`` are :func:`highest_level_speed` and :func:`best_climb`, the very
  functions ``max-level-speed`` and ``best-rate-of-climb`` run, at the sample mass with its clean stall speed:
  one producer of each (ADR 0022), same scan grid and start, no search of its own;
- ``m_max,TO``: the root of ``H(m) = T(V_TO) - D(V_TO)`` over the mass, with
  ``V_TO(m) = V_S,TO(m) V_TO / V_S,TO`` (the take-off reserve of the current mass kept), the take-off
  configuration and ``L = m g``.

The thrust and the drag are the shared ones of ``powered_flight`` (:class:`PoweredFlight`: the drive-train
relations and ``OptiAdapter.level_flight_point``) and the stall is ``OptiAdapter.stall`` with the check of
``stall-speed`` (``optimum_at_main_cl_peak``) on every solve; this module writes the two root searches and
no physics. The embedded optimisations are used as the shared functions of their modules, not through
``Context.embedded``, which hands out only the registered relations (the four propulsion relations;
ARCHITECTURE ch. 8.12 defers the relation form of an embedded optimisation).

**The search.** The mass is scanned upward from the current mass, each step by the factor
``1 + mass_envelope_step`` (geometric: the largest mass of a thrust-limited model is a multiple of its mass,
and each scan point costs a speed search), to the first mass at which the function is not positive; the root
in that bracket is refined by Illinois regula falsi. A current mass at which the state is not held is the
declared failure ``no_feasible_speed`` (the largest mass then lies below it; no downward search). A root not
reached in ``mass_envelope_max_steps`` steps is ``not_converged``.

**What closes the bracket without a sign change** (ADR 0020, declared by ``powered_limit_declared`` with
``limit = evaluation_edge``): at a mass above the current one the function cannot be evaluated because the
data end, namely ``no_feasible_speed`` of the level problem (no speed inside the propeller table at which
the wing carries the weight) and ``outside_propeller_table`` of the lift-off problem (the lift-off speed is
beyond the table). The edge between the last mass that evaluates and the first that does not is bisected to
``mass_envelope_edge_tolerance`` and the last mass that evaluates is the answer. Every other failure at any mass
(a stall solve that does not converge, a stall off the main lift peak, a missing input) is not "not held":
it surfaces unchanged, with the mass in the message and in ``detail.mass_kg``.

**Warnings forwarded** (ADR 0020): those of the answer of each root, the level-flight state at
``m_max,level`` and the take-off state at ``m_max,TO`` (with the flap-validity declaration of its stall
solve), the route notice and the skipped speeds once, and those of the curve samples as one summary per
code and declared limit (:meth:`Envelope.forward_samples`). The warnings of the iterates of the root
searches are not forwarded.
"""

import math
from collections.abc import Awaitable, Callable, Collection, Mapping

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs, Value
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.best_rate_of_climb import best_climb
from aero_kernel.formulas.flap_validity import warn_flap_validity
from aero_kernel.formulas.max_level_speed import highest_level_speed
from aero_kernel.formulas.powered_flight import (
    LEVEL_FLIGHT,
    Optimum,
    PoweredFlight,
    Unflyable,
    declare_limit,
    finish_climb,
    illinois_root,
    maximise_over_speed,
    no_feasible_speed,
)
from aero_kernel.formulas.stall_speed import main_extremum_check
from aero_kernel.formulas.values import air_state, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import CheckResult, formula, precondition
from aero_kernel.schema import Curve, KernelWarning
from aero_kernel.solvers.opti import Stall
from pydantic import JsonValue

__all__ = ["current_mass_positive", "mass_envelope", "takeoff_speed_above_stall_speed"]

Root = tuple[float, float]  # a mass in kg and the function value there in N
LEVEL_NOT_HELD = frozenset({"no_feasible_speed"})  # the level problem has no speed inside the table
TAKEOFF_NOT_HELD = frozenset({"outside_propeller_table"})  # the lift-off speed is beyond the table
ROUTE_NOTICE = "powertrain_route_winding_resistance"  # declared once by the answers, not per sample


@precondition("mass-envelope", "takeoff_speed_above_stall_speed")
def takeoff_speed_above_stall_speed(x: Mapping[str, object]) -> CheckResult:
    """The take-off speed must be above the take-off stall speed, which must be above 0.

    The scan keeps the take-off reserve ``V_TO / V_S,TO`` of the current mass; a reserve of 1 or less
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


@precondition("mass-envelope", "current_mass_positive")
def current_mass_positive(x: Mapping[str, object]) -> CheckResult:
    """The current mass, the start of the scan, must be a finite number above 0 kg."""
    mass = number(x, "m_current")
    if math.isfinite(mass) and mass > 0.0:
        return CheckResult(state="held", message=f"the current mass {mass} kg is above zero")
    return CheckResult(
        state="violated",
        message=f"the current mass {mass} kg is not a finite number above zero; give it in kg",
    )


def _not_held_at_current(what: str, mass: float) -> FormulaError:
    """The declared failure of a state that is already lost at the current mass."""
    return no_feasible_speed(
        f"{what} is not held at the current mass of {mass:.4g} kg, so the largest mass lies below it; "
        "the scan goes upward from the current mass and a downward search is not built"
    )


def _no_bracket(what: str, mass: float, steps: int) -> FormulaError:
    """``not_converged``: the state is still held at the last mass of the upward scan."""
    return FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        f"{what} is still held at {mass:.4g} kg, the last mass of the search ({steps} steps)",
        "report the case; the step limit (mass_envelope_max_steps or powered_search_max_steps) ends the search",
        detail={"mass_kg": mass, "steps": steps},
    )


def _stall_off_peak(result: CheckResult, mass: float, what: str) -> FormulaError:
    """The stall optimum is not the main C_L peak at a mass of the scan (the embedded check of ``stall-speed``)."""
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "postcondition_violated",
        f"at the mass {mass:.4g} kg the stall solve of {what} violates optimum_at_main_cl_peak: "
        f"{result.message}",
        "the stall speed of this mass is not on the branch before the main lift peak; report the case",
        detail={"embedded": what, "mass_kg": mass},
    )


def _named_at(error: FormulaError, mass: float) -> FormulaError:
    """The same failure with the mass of the scan in its message and in ``detail.mass_kg``."""
    return FormulaError(
        error.category,
        error.code,
        f"at the mass {mass:.4g} kg: {error.message}",
        error.hint,
        {**error.detail, "mass_kg": mass},
        error.parameter,
    )


class _DataEndError(Exception):
    """An iterate of a refinement could not be evaluated because the data end (internal, never escapes)."""

    def __init__(self, mass: float, reason: str) -> None:
        super().__init__(reason)
        self.mass, self.reason = mass, reason


class Envelope:
    """The scan of one call: flights and stall solves at a mass, the two root searches over the mass."""

    def __init__(self, x: Inputs, ctx: Context) -> None:
        self.x, self.ctx = x, ctx
        self.mass = number(x, "m_current")
        self.gravity = number(x, "g")
        self.reserve = number(x, "v_to") / number(x, "v_s_to")
        settings = config()
        self.step = settings.mass_envelope_step.value
        self.steps = round(settings.mass_envelope_max_steps.value)
        self.points = round(settings.mass_envelope_curve_points.value)
        self._levels: dict[float, tuple[PoweredFlight, Optimum]] = {}  # the best excess per mass
        self._stalls: dict[
            tuple[float, bool], Stall
        ] = {}  # one stall solve per mass and configuration

    def at(self, mass: float, v_s: float, *, takeoff: bool = False) -> Inputs:
        """``x`` of the shared powered-flight code at ``mass`` with its clean stall speed ``v_s`` in m/s.

        For the take-off the configuration is the take-off airplane (and ``v_s`` is its stall speed, which
        the lift-off state does not scan from).
        """
        found: dict[str, Value | None] = {**self.x, "m": mass, "v_s": v_s}
        if takeoff:
            found["airplane"] = self.x["airplane_to"]
        return found

    def flight(
        self, mass: float, v_s: float, *, takeoff: bool = False, ctx: Context | None = None
    ) -> PoweredFlight:
        """The thrust and drag of the airplane at ``mass`` (on ``ctx``, this call's context by default)."""
        return PoweredFlight(self.at(mass, v_s, takeoff=takeoff), ctx or self.ctx)

    def airplane(self, *, takeoff: bool) -> AirplaneGeometry:
        """The geometry of the configuration."""
        value = self.x["airplane_to" if takeoff else "airplane"]
        if not isinstance(value, AirplaneGeometry):
            msg = "the airplane of the scan must be the geometry document"
            raise TypeError(msg)
        return value

    async def stall(self, mass: float, *, takeoff: bool) -> Stall:
        """The stall problem at ``mass`` with the embedded check of ``stall-speed`` on its optimum.

        Solved once per mass and configuration within the call (the roots and the curves meet at the same
        masses: the current mass, the root, the iterates).
        """
        key = (mass, takeoff)
        if key not in self._stalls:
            stall = await self.ctx.solvers.opti.stall(
                self.airplane(takeoff=takeoff), mass, self.gravity, LEVEL_FLIGHT, air_state(self.x)
            )
            solution = stall.solution
            checked = main_extremum_check(
                solution.polar, solution.alpha_s, solution.cl_max, upright=True
            )
            if checked.state != "held":
                raise _stall_off_peak(
                    checked, mass, "stall-speed.takeoff" if takeoff else "stall-speed.clean"
                )
            self._stalls[key] = stall
        return self._stalls[key]

    async def best_excess(self, mass: float) -> tuple[PoweredFlight, Optimum]:
        """The largest ``T - D`` over the speed in level flight at ``mass``, and the speed of it (kept per mass)."""
        if mass not in self._levels:
            v_s = (await self.stall(mass, takeoff=False)).solution.v_s
            flight = self.flight(mass, v_s)

            async def excess(v: float) -> float | Unflyable:
                drag = await flight.drag(v, LEVEL_FLIGHT)
                return Unflyable.WING if drag is None else flight.thrust(v) - drag

            self._levels[mass] = (flight, await maximise_over_speed(excess, flight, v_s))
        return self._levels[mass]

    async def level_function(self, mass: float) -> float:
        """``G(m)``: the best excess thrust over the drag in level flight, in N."""
        return (await self.best_excess(mass))[1].value

    async def takeoff_function(self, mass: float) -> float:
        """``H(m)``: thrust minus drag at ``V_TO(m)`` in the take-off configuration, in N."""
        v_s = (await self.stall(mass, takeoff=True)).solution.v_s
        v_to = self.reserve * v_s
        flight = self.flight(mass, v_s, takeoff=True)
        return flight.thrust(v_to) - await flight.required_drag(v_to, LEVEL_FLIGHT)

    async def value(
        self, f: Callable[[float], Awaitable[float]], mass: float, not_held: Collection[str]
    ) -> tuple[float | None, str]:
        """``f(mass)``, or ``None`` with the reason where the failure is one of ``not_held`` (the data end).

        Every other failure surfaces with the mass named (:func:`_named_at`).
        """
        try:
            return await f(mass), ""
        except FormulaError as error:
            if error.code in not_held:
                return None, error.message
            raise _named_at(error, mass) from error

    async def root(
        self,
        f: Callable[[float], Awaitable[float]],
        what: str,
        not_held: Collection[str],
    ) -> tuple[float, bool]:
        """The mass at which ``f`` is zero, and whether it is the edge of the data instead of a sign change.

        The upward scan of the mass to a bracket, then Illinois regula falsi (:meth:`refine`).

        Raises:
            FormulaError: ``no_feasible_speed`` where ``f`` is not positive at the current mass;
                ``not_converged`` where it is still positive at the last mass of the scan or the edge
                search does not narrow; any other failure of ``f`` with the mass named.
        """
        first, _ = await self.value(f, self.mass, ())
        if (
            first is None or first <= 0.0
        ):  # None cannot happen: nothing is "not held" at the current mass
            raise _not_held_at_current(what, self.mass)
        low: Root = (self.mass, first)
        for k in range(1, self.steps + 1):
            mass = self.mass * (1.0 + self.step) ** k
            found, reason = await self.value(f, mass, not_held)
            if found is None:
                return await self.edge(f, low, mass, what, reason, not_held)
            if found <= 0.0:
                return await self.refine(f, low, (mass, found), what, not_held)
            low = (mass, found)
        raise _no_bracket(what, low[0], self.steps)

    async def refine(
        self,
        f: Callable[[float], Awaitable[float]],
        low: Root,
        high: Root,
        what: str,
        not_held: Collection[str],
    ) -> tuple[float, bool]:
        """Illinois regula falsi between two masses with opposite signs, every iterate through :meth:`value`.

        A failure at an iterate carries its mass (not the current mass). An iterate that cannot be
        evaluated because the data end is not a sign: the data end lies between the low mass and that
        iterate, and the edge search takes it from there (the same outcome as in the scan).
        """

        async def checked(mass: float) -> float:
            found, reason = await self.value(f, mass, not_held)
            if found is None:
                raise _DataEndError(mass, reason)
            return found

        try:
            return await illinois_root(checked, low, high, self.mass * self.gravity), False
        except _DataEndError as end:
            return await self.edge(f, low, end.mass, what, end.reason, not_held)

    async def edge(
        self,
        f: Callable[[float], Awaitable[float]],
        low: Root,
        high: float,
        what: str,
        reason: str,
        not_held: Collection[str],
    ) -> tuple[float, bool]:
        """The last mass at which ``f`` evaluates (and is positive) below the first mass that does not.

        The edge is bisected to ``mass_envelope_edge_tolerance`` of the mass; a sign change found on the way
        is refined as a root. The answer at the edge is declared (``powered_limit_declared``).
        """
        settings = config()
        tolerance = settings.mass_envelope_edge_tolerance.value
        limit = round(settings.powered_search_max_steps.value)
        for _ in range(limit):
            if high - low[0] <= tolerance * low[0]:
                declare_limit(
                    self.ctx,
                    "evaluation_edge",
                    f"{what.capitalize()} is still held at {low[0]:.4g} kg, the last mass at which it can be "
                    f"evaluated; above it the data end ({reason}). The mass is the edge of the data, not a "
                    "sign change of the force balance.",
                    {"mass_kg": low[0], "first_unevaluable_mass_kg": high},
                )
                return low[0], True
            mid = 0.5 * (low[0] + high)
            found, why = await self.value(f, mid, not_held)
            if found is None:
                high, reason = mid, why  # the reason of the first mass that does not evaluate
            elif found <= 0.0:
                return await self.refine(f, low, (mid, found), what, not_held)
            else:
                low = (mid, found)
        raise _no_bracket(what, low[0], limit)

    async def sample(self, mass: float) -> tuple[float, float, float, tuple[KernelWarning, ...]]:
        """``V_S``, ``V_max`` and ``ROC_max`` at one sample mass, and the warnings that sample produced.

        The values come from the functions of the two formulas. Their answer states are evaluated once
        more, as each formula does, on a scratch context, so the warnings of the stall solve, of the level
        answer and of the climb answer (regime, flap, the limits declared) are returned for the summary
        of :meth:`curves` instead of being dropped. Every failure surfaces with the mass named.
        """
        sub = self.ctx.scratch()
        try:
            stall = await self.stall(mass, takeoff=False)
            v_s = stall.solution.v_s
            forward_warnings(sub, stall.warnings)
            warn_flap_validity(sub, self.airplane(takeoff=False), stall.solution.diagnostics)
            flight = self.flight(mass, v_s, ctx=sub)
            v_max = await highest_level_speed(flight)
            await flight.answer(v_max, LEVEL_FLIGHT)
            optimum, gamma = await best_climb(flight)
            await finish_climb(flight, optimum, gamma)
        except FormulaError as error:
            raise _named_at(error, mass) from error
        return v_s, v_max, optimum.value, sub.warnings

    async def curves(
        self, root: float, *, edge: bool
    ) -> tuple[tuple[Curve, Curve], Curve, tuple[float, ...]]:
        """The speed range and the best rate of climb over the masses of the sweep, and the masses.

        The samples are equally spaced from the current mass up to (not including) ``m_max,level``, each
        computed by :meth:`sample`. The last point is the root:

        - where the root is the edge of the data (``edge``), the thrust still exceeds the drag there, so it
          is computed like every other sample;
        - where the root is a sign change of the best excess, the thrust equals the drag at the best speed
          there: that is the root condition itself, so ``V_max`` is the speed of the best excess the root
          search found and the rate of climb is zero (within the tolerance of the root); only the stall
          speed is computed.

        The warnings of all the samples are forwarded as one summary (:meth:`forward_samples`).
        """
        masses = [self.mass + (root - self.mass) * k / self.points for k in range(self.points)]
        samples = [await self.sample(mass) for mass in masses]
        masses.append(root)
        if edge:
            samples.append(await self.sample(root))
        else:
            v_s_root = (await self.stall(root, takeoff=False)).solution.v_s
            v_best = (await self.best_excess(root))[1].v
            samples.append((v_s_root, v_best, 0.0, ()))
        self.forward_samples(masses, [x[3] for x in samples])
        grid = tuple(masses)
        speed_range = (
            Curve(x=grid, y=tuple(x[0] for x in samples)),
            Curve(x=grid, y=tuple(x[1] for x in samples)),
        )
        return speed_range, Curve(x=grid, y=tuple(x[2] for x in samples)), grid

    def forward_samples(self, masses: list[float], found: list[tuple[KernelWarning, ...]]) -> None:
        """Forward the warnings of the curve samples as summaries with the masses they occurred at (ADR 0020).

        One summary per code and, for a declared limit, per ``detail.limit``: a sample can declare two
        limits under one code (the floor of the climb scan and the vertical climb), and different samples
        different ones. The message and the detail of the first occurrence are kept; ``detail.masses_kg``
        lists the sample masses and ``detail.by_mass`` the detail of every occurrence. The stall solve, the
        level answer and the climb answer of one sample are different states, so the same code with a
        different message or detail at one mass is kept; only an identical repetition is listed once. The
        route notice is left out: the answers declare it once. The warnings of the iterates of the root
        searches are not forwarded (as in ``max-level-speed``); those of the answers are forwarded as they
        happen.
        """
        groups: dict[tuple[str, str], list[tuple[float, KernelWarning]]] = {}
        for mass, warnings in zip(masses, found, strict=True):
            for warning in warnings:
                if warning.code == ROUTE_NOTICE:
                    continue
                hits = groups.setdefault((warning.code, str(warning.detail.get("limit", ""))), [])
                if not any(
                    seen == mass and w.message == warning.message and w.detail == warning.detail
                    for seen, w in hits
                ):
                    hits.append((mass, warning))
        for (code, _), hits in groups.items():
            first = hits[0][1]
            at: list[JsonValue] = list(dict.fromkeys(mass for mass, _ in hits))  # each mass once
            self.ctx.warn(
                code,
                f"{first.message} (curve samples: occurred at {len(at)} of {len(masses)} masses)",
                {
                    **first.detail,
                    "masses_kg": at,
                    "by_mass": [{"mass_kg": mass, **w.detail} for mass, w in hits],
                },
            )

    async def declare_level(self, root: float) -> None:
        """Evaluate and declare the level-flight answer at ``m_max,level``, with its clean stall warnings."""
        stall = await self.stall(root, takeoff=False)
        forward_warnings(self.ctx, stall.warnings)
        warn_flap_validity(self.ctx, self.airplane(takeoff=False), stall.solution.diagnostics)
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

    async def declare_takeoff(self, root: float) -> None:
        """Evaluate and declare the take-off answer at ``m_max,TO``: its stall solve and its drag."""
        stall = await self.stall(root, takeoff=True)
        forward_warnings(self.ctx, stall.warnings)
        warn_flap_validity(self.ctx, self.airplane(takeoff=True), stall.solution.diagnostics)
        flight = self.flight(root, stall.solution.v_s, takeoff=True)
        await flight.answer(self.reserve * stall.solution.v_s, LEVEL_FLIGHT, declare=False)


@formula("mass-envelope")
async def mass_envelope(x: Inputs, ctx: Context) -> dict[str, float | Curve | tuple[Curve, Curve]]:
    """The two largest masses (level flight, lift-off) and the speed range and climb rate over the mass.

    Args:
        x: ``airplane`` and ``airplane_to`` the clean and the take-off configuration, ``m_current`` the
            current mass in kg (the start of the scan), ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in
            Pa s, ``a`` in m/s, ``v_s_to`` and ``v_to`` in m/s (the take-off reserve of the current mass),
            ``components``, ``k_v`` in rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in
            m; ``p_mot_max`` and ``eta_mot`` are bound for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup, hands out the embedded propulsion relations and
            declares the route, the skipped speeds and the bounds the answers lie on.

    Returns:
        ``m_max_level`` and ``m_max_to`` in kg; ``speed_range`` (the two curves ``V_S(m)`` and ``V_max(m)`` in m/s over
        the mass in kg; a ``curve_pair`` is not a result, so it is computed and not requestable) and ``roc_curve`` (the best rate of climb in m/s over the mass).

    Raises:
        TypeError: If ``airplane``, ``airplane_to`` or ``components`` is not the document.
        FormulaError: ``no_feasible_speed`` where level flight or the lift-off is not held at the current
            mass; ``not_converged`` where a state is still held at the last mass of the scan;
            ``postcondition_violated`` where a stall solve of the scan is not at the main lift peak;
            the failures of the searches and the drive train (``outside_propeller_table``,
            ``missing_input``), each with the mass of the scan named.
    """
    scan = Envelope(x, ctx)
    m_level, edge = await scan.root(scan.level_function, "level flight", LEVEL_NOT_HELD)
    await scan.declare_level(m_level)
    m_to, _ = await scan.root(scan.takeoff_function, "the lift-off", TAKEOFF_NOT_HELD)
    await scan.declare_takeoff(m_to)
    speed_range, roc_curve, _ = await scan.curves(m_level, edge=edge)
    return {
        "speed_range": speed_range,
        "roc_curve": roc_curve,
        "m_max_level": m_level,
        "m_max_to": m_to,
    }
