"""Canon formula ``endurance-and-range-optimum``: the greatest flight time and the greatest range.

``t_max = 3600 E_bat / min_V P_bat(V)`` and ``R_max = 3600 E_bat / min_V (P_bat(V) / V)``, the minima
taken over the speeds the airplane can fly level at full throttle or less, with the battery power
``P_bat(V)`` from the embedded ``motor-propeller-part-load`` relation (ADR 0022; no assumed
drive-train efficiency, maintainer 2026-10-25, #1235). The stall speed is the input ``v_s``
(canon quantity ``stall-speed``, application ``clean``): the lower end of the domain.

The domain and its search (declared, never silent)
--------------------------------------------------
A **scan** starts at the stall speed and rises by the ratio ``endurance_speed_ratio`` (``config.yaml``)
until the drive train cannot hold the speed (``r_T > 1``) or the part-load chain has no answer there
(``outside_propeller_table``: the table holds no balance at that speed; ``no_thrust_at_full_throttle`` or
``propeller_windmilling``: the full-throttle thrust has vanished), or the Mach limit of the RC/UAV regime
(rule ``reynolds-mach-regime``, ADR 0028) is reached. A speed at which the level-flight solve does
not converge (near the stall speed the weight is carried only at the lift peak) is not in the domain;
the domain starts at the lowest scan speed that solves. The best scan speed of each objective is
refined by golden section inside its two neighbouring cells to the relative width
``endurance_speed_tolerance``; a speed outside the domain counts as worse than any speed inside it.
Where the optimum lies on a bound of the domain the ``warning`` ``optimum_at_domain_bound`` says which.
Unimodality of ``P_bat`` and ``P_bat / V`` between neighbouring scan speeds is assumed.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.motor_propeller_part_load import (
    SpeedPoint,
    energy_over_power,
    forward_part_load_caveats,
    part_load_at,
)
from aero_kernel.formulas.values import number
from aero_kernel.registry import formula
from aero_kernel.solvers.regime import REGIME_RULE
from pydantic import JsonValue

__all__ = ["endurance_and_range_optimum"]

# The failures of the part-load chain that end the domain at a speed, by the bound they name. All four
# depend on the speed: the level-flight solve has no answer (near the stall speed), the table holds no
# balance, or the full-throttle thrust of the drive train has vanished (no thrust, or a propeller
# driven by the airstream). Any other failure (a missing input) is not about the speed and passes.
_EXIT_BOUNDS = {
    "not_converged": "level_flight_solution",
    "outside_propeller_table": "propeller_table",
    "no_thrust_at_full_throttle": "full_throttle_thrust",
    "propeller_windmilling": "full_throttle_thrust",
}
_FULL_THROTTLE = "full_throttle"
_STALL_SPEED = "stall_speed"
_MACH_LIMIT = "mach_limit"
_GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0  # the golden-section ratio, a mathematical constant

Objective = Callable[[SpeedPoint], float]


def _endurance_cost(speed: SpeedPoint) -> float:
    """The battery power in W: least where the flight time is longest."""
    return speed.point.p_bat


def _range_cost(speed: SpeedPoint) -> float:
    """The battery energy per metre in J/m: least where the range is longest."""
    return speed.point.p_bat / speed.v


@dataclass(frozen=True)
class _Found:
    """The optimum of one objective.

    Attributes:
        speed: The best evaluated speed with its part-load point.
        bound: The bound of the domain the optimum lies on, or ``None`` if it is interior.
        edge_v: The speed of that bound in m/s, or ``None``.
    """

    speed: SpeedPoint
    bound: str | None
    edge_v: float | None


class _Domain:
    """The speeds the airplane can fly level at full throttle or less, searched through one cache.

    Every speed is evaluated once, whichever search asks for it (ADR 0020: the scan and both
    refinements share the evaluations).
    """

    def __init__(self, x: Inputs, ctx: Context, v_s: float, v_cap: float) -> None:
        self._x, self._ctx, self._v_s, self.v_cap = x, ctx, v_s, v_cap
        self._ratio = config().endurance_speed_ratio.value
        self._tolerance = config().endurance_speed_tolerance.value
        self._outcome: dict[float, SpeedPoint | str] = {}  # a point inside, a bound's name outside
        self.grid: list[float] = []

    async def at(self, v: float) -> SpeedPoint | str:
        """The part-load point at ``v``, or the name of the bound that puts ``v`` outside."""
        if v not in self._outcome:
            self._outcome[v] = await self._evaluate(v)
        return self._outcome[v]

    async def _evaluate(self, v: float) -> SpeedPoint | str:
        """One evaluation: a point where the drive train holds the speed, else the bound's name."""
        try:
            speed = await part_load_at(self._x, self._ctx, v)
        except FormulaError as error:
            bound = _EXIT_BOUNDS.get(error.code)
            if bound is None:
                raise
            return bound
        return speed if speed.point.r_t <= 1.0 else _FULL_THROTTLE

    def inside(self, v: float) -> SpeedPoint | None:
        """The evaluated point at ``v`` if ``v`` is inside the domain."""
        found = self._outcome.get(v)
        return found if isinstance(found, SpeedPoint) else None

    def _bound_of(self, v: float) -> str | None:
        """The bound that makes the evaluated speed ``v`` an edge of the domain, ``None`` if inside."""
        found = self._outcome.get(v)
        return found if isinstance(found, str) else None

    async def scan(self) -> None:
        """Evaluate the speeds from the stall speed up, until the domain ends or the Mach limit.

        Raises:
            FormulaError: ``no_level_flight_speed`` if no scan speed is inside the domain.
        """
        v = self._v_s
        while v <= self.v_cap:
            outcome = await self.at(v)
            self.grid.append(v)
            if isinstance(outcome, str) and any(self.inside(g) for g in self.grid):
                return  # the first speed outside after the domain began is its upper end
            v *= self._ratio
        if not any(self.inside(g) for g in self.grid):
            raise self._empty()

    def _empty(self) -> FormulaError:
        """The declared failure of a scan without a single speed inside the domain."""
        reasons: dict[str, JsonValue] = {f"{v:.4g}": str(self._outcome.get(v)) for v in self.grid}
        return FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "no_level_flight_speed",
            f"endurance-and-range-optimum: no speed from the stall speed {self._v_s:.4g} m/s up to the "
            f"Mach limit speed {self.v_cap:.4g} m/s is inside the domain (level flight at full "
            "throttle or less, on the propeller table).",
            "Check the stall speed, the drive train and the propeller table; the kernel does not "
            "extrapolate.",
            detail={"stall_speed_ms": self._v_s, "limit_speed_ms": self.v_cap, "outcomes": reasons},
        )

    async def optimum(self, cost: Objective) -> _Found:
        """The speed of least cost: the best scan speed refined inside its two neighbouring cells."""
        best = min((p for g in self.grid if (p := self.inside(g))), key=cost)
        i = self.grid.index(best.v)
        lo = self.grid[i - 1] if i > 0 else best.v
        hi = self.grid[i + 1] if i + 1 < len(self.grid) else max(best.v, self.v_cap)
        await self._golden(cost, lo, hi)
        found = min((p for v in self._outcome if (p := self.inside(v))), key=cost)
        return self._found(found)

    async def _golden(self, cost: Objective, lo: float, hi: float) -> None:
        """Golden-section search of the cost on ``[lo, hi]``; a speed outside the domain costs infinity.

        The search only evaluates (into the shared cache); the optimum is read off the cache.
        """

        async def value(v: float) -> float:
            found = await self.at(v) if v <= self.v_cap else None
            return cost(found) if isinstance(found, SpeedPoint) else math.inf

        a, b = lo, hi
        c, d = b - _GOLDEN * (b - a), a + _GOLDEN * (b - a)
        f_c, f_d = await value(c), await value(d)
        while b - a > self._tolerance * b:
            if f_c <= f_d:
                b, d, f_d = d, c, f_c
                c = b - _GOLDEN * (b - a)
                f_c = await value(c)
            else:
                a, c, f_c = c, d, f_d
                d = a + _GOLDEN * (b - a)
                f_d = await value(d)

    def _found(self, speed: SpeedPoint) -> _Found:
        """The optimum, and the bound of the domain it lies on if the search ended against one.

        The search ended against a bound when the nearest evaluated speed on one side lies outside
        the domain and within the search resolution of the best speed, or the best speed is at the
        stall speed or the Mach limit within that resolution.
        """
        v, resolution = speed.v, self._tolerance * speed.v
        below = max((u for u in self._outcome if u < v), default=None)
        above = min((u for u in self._outcome if u > v), default=None)
        if v - self._v_s <= resolution:
            return _Found(speed, self._bound_of(self._v_s) or _STALL_SPEED, self._v_s)
        if below is not None and self._bound_of(below) and v - below <= resolution:
            return _Found(speed, self._bound_of(below), below)
        if above is not None and self._bound_of(above) and above - v <= resolution:
            return _Found(speed, self._bound_of(above), above)
        if self.v_cap - v <= resolution:
            return _Found(speed, _MACH_LIMIT, self.v_cap)
        return _Found(speed, None, None)


def _declare_bound(ctx: Context, what: str, found: _Found) -> None:
    """Report an optimum on a bound of the domain (the canon: reported, never accepted silently)."""
    if found.bound is None:
        return
    ctx.warn(
        "optimum_at_domain_bound",
        f"The greatest {what} lies on a bound of the speed domain: the bound `{found.bound}` at "
        f"{found.edge_v:.4g} m/s (best speed {found.speed.v:.4g} m/s). The upper edge of the domain "
        "is resolved to the scan cell, not to the exact crossing.",
        {"objective": what, "bound": found.bound, "edge_v_ms": found.edge_v, "v_ms": found.speed.v},
    )


@formula("endurance-and-range-optimum")
async def endurance_and_range_optimum(x: Inputs, ctx: Context) -> dict[str, float]:
    """The greatest flight time and the greatest range on the rated battery energy.

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, ``rho`` in kg/m^3, ``mu`` in Pa s, ``a`` in
            m/s, ``e_bat`` in Wh, ``v_s`` the clean stall speed in m/s, ``components``, ``k_v`` in
            rpm/V, ``i_0`` in A, ``r_m`` in ohm, ``u_bat`` in V, ``d_prop`` in m; ``p_mot_max`` and
            ``eta_mot`` are bound for route A and not read on route B.
        ctx: The formula context; it runs AeroBuildup and hands out the embedded relations.

    Returns:
        ``t_max`` in s and ``r_max`` in m.

    Raises:
        TypeError: If ``airplane`` or ``components`` is not the document.
        FormulaError: ``missing_input`` for an absent ``r_m`` or ``i_0``; ``no_level_flight_speed``;
            ``non_positive_battery_power``; a failure of the part-load chain that is not about the
            speed passes unchanged.
    """
    mach_limit = ctx.solvers.rules.value(REGIME_RULE, "mach_limit")
    domain = _Domain(x, ctx, number(x, "v_s"), mach_limit * number(x, "a"))
    await domain.scan()
    endurance = await domain.optimum(_endurance_cost)
    best_range = await domain.optimum(_range_cost)
    e_bat = number(x, "e_bat")
    t_max = energy_over_power(e_bat, endurance.speed.point.p_bat, endurance.speed.v)
    r_max = best_range.speed.v * energy_over_power(
        e_bat, best_range.speed.point.p_bat, best_range.speed.v
    )
    forward_part_load_caveats(ctx, [endurance.speed, best_range.speed], e_bat)
    _declare_bound(ctx, "endurance", endurance)
    _declare_bound(ctx, "range", best_range)
    return {"t_max": t_max, "r_max": r_max}
