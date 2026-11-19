"""Builders for the powered-performance tests (gh-1414): a closed-form airplane and an independent solution.

The AeroBuildup boundary is a stub with a parabolic polar, ``C_D = C_D0 + k C_L^2`` and ``C_L,max``, on the
wing area ``S``. The drive train is the T-Motor AT2814 KV900 on 14.8 V with the published APC 13x8E table; the
thrust of the independent solution is ``powertrain_reference.full_throttle`` (plain Python, bisection on rpm).
Everything below the stub (the root of ``T = D``, the climb angle, the load factor of a turn) is written here
again in closed form or by brute force, never by the kernel's searches.
"""

import functools
import math
from typing import Any

from aero_kernel.build import shipped_build
from aero_kernel.context import Context
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import KernelWarning
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import LevelFlightPoint, LevelPoint
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.formula_builders import inputs_from_model, solvers_with
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.wing_builders import airplane_document

# The reference reads the table file at every coefficient; read it once.
reference.apc_13x8e_table = functools.cache(reference.apc_13x8e_table)

RHO, G, MU, SOUND = 1.225, 9.80665, 1.8e-5, 340.0
AREA, CD0, K, CL_MAX = 0.5, 0.04, 0.06, 1.2
KV, I0, RM, U_BAT = 900.0, 1.2, 0.082, 14.8


class PolarOpti(StubOpti):
    """``level_flight_point`` of a parabolic polar on the area ``AREA``; the wing limit is ``CL_MAX``.

    Below ``zero_lift_floor`` the zero-lift point does not exist (the adapter's low-Reynolds-number case).
    """

    def __init__(
        self,
        cd0: float = CD0,
        warnings: tuple[KernelWarning, ...] = (),
        zero_lift_floor: float = 0.0,
    ) -> None:
        super().__init__()
        self.cd0, self.warnings, self.zero_lift_floor = cd0, warnings, zero_lift_floor
        self.evaluations: list[tuple[float, float]] = []

    async def level_flight_point(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        air: AirState,
        v_ms: float,
        n_load: float,
    ) -> LevelFlightPoint:
        self.evaluations.append((v_ms, n_load))
        q_s = 0.5 * air.density * v_ms**2 * AREA
        cl = n_load * mass_kg * gravity / q_s
        if cl > CL_MAX or (n_load == 0.0 and v_ms < self.zero_lift_floor):
            raise FormulaError(
                ErrorCategory.NOT_CONVERGED,
                "not_converged",
                f"the airplane does not reach C_L = {cl:.4g} below its first C_L peak",
                "check mass and speed",
                detail={"limit": "wing_lift", "v_ms": v_ms},
            )
        cd = self.cd0 + K * cl * cl
        point = LevelPoint(
            v_ms=v_ms, alpha_deg=cl / 0.1, cl=cl, cd=cd, lift_n=cl * q_s, drag_n=cd * q_s
        )
        return LevelFlightPoint(point=point, warnings=self.warnings)


def limits(ctx: Context) -> list[str]:
    """The ``limit`` of every ``powered_limit_declared`` notice of the context."""
    return [str(w.detail["limit"]) for w in ctx.warnings if w.code == "powered_limit_declared"]


def context(slug: str, opti: PolarOpti | None = None) -> Context:
    """The context of a formula with the relations of its canon ``embeds`` and the stub airplane."""
    formula = shipped_build().model.formula(slug)
    assert formula is not None
    relations = {item: DEFAULT_REGISTRY.relation_of(item.split(".")[0]) for item in formula.embeds}
    return Context(
        origin="t",
        solvers=solvers_with(opti=opti or PolarOpti()),
        relations={k: v for k, v in relations.items() if v is not None},
    )


def bound_inputs(slug: str, mass: float = 3.4, n_lim: float = 6.0, **extra: Any) -> dict[str, Any]:
    """``x`` of a formula built from the model: the AT2814 on 14.8 V with the APC 13x8E table."""
    by_quantity: dict[str, Any] = {
        "airplane": AirplaneGeometry.model_validate(airplane_document()),
        "aircraft-mass": mass,
        "gravity": G,
        "air-density": RHO,
        "dynamic-viscosity": MU,
        "speed-of-sound": SOUND,
        "limit-load-factor": n_lim,
        "components": complete_components_with_table(),
        "motor-voltage-constant": KV,
        "motor-no-load-current": I0,
        "motor-circuit-resistance": RM,
        "battery-voltage": U_BAT,
        "motor-max-power": 650.0,
        "propeller-diameter": reference.D_PROP,
        "motor-efficiency": 0.8,
    }
    by_quantity.update(extra)
    model = shipped_build().model
    formula = model.formula(slug)
    assert formula is not None
    wanted = set(formula.application("default").bind.values())
    chosen = {k: v for k, v in by_quantity.items() if f"calc:{k}" in wanted}
    return inputs_from_model(model, slug, chosen)


# --- the independent solution ---------------------------------------------------------------------


TABLE_EDGE_MS = (
    33.0  # above it the bracket of the independent balance leaves the APC table (J > 0.75)
)


@functools.cache
def thrust(v: float) -> float:
    """Full-throttle thrust in N at ``v`` below ``TABLE_EDGE_MS``: the independent torque balance.

    The balance of ``powertrain_reference`` bisects from 1000 rpm, where the advance ratio leaves the table
    at 30 m/s; here the bracket starts at 8000 rpm (the balance lies between 8500 and 9300 rpm for 0 to
    35 m/s), which stays inside the table up to ``TABLE_EDGE_MS``.
    """
    low, high = 8000.0, reference.KV * reference.U_BAT
    rpm = 0.5 * (low + high)
    for _ in range(reference.ITERATIONS):
        rpm = 0.5 * (low + high)
        n = rpm / 60
        _, c_p = reference.coefficients(rpm, v / (n * reference.D_PROP))
        q_p = c_p * RHO * n**2 * reference.D_PROP**5 / (2 * math.pi)
        q_m = ((U_BAT - 2 * math.pi * n / reference.KV_RAD) / RM - I0) / reference.KV_RAD
        if q_m - q_p > 0:
            low = rpm
        else:
            high = rpm
    n = rpm / 60
    c_t, _ = reference.coefficients(rpm, v / (n * reference.D_PROP))
    return c_t * RHO * n**2 * reference.D_PROP**4


def drag(v: float, n: float, mass: float, cd0: float = CD0) -> float | None:
    """The polar's drag in N at speed ``v`` and load factor ``n``; ``None`` beyond ``CL_MAX``."""
    q_s = 0.5 * RHO * v * v * AREA
    cl = n * mass * G / q_s
    return None if cl > CL_MAX else q_s * (cd0 + K * cl * cl)


def bisect(f: Any, low: float, high: float) -> float:
    """The root of ``f`` on ``[low, high]`` with ``f(low) > 0 >= f(high)``, by 80 bisections."""
    for _ in range(80):
        middle = 0.5 * (low + high)
        if f(middle) > 0.0:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def max_level_speed(mass: float, cd0: float = CD0) -> float:
    """The highest root of ``T - D`` on a 0.01 m/s grid, refined by bisection."""
    best = None
    v = 5.0
    while v < TABLE_EDGE_MS:
        d = drag(v, 1.0, mass, cd0)
        if d is not None and thrust(v) - d > 0.0:
            best = v
        v += 0.25
    assert best is not None

    def excess(speed: float) -> float:
        d = drag(speed, 1.0, mass, cd0)
        assert d is not None
        return thrust(speed) - d

    return bisect(excess, best, best + 0.25)


def climb_angle(v: float, mass: float) -> float | None:
    """The steepest steady climb angle in rad at ``v``, by bisection on ``T - D(cos g) - m g sin g``.

    The wing carries the lift ``m g cos(g)`` only for ``cos(g) <= n_w = C_L,max q S / W`` (closed form of the
    polar), so the angles start at ``acos(min(1, n_w))``.
    """
    weight, q_s = mass * G, 0.5 * RHO * v * v * AREA
    gamma_wing = math.acos(min(1.0, CL_MAX * q_s / weight)) + 1e-9

    def excess(gamma: float) -> float:
        d = drag(v, math.cos(gamma), mass)
        assert d is not None
        return thrust(v) - d - weight * math.sin(gamma)

    if excess(0.5 * math.pi) >= 0.0:
        return 0.5 * math.pi
    if excess(gamma_wing) < 0.0:
        return None
    return bisect(excess, gamma_wing, 0.5 * math.pi)


def sustained_n(v: float, mass: float, n_lim: float, cd0: float = CD0) -> tuple[float, str] | None:
    """The highest sustained load factor at ``v`` and its limit, in closed form from the polar."""
    weight, q_s = mass * G, 0.5 * RHO * v * v * AREA
    level = drag(v, 1.0, mass, cd0)
    if level is None or thrust(v) < level:
        return None
    n_thrust = math.sqrt(max((thrust(v) / q_s - cd0) / K, 0.0)) * q_s / weight
    n_wing = CL_MAX * q_s / weight
    n = min(n_lim, n_thrust, n_wing)
    limit = "structure" if n == n_lim else ("thrust" if n == n_thrust else "wing")
    return n, limit
