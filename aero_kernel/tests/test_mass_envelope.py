"""``mass-envelope`` against an independent solution (gh-1420, fast tier).

AeroBuildup is the stub of ``powered_builders`` (a parabolic polar ``C_D = C_D0 + 0.06 C_L^2``, ``C_L,max =
1.2``, ``S = 0.5 m^2``) with a draggy ``C_D0 = 0.4``, so that the airplane stops flying inside the scan of the
mass; the stall solve is the closed form ``V_S = sqrt(2 m g / (rho S C_L,max))`` with a lift curve whose first
peak is the stall. The drive train is the AT2814 on 14.8 V with the published APC 13x8E table, its thrust the
plain-Python balance of ``powertrain_reference``. The expectations are written here without the kernel's
searches: a fine grid of the speed for the best excess thrust, bisection over the mass. The hand check: at
``m_max,level`` the full-throttle thrust equals the level-flight drag at the best speed and no climb is left.
"""

import math
from collections.abc import Callable
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.config import config
from aero_kernel.context import Context
from aero_kernel.errors import FormulaError
from aero_kernel.formulas import mass_envelope as module
from aero_kernel.formulas.best_rate_of_climb import best_rate_of_climb
from aero_kernel.formulas.mass_envelope import (
    Envelope,
    mass_envelope,
    takeoff_speed_above_stall_speed,
)
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import Curve, CurvePair, KernelWarning
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import LevelFlightPoint, Stall, StallSolution
from aero_kernel.tests import powered_builders as pb
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.stall_stubs import UPRIGHT_PEAK, lift_curve
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

M0 = 3.4
CD0 = 0.4  # draggy: the best excess thrust vanishes near 6.4 kg
RESERVE = 1.3
STUB_NOTICE = KernelWarning.of("induced_drag_viscous_factor_removed", "the stub's drag notice")
CURVE_POINTS = 6  # config: mass_envelope_curve_points


def v_stall(mass: float) -> float:
    """The stub's closed-form stall speed in m/s."""
    return math.sqrt(2.0 * mass * pb.G / (pb.RHO * pb.AREA * pb.CL_MAX))


class EnvelopeOpti(pb.PolarOpti):
    """The polar stub with a stall solve of the same polar, and a record of the airplanes it saw."""

    def __init__(self, cd0: float = CD0, *, stall_alpha: float = UPRIGHT_PEAK[0], **kwargs: Any):
        super().__init__(cd0=cd0, **kwargs)
        self.stall_alpha = stall_alpha
        self.stall_airplanes: list[AirplaneGeometry] = []
        self.level_airplanes: list[AirplaneGeometry] = []

    async def level_flight_point(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        air: AirState,
        v_ms: float,
        n_load: float,
    ) -> LevelFlightPoint:
        self.level_airplanes.append(airplane)
        return await super().level_flight_point(airplane, mass_kg, gravity, air, v_ms, n_load)

    async def stall(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        n_load: float,
        air: AirState,
    ) -> Stall:
        self.stall_airplanes.append(airplane)
        solution = StallSolution(
            v_s=v_stall(mass_kg),
            cl_max=pb.CL_MAX,
            alpha_s=self.stall_alpha,
            polar=lift_curve((UPRIGHT_PEAK[0], pb.CL_MAX), True),
        )
        return Stall(solution=solution, warnings=())


def inputs(mass: float = M0, **extra: Any) -> dict[str, Any]:
    """``x`` of ``mass-envelope``: the AT2814 on 14.8 V, the take-off reserve of the current mass."""
    values: dict[str, Any] = {
        "stall-speed-takeoff": v_stall(mass),
        "takeoff-speed": RESERVE * v_stall(mass),
        "airplane-takeoff": AirplaneGeometry.model_validate(airplane_document()),
    }
    values.update(extra)
    return pb.bound_inputs("mass-envelope", mass, **values)


async def run(
    opti: EnvelopeOpti | None = None, mass: float = M0, **extra: Any
) -> tuple[dict[str, Any], Context]:
    ctx = pb.context("mass-envelope", opti or EnvelopeOpti())
    return await mass_envelope(inputs(mass, **extra), ctx), ctx


# --- the independent solution ---------------------------------------------------------------------


def best_excess(mass: float, cd0: float = CD0) -> tuple[float, float]:
    """The largest ``T - D`` in level flight and its speed: a grid of 0.05 m/s from 5 to 33 m/s, and the
    stall corner itself (a draggy polar has its drag falling up to the stall, so the best excess lies there)."""
    best = (-math.inf, 0.0)
    for v in [5.0 + 0.05 * k for k in range(560)] + [v_stall(mass) * (1.0 + 1e-7)]:
        drag = pb.drag(v, 1.0, mass, cd0)
        if drag is not None:
            best = max(best, (pb.thrust(v) - drag, v))
    return best


def takeoff_excess(mass: float, cd0: float = CD0) -> float:
    """``T - D`` at ``V_TO(m) = 1.3 V_S(m)`` in level flight."""
    v = RESERVE * v_stall(mass)
    drag = pb.drag(v, 1.0, mass, cd0)
    assert drag is not None
    return pb.thrust(v) - drag


def root_over_mass(f: Callable[[float], float], low: float, high: float) -> float:
    """The mass where ``f`` changes from positive to not positive on ``[low, high]``."""
    return pb.bisect(f, low, high)


def climb_angle(v: float, mass: float) -> float | None:
    """The steepest steady climb angle in rad at ``v`` (bisection on ``T - D(cos g) - m g sin g``), or ``None``.

    ``pb.climb_angle`` is the one of the stub's default polar; this is the same bisection for ``CD0``.
    """
    weight, q_s = mass * pb.G, 0.5 * pb.RHO * v * v * pb.AREA
    gamma_wing = math.acos(min(1.0, pb.CL_MAX * q_s / weight)) + 1e-9

    def excess(gamma: float) -> float:
        d = pb.drag(v, math.cos(gamma), mass, CD0)
        assert d is not None
        return pb.thrust(v) - d - weight * math.sin(gamma)

    if excess(0.5 * math.pi) >= 0.0:
        return 0.5 * math.pi
    if excess(gamma_wing) < 0.0:
        return None
    return pb.bisect(excess, gamma_wing, 0.5 * math.pi)


def best_climb_rate(mass: float) -> float:
    """The largest ``V sin(gamma)``: a grid of 0.1 m/s from 5 to 33 m/s, then 0.002 m/s around the best.

    The best climb can lie on the edge of the speeds that have one (below the level stall speed), where a
    coarse grid undershoots.
    """

    def rate(v: float) -> float:
        gamma = climb_angle(v, mass)
        return 0.0 if gamma is None else v * math.sin(gamma)

    best_v = max((5.0 + 0.1 * k for k in range(280)), key=rate)
    return max(rate(best_v - 0.1 + 0.002 * k) for k in range(101))


def level_root() -> float:
    return root_over_mass(lambda m: best_excess(m)[0], M0, 8.0)


def takeoff_root() -> float:
    return root_over_mass(takeoff_excess, M0, 8.0)


# --- the two largest masses -------------------------------------------------------------------------


async def test_the_largest_level_flight_mass_is_the_root_of_the_best_excess_thrust() -> None:
    got, _ = await run()
    expected = level_root()
    assert 5.0 < expected < 8.0  # the brute force closes inside the scan (1.3^12 x 3.4 kg)
    assert close(got["m_max_level"], expected, 1e-3)


async def test_at_the_largest_level_mass_thrust_equals_drag_and_no_climb_is_left() -> None:
    """The hand check: ``T = D`` at the best speed, so the climb angle and the rate of climb vanish."""
    got, _ = await run()
    mass = got["m_max_level"]
    excess, v_best = best_excess(mass)
    assert abs(excess) < 1e-3  # N: thrust equals drag at the best speed
    drag = pb.drag(v_best, 1.0, mass, CD0)
    assert drag is not None
    assert close(pb.thrust(v_best), drag, 1e-3)
    assert best_climb_rate(mass * 1.001) == 0.0  # slightly heavier: nowhere to climb
    assert best_climb_rate(mass * 0.999) < 0.1  # slightly lighter: m/s, almost nothing


async def test_the_largest_lift_off_mass_is_the_root_of_the_excess_at_the_lift_off_speed() -> None:
    got, _ = await run()
    expected = takeoff_root()
    assert close(got["m_max_to"], expected, 1e-3)
    assert (
        got["m_max_to"] < got["m_max_level"]
    )  # the overloaded bomber: it cruises, it cannot climb out
    assert abs(takeoff_excess(got["m_max_to"])) < 1e-2  # N


# --- the curves ------------------------------------------------------------------------------------


async def test_the_curves_are_the_stall_the_level_speed_and_the_climb_over_the_masses_of_the_scan() -> (
    None
):
    got, _ = await run()
    pair, climb = got["speed_range"], got["roc_curve"]
    assert isinstance(pair, CurvePair)
    assert isinstance(climb, Curve)
    masses = pair.x
    assert masses[0] == M0
    assert len(masses) == CURVE_POINTS + 1  # equally spaced from the current mass, then the root
    assert close(masses[1], M0 + (got["m_max_level"] - M0) / CURVE_POINTS, 1e-12)
    assert masses[-1] == got["m_max_level"]
    assert climb.x == masses
    assert close(pair.lower[0], v_stall(M0), 1e-9)
    for k, mass in enumerate(masses[:-1]):  # every scan mass against the brute force
        assert close(pair.lower[k], v_stall(mass), 1e-9)
        assert close(pair.upper[k], pb.max_level_speed(mass, CD0), 1e-4)
        assert close(climb.y[k], best_climb_rate(mass), 5e-3)
    assert list(pair.lower) == sorted(pair.lower)  # the stall speed rises with the mass
    assert climb.y[0] > climb.y[1] > 0.0  # the climb falls with the mass ...
    assert climb.y[-1] == 0.0  # ... and is zero where level flight ends
    assert (
        pair.upper[-1] > pair.lower[-1]
    )  # the range has closed to the best speed, above the stall
    assert close(pair.upper[-1], best_excess(masses[-1])[1], 1e-3)


# --- warnings, embedding, configuration ------------------------------------------------------------


async def test_only_the_warnings_of_the_two_answers_are_forwarded_and_the_route_is_declared_once() -> (
    None
):
    opti = EnvelopeOpti(warnings=(STUB_NOTICE,))
    _, ctx = await run(opti)
    codes = [w.code for w in ctx.warnings]
    assert len(opti.evaluations) > 100  # many evaluations along the searches
    assert codes.count("induced_drag_viscous_factor_removed") == 2  # level answer, take-off answer
    assert codes.count("powertrain_route_winding_resistance") == 1
    assert pb.limits(ctx) == ["wing"]  # the draggy polar's best excess is at the stall corner


async def test_the_embedded_relations_requested_are_those_of_the_canon_that_exist() -> None:
    _, ctx = await run()
    formula = shipped_build().model.formula("mass-envelope")
    assert formula is not None
    relations = {i for i in formula.embeds if DEFAULT_REGISTRY.relation_of(i.split(".")[0])}
    assert set(ctx.embedded_requests) == relations
    assert len(relations) == 4  # the optimisations (stall, level speed, climb) are shared functions


async def test_the_take_off_stall_and_drag_are_solved_on_the_take_off_configuration() -> None:
    takeoff = AirplaneGeometry.model_validate(airplane_document())
    opti = EnvelopeOpti()
    swapped: dict[str, Any] = {"airplane-takeoff": takeoff}
    await run(opti, **swapped)
    assert any(a is takeoff for a in opti.stall_airplanes)  # the take-off stall solves
    assert any(a is takeoff for a in opti.level_airplanes)  # the take-off drag
    assert any(a is not takeoff for a in opti.stall_airplanes)  # the clean stall of the curves
    assert any(a is not takeoff for a in opti.level_airplanes)  # the clean level flight


# --- the declared failures -------------------------------------------------------------------------


async def test_a_current_mass_above_the_level_flight_limit_is_a_declared_failure() -> None:
    with pytest.raises(FormulaError) as caught:
        await run(mass=7.5)
    assert caught.value.code == "no_feasible_speed"
    assert "level flight is not held at the current mass of 7.5 kg" in caught.value.message


async def test_a_current_mass_that_cannot_climb_out_is_a_declared_failure() -> None:
    mass = 0.5 * (takeoff_root() + level_root())  # flies level, cannot lift off
    with pytest.raises(FormulaError) as caught:
        await run(mass=mass)
    assert caught.value.code == "no_feasible_speed"
    assert "the lift-off is not held at the current mass" in caught.value.message


async def test_a_state_still_held_at_the_end_of_the_scan_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = config()
    short = real.mass_envelope_max_steps.model_copy(update={"value": 2.0})
    patched = real.model_copy(update={"mass_envelope_max_steps": short})
    monkeypatch.setattr(module, "config", lambda: patched)  # 1.3^2 x 3.4 kg = 5.7 kg < 6.3 kg
    with pytest.raises(FormulaError) as caught:
        await run()
    assert caught.value.code == "not_converged"
    assert "still held" in caught.value.message
    assert caught.value.detail["steps"] == 2


async def test_a_stall_off_the_first_lift_peak_is_the_embedded_check_failing() -> None:
    with pytest.raises(FormulaError) as caught:
        await run(EnvelopeOpti(stall_alpha=5.0))
    assert caught.value.code == "postcondition_violated"
    assert caught.value.detail["embedded"] == "stall-speed.takeoff"
    assert caught.value.detail["mass_kg"] == M0


async def test_an_absent_winding_resistance_is_missing_input() -> None:
    absent: dict[str, Any] = {"motor-circuit-resistance": None}
    with pytest.raises(FormulaError) as caught:
        await run(**absent)
    assert caught.value.code == "missing_input"


# --- the precondition ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("v_s_to", "v_to", "state"),
    [
        (10.0, 13.0, "held"),
        (10.0, 10.0, "violated"),
        (10.0, 8.0, "violated"),
        (0.0, 5.0, "violated"),
    ],
)
async def test_the_take_off_speed_must_exceed_the_stall_speed_above_zero(
    v_s_to: float, v_to: float, state: str
) -> None:
    result = takeoff_speed_above_stall_speed({"v_s_to": v_s_to, "v_to": v_to})
    assert result.state == state


async def test_the_precondition_is_the_one_the_canon_binds_to_the_take_off_speed() -> None:
    formula = shipped_build().model.formula("mass-envelope")
    assert formula is not None
    assert [(c.id, c.parameter) for c in formula.preconditions] == [
        ("takeoff_speed_above_stall_speed", "v_to")
    ]
    assert DEFAULT_REGISTRY.checks("mass-envelope", "pre") == {
        "takeoff_speed_above_stall_speed": takeoff_speed_above_stall_speed
    }


# --- the window searches against the formulas they stand in for -------------------------------------


async def test_the_window_searches_agree_with_the_scans_of_max_level_speed_and_best_rate_of_climb() -> (
    None
):
    """Where the scans of the two formulas work (a polar with room for the level flight) the window
    searches of the sweep, started from the best excess, find the same ``V_max`` and ``ROC_max``."""
    ctx = pb.context("mass-envelope", EnvelopeOpti(cd0=pb.CD0))
    sweep = Envelope(inputs(), ctx)
    flight, best = await sweep.best_excess(M0)
    v_max = await sweep.level_speed_above(flight, best.v)
    climb = await sweep.climb_rate(flight, best.v, v_max)
    level = await max_level_speed(
        pb.bound_inputs("max-level-speed"), pb.context("max-level-speed", pb.PolarOpti())
    )
    rate = await best_rate_of_climb(
        pb.bound_inputs("best-rate-of-climb"), pb.context("best-rate-of-climb", pb.PolarOpti())
    )
    assert close(v_max, level["v_max"], 1e-4)
    assert close(climb, rate["roc_max"], 1e-3)
    assert best.v < v_max  # the best excess lies below the highest level speed


async def test_a_level_speed_still_above_the_drag_at_the_scan_limit_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = config()
    low_limit = real.powered_speed_scan_limit.model_copy(update={"value": 12.0})
    patched = real.model_copy(update={"powered_speed_scan_limit": low_limit})
    monkeypatch.setattr(module, "config", lambda: patched)
    with pytest.raises(FormulaError) as caught:
        await run()
    assert caught.value.code == "not_converged"
    assert "level-flight excess thrust" in caught.value.message


async def test_an_airplane_that_is_not_the_geometry_is_a_type_error() -> None:
    swapped: dict[str, Any] = {"airplane-takeoff": 1.0}
    sweep = Envelope(inputs(**swapped), pb.context("mass-envelope", EnvelopeOpti()))
    with pytest.raises(TypeError):
        sweep.airplane(takeoff=True)
