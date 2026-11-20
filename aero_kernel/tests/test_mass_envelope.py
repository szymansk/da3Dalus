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
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas import mass_envelope as module
from aero_kernel.formulas.best_rate_of_climb import best_rate_of_climb
from aero_kernel.formulas.mass_envelope import (
    LEVEL_NOT_HELD,
    TAKEOFF_NOT_HELD,
    Envelope,
    current_mass_positive,
    mass_envelope,
    takeoff_speed_above_stall_speed,
)
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import Curve, KernelWarning
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
CURVE_POINTS = 3  # the curve tests patch mass_envelope_curve_points to this (see `few_points`)
STUB_NOTICE = KernelWarning.of("induced_drag_viscous_factor_removed", "the stub's drag notice")


def failure(code: str, message: str) -> FormulaError:
    """A formula error of the category its code belongs to."""
    category = (
        ErrorCategory.NOT_CONVERGED
        if code == "not_converged"
        else ErrorCategory.UNSUPPORTED_CONFIGURATION
    )
    return FormulaError(category, code, message, "a hint")


def v_stall(mass: float) -> float:
    """The stub's closed-form stall speed in m/s."""
    return math.sqrt(2.0 * mass * pb.G / (pb.RHO * pb.AREA * pb.CL_MAX))


class EnvelopeOpti(pb.PolarOpti):
    """The polar stub with a stall solve of the same polar, and a record of the airplanes it saw."""

    def __init__(
        self,
        cd0: float = CD0,
        *,
        stall_alpha: float = UPRIGHT_PEAK[0],
        stall_fails_above: float = math.inf,
        stall_scale: float = 1.0,
        lift_cap_mass: float = math.inf,
        stall_warning_above: float = math.inf,
        **kwargs: Any,
    ):
        super().__init__(cd0=cd0, **kwargs)
        self.stall_alpha = stall_alpha
        self.stall_fails_above = stall_fails_above
        self.stall_scale = stall_scale
        self.lift_cap_mass = lift_cap_mass
        self.stall_warning_above = stall_warning_above
        self.stall_masses: list[float] = []
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
        if (
            mass_kg > self.lift_cap_mass
        ):  # the data end: the wing cannot carry this mass at any speed
            raise FormulaError(
                ErrorCategory.NOT_CONVERGED,
                "not_converged",
                f"the airplane does not reach the lift of {mass_kg:.4g} kg below its first C_L peak",
                "check mass and speed",
                detail={"limit": "wing_lift", "v_ms": v_ms},
            )
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
        self.stall_masses.append(mass_kg)
        if mass_kg > self.stall_fails_above:
            raise failure(
                "not_converged", "the optimum of the stall problem lies on the bound of alpha"
            )
        solution = StallSolution(
            v_s=v_stall(mass_kg) * self.stall_scale,
            cl_max=pb.CL_MAX,
            alpha_s=self.stall_alpha,
            polar=lift_curve((UPRIGHT_PEAK[0], pb.CL_MAX), True),
        )
        regime = (
            (
                KernelWarning.of(
                    "reynolds_outside_band",
                    "the stub's chord Reynolds number is low",
                    detail={"re": 3.0e4},
                ),
            )
            if mass_kg > self.stall_warning_above
            else ()
        )
        return Stall(solution=solution, warnings=regime)


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


def climb_angle(v: float, mass: float, cd0: float = CD0) -> float | None:
    """The steepest steady climb angle in rad at ``v`` (bisection on ``T - D(cos g) - m g sin g``), or ``None``.

    ``pb.climb_angle`` is the one of the stub's default polar; this is the same bisection for ``CD0``.
    """
    weight, q_s = mass * pb.G, 0.5 * pb.RHO * v * v * pb.AREA
    gamma_wing = math.acos(min(1.0, pb.CL_MAX * q_s / weight)) + 1e-9

    def excess(gamma: float) -> float:
        d = pb.drag(v, math.cos(gamma), mass, cd0)
        assert d is not None
        return pb.thrust(v) - d - weight * math.sin(gamma)

    if excess(0.5 * math.pi) >= 0.0:
        return 0.5 * math.pi
    if excess(gamma_wing) < 0.0:
        return None
    return pb.bisect(excess, gamma_wing, 0.5 * math.pi)


def best_climb_rate(mass: float, cd0: float = CD0) -> float:
    """The largest ``V sin(gamma)``: a grid of 0.1 m/s from 5 to 33 m/s, then 0.002 m/s around the best.

    The best climb can lie on the edge of the speeds that have one (below the level stall speed), where a
    coarse grid undershoots.
    """

    def rate(v: float) -> float:
        gamma = climb_angle(v, mass, cd0)
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


# --- warnings, embedding, configuration ------------------------------------------------------------


async def test_only_the_warnings_of_the_two_answers_are_forwarded_and_the_route_is_declared_once() -> (
    None
):
    opti = EnvelopeOpti(warnings=(STUB_NOTICE,))
    _, ctx = await run(opti)
    codes = [w.code for w in ctx.warnings]
    assert len(opti.evaluations) > 100  # many evaluations along the searches
    # the level answer, the take-off answer, and the one summary of the curve samples (ADR 0020)
    assert codes.count("induced_drag_viscous_factor_removed") == 3
    assert codes.count("powertrain_route_winding_resistance") == 1
    # the scan starts at the stall speed, so the stall corner is its first point: no wing notice; the
    # samples' climb scans declare their floor start (one summary)
    assert "wing" not in pb.limits(ctx)


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
    assert any(
        a is not takeoff for a in opti.stall_airplanes
    )  # the clean stall starts the speed scan
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
    assert caught.value.detail["embedded"] == "stall-speed.clean"  # the level problem solves first
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


@pytest.mark.parametrize(
    ("mass", "state"),
    [
        (3.4, "held"),
        (0.0, "violated"),
        (-1.0, "violated"),
        (math.inf, "violated"),
        (math.nan, "violated"),
    ],
)
async def test_the_current_mass_must_be_a_finite_number_above_zero(mass: float, state: str) -> None:
    assert current_mass_positive({"m_current": mass}).state == state


async def test_the_preconditions_are_the_ones_the_canon_binds() -> None:
    formula = shipped_build().model.formula("mass-envelope")
    assert formula is not None
    assert [(c.id, c.parameter) for c in formula.preconditions] == [
        ("takeoff_speed_above_stall_speed", "v_to"),
        ("current_mass_positive", "m_current"),
    ]
    assert DEFAULT_REGISTRY.checks("mass-envelope", "pre") == {
        "takeoff_speed_above_stall_speed": takeoff_speed_above_stall_speed,
        "current_mass_positive": current_mass_positive,
    }


# --- the type of the airplane ---


async def test_an_airplane_that_is_not_the_geometry_is_a_type_error() -> None:
    swapped: dict[str, Any] = {"airplane-takeoff": 1.0}
    sweep = Envelope(inputs(**swapped), pb.context("mass-envelope", EnvelopeOpti()))
    with pytest.raises(TypeError):
        sweep.airplane(takeoff=True)


# --- what closes the bracket, and what does not ----------------------------------------------------------


def scan() -> Envelope:
    """An ``Envelope`` at 3.4 kg (the scan masses are 3.4, 4.42, 5.75, 7.47, 9.71 kg, ...)."""
    return Envelope(inputs(), pb.context("mass-envelope", EnvelopeOpti()))


def with_edge(edge: float, level: float, code: str) -> Callable[[float], Any]:
    """``f(m) = level - m``, which cannot be evaluated above ``edge`` (the failure ``code``)."""

    async def f(mass: float) -> float:
        if mass > edge:
            raise failure(code, "the data end here")
        return level - mass

    return f


@pytest.mark.parametrize(
    ("code", "not_held"),
    [("no_feasible_speed", LEVEL_NOT_HELD), ("outside_propeller_table", TAKEOFF_NOT_HELD)],
)
async def test_where_the_data_end_with_the_state_still_held_the_last_mass_that_evaluates_is_the_answer(
    code: str, not_held: frozenset[str]
) -> None:
    sweep = scan()
    got, edge = await sweep.root(with_edge(8.0, 10.0, code), "level flight", not_held)
    assert edge  # the root is the edge of the data, not a sign change
    assert close(got, 8.0, 2e-5)  # the edge, bisected to mass_envelope_edge_tolerance
    assert got <= 8.0  # the last mass that evaluates
    declared = [w for w in sweep.ctx.warnings if w.code == "powered_limit_declared"]
    assert [w.detail["limit"] for w in declared] == ["evaluation_edge"]
    assert "the data end here" in declared[0].message
    assert declared[0].detail["mass_kg"] == got


@pytest.mark.parametrize(
    ("code", "not_held"),
    [("no_feasible_speed", LEVEL_NOT_HELD), ("outside_propeller_table", TAKEOFF_NOT_HELD)],
)
async def test_a_sign_change_below_the_edge_is_refined_as_a_root(
    code: str, not_held: frozenset[str]
) -> None:
    sweep = scan()
    got, edge = await sweep.root(
        with_edge(8.0, 7.7, code), "level flight", not_held
    )  # f(7.47) > 0 > f(8.0)
    assert not edge
    assert close(got, 7.7, 1e-4)
    assert not [w for w in sweep.ctx.warnings if w.code == "powered_limit_declared"]


@pytest.mark.parametrize(
    ("code", "other"),
    [
        ("outside_propeller_table", LEVEL_NOT_HELD),  # not the level problem's "not held"
        ("no_feasible_speed", TAKEOFF_NOT_HELD),  # not the lift-off problem's "not held"
        ("not_converged", LEVEL_NOT_HELD),
        ("not_converged", TAKEOFF_NOT_HELD),
    ],
)
async def test_every_other_failure_surfaces_with_the_mass_named(
    code: str, other: frozenset[str]
) -> None:
    with pytest.raises(FormulaError) as caught:
        await scan().root(with_edge(5.0, 10.0, code), "level flight", other)
    assert caught.value.code == code
    assert "at the mass 5.746 kg:" in caught.value.message  # the first scan mass above the edge
    assert close(float(str(caught.value.detail["mass_kg"])), 5.746, 1e-3)
    assert caught.value.hint == "a hint"


async def test_a_failure_at_the_current_mass_is_never_the_data_end() -> None:
    with pytest.raises(FormulaError) as caught:
        await scan().root(with_edge(1.0, 10.0, "no_feasible_speed"), "level flight", LEVEL_NOT_HELD)
    assert caught.value.code == "no_feasible_speed"
    assert "at the mass 3.4 kg:" in caught.value.message


async def test_an_edge_search_that_does_not_narrow_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = config()
    short = real.powered_search_max_steps.model_copy(update={"value": 2.0})
    monkeypatch.setattr(
        module, "config", lambda: real.model_copy(update={"powered_search_max_steps": short})
    )
    with pytest.raises(FormulaError) as caught:
        await scan().root(with_edge(8.0, 10.0, "no_feasible_speed"), "level flight", LEVEL_NOT_HELD)
    assert caught.value.code == "not_converged"
    assert caught.value.detail["steps"] == 2


async def test_a_stall_solve_that_fails_above_the_current_mass_surfaces_with_the_mass() -> None:
    """The defect of bug #1423 (a stall solve that does not converge) is not "not held"."""
    with pytest.raises(FormulaError) as caught:
        await run(EnvelopeOpti(stall_fails_above=4.0))
    assert caught.value.code == "not_converged"
    assert "at the mass 4.42 kg:" in caught.value.message
    assert "bound of alpha" in caught.value.message
    assert close(float(str(caught.value.detail["mass_kg"])), 4.42, 1e-3)


async def test_a_best_excess_at_the_stall_corner_above_a_skipped_speed_is_declared() -> None:
    """A stall speed below the speed the wing can fly (here 0.8 of it) leaves speeds to skip; the best excess
    lies at the corner above them and the notice says the wing, not the thrust, ends the speed range."""
    got, ctx = await run(EnvelopeOpti(stall_scale=0.8))
    assert close(
        got["m_max_level"], level_root(), 1e-3
    )  # the same root: the skipped speeds carry no value
    assert pb.limits(ctx)[0] == "wing"  # the level answer's; the samples' summary follows


@pytest.fixture(autouse=True)
def few_points(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three curve samples: the draggy stub's speeds with an excess are narrow near its root, and a sample
    within a few percent of it is narrower than the 2 m/s scan step of the two formulas (declared limit)."""
    real = config()
    few = real.mass_envelope_curve_points.model_copy(update={"value": float(CURVE_POINTS)})
    patched = real.model_copy(update={"mass_envelope_curve_points": few})
    monkeypatch.setattr(module, "config", lambda: patched)


# --- the curves: one producer ----------------------------------------------------------------------------


async def test_the_curve_samples_are_what_max_level_speed_and_best_rate_of_climb_return_at_that_mass() -> (
    None
):
    """One producer (ADR 0022): at every sample mass the curves hold exactly the value the two formulas
    return for that mass and its clean stall speed: same functions, same scan grid and start, no second
    search. Equality, not agreement."""
    got, _ = await run()
    _, level_curve = got["speed_range"]
    climb = got["roc_curve"]
    assert isinstance(level_curve, Curve)
    assert isinstance(climb, Curve)
    for k, mass in enumerate(level_curve.x[:-1]):
        values: dict[str, Any] = {"stall-speed": v_stall(mass)}
        level = await max_level_speed(
            pb.bound_inputs("max-level-speed", mass, **values),
            pb.context("max-level-speed", EnvelopeOpti()),
        )
        rate = await best_rate_of_climb(
            pb.bound_inputs("best-rate-of-climb", mass, **values),
            pb.context("best-rate-of-climb", EnvelopeOpti()),
        )
        assert level_curve.y[k] == level["v_max"]
        assert climb.y[k] == rate["roc_max"]


async def test_the_curves_run_from_the_current_mass_to_the_largest_level_mass_and_close_there() -> (
    None
):
    got, _ = await run()
    stall_curve, level_curve = got["speed_range"]
    climb = got["roc_curve"]
    root = got["m_max_level"]
    assert len(stall_curve.x) == CURVE_POINTS + 1
    assert stall_curve.x == level_curve.x == climb.x  # the speed range is two curves over one grid
    assert stall_curve.x[0] == M0
    assert stall_curve.x[-1] == root
    for k, mass in enumerate(stall_curve.x[:-1]):  # equally spaced from the current mass
        assert close(mass, M0 + (root - M0) * k / CURVE_POINTS, 1e-12)
    for k, mass in enumerate(stall_curve.x):
        assert close(stall_curve.y[k], v_stall(mass), 1e-9)  # the stall solve of each mass
    assert list(stall_curve.y) == sorted(stall_curve.y)  # V_S rises with the mass
    assert climb.y[0] > climb.y[1] > climb.y[-2] > 0.0  # the climb falls with the mass ...
    assert climb.y[-1] == 0.0  # ... and is zero where level flight ends
    assert close(level_curve.y[-1], best_excess(root)[1], 1e-3)  # V_max closes on the best speed


async def test_a_sample_whose_search_fails_surfaces_with_its_mass_named() -> None:
    """A curve sample is not "not held": its failure surfaces (here: the climb scan finds no speed)."""
    with pytest.raises(FormulaError) as caught:
        await run(EnvelopeOpti(stall_fails_above=5.0))  # the stall solve of a sample mass fails
    assert caught.value.code == "not_converged"
    assert "at the mass" in caught.value.message


async def test_a_sample_in_a_window_narrower_than_the_scan_step_fails_with_its_mass_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The declared limit of one producer: with six samples the last lies 7 percent below the root of the
    draggy stub, where the speeds with an excess are narrower than the 2 m/s step of the scan the two
    formulas share. The formula says so, with the mass, instead of skipping the point or searching again."""
    real = config()
    six = real.mass_envelope_curve_points.model_copy(update={"value": 6.0})
    patched = real.model_copy(update={"mass_envelope_curve_points": six})
    monkeypatch.setattr(module, "config", lambda: patched)
    with pytest.raises(FormulaError) as caught:
        await run()
    assert caught.value.code == "no_feasible_speed"
    assert "at the mass 5.824 kg:" in caught.value.message


# --- the refinement goes through the same wrapper as the scan ----------------------------------------------


def with_hole(low: float, high: float, code: str, level: float = 7.0) -> Callable[[float], Any]:
    """``f(m) = level - m`` (linear: its regula falsi iterate is the root), which fails with ``code`` for
    ``low < m < high``, a band that holds no mass of the scan (3.4, 4.42, 5.746, 7.47 kg) but the iterate."""

    async def f(mass: float) -> float:
        if low < mass < high:
            raise failure(code, "failed inside the bracket")
        return level - mass

    return f


async def test_a_failure_at_a_refinement_mass_carries_that_mass() -> None:
    """The iterate (7.0 kg) is neither the current mass nor a scan mass; its failure names it."""
    with pytest.raises(FormulaError) as caught:
        await scan().root(with_hole(6.5, 7.3, "not_converged"), "level flight", LEVEL_NOT_HELD)
    assert caught.value.code == "not_converged"
    assert "at the mass 7 kg:" in caught.value.message
    assert close(float(str(caught.value.detail["mass_kg"])), 7.0, 1e-3)


@pytest.mark.parametrize(
    ("code", "not_held"),
    [("no_feasible_speed", LEVEL_NOT_HELD), ("outside_propeller_table", TAKEOFF_NOT_HELD)],
)
async def test_a_data_end_at_a_refinement_mass_closes_the_bracket_like_in_the_scan(
    code: str, not_held: frozenset[str]
) -> None:
    """Not "not held at the current mass": the edge below the iterate is bisected (6.5 kg) and declared."""
    sweep = scan()
    got, edge = await sweep.root(with_hole(6.5, 7.3, code), "level flight", not_held)
    assert edge
    assert close(got, 6.5, 2e-5)
    assert [
        w.detail["limit"] for w in sweep.ctx.warnings if w.code == "powered_limit_declared"
    ] == ["evaluation_edge"]


async def test_a_stall_solve_that_fails_at_a_refinement_mass_of_the_real_search_carries_it() -> (
    None
):
    """A stall solve that does not converge above 6.0 kg: the level scan reaches 7.47 kg, but the stall solve
    of the first iterate is what the stub fails first at a mass that is not a scan mass? No: scan masses are
    3.4, 4.42, 5.746, 7.47; the failure is placed above 6.0 kg so the scan mass 7.47 fails first, named."""
    with pytest.raises(FormulaError) as caught:
        await run(EnvelopeOpti(stall_fails_above=6.0))
    assert caught.value.code == "not_converged"
    assert "at the mass 7.47" in caught.value.message


# --- the last point of the curves --------------------------------------------------------------------------


async def test_at_an_edge_root_the_last_curve_point_is_computed_not_asserted() -> None:
    """Where the level problem ends at the edge of the data (the wing carries no mass above 8 kg), the best
    excess is still positive at the root: the closing climb rate is the computed one and V_max the computed
    highest level speed, not zero and not the speed of the best excess."""
    opti = EnvelopeOpti(cd0=0.2, lift_cap_mass=8.0)
    got, ctx = await run(opti)
    root = got["m_max_level"]
    assert close(root, 8.0, 2e-5)
    assert root <= 8.0
    stall_curve, level_curve = got["speed_range"]
    climb = got["roc_curve"]
    assert climb.x[-1] == root
    assert climb.y[-1] > 0.5  # m/s: the thrust still exceeds the drag at 8 kg
    assert close(climb.y[-1], best_climb_rate(root, 0.2), 5e-3)
    assert close(level_curve.y[-1], pb.max_level_speed(root, 0.2), 1e-4)
    assert level_curve.y[-1] != best_excess(root, 0.2)[1]  # not the speed of the best excess
    assert close(stall_curve.y[-1], v_stall(root), 1e-9)
    assert "evaluation_edge" in pb.limits(ctx)


async def test_at_a_sign_change_root_the_closing_values_are_the_root_condition() -> None:
    """Where the root is a sign change the thrust equals the drag at the best speed: V_max is that speed and
    the climb rate zero by the root condition (the entry says so); only the stall speed is computed."""
    got, _ = await run()
    _, level_curve = got["speed_range"]
    climb = got["roc_curve"]
    assert climb.y[-1] == 0.0
    assert close(level_curve.y[-1], best_excess(got["m_max_level"])[1], 1e-3)


# --- the warnings of the curve samples --------------------------------------------------------------------


async def test_a_sample_with_a_regime_warning_makes_the_curves_carry_it_with_the_mass() -> None:
    """ADR 0020: the warning of a sample's stall solve is not dropped; one warning per code, the masses
    at which it occurred in its detail."""
    _, ctx = await run(EnvelopeOpti(stall_warning_above=5.0))
    found = [w for w in ctx.warnings if w.code == "reynolds_outside_band"]
    summary = [w for w in found if "masses_kg" in w.detail]
    assert len(summary) == 1  # de-duplicated by code
    masses = summary[0].detail["masses_kg"]
    assert isinstance(masses, list)
    assert all(isinstance(m, float) and m > 5.0 for m in masses)  # only the samples above 5 kg
    assert len(masses) >= 1
    assert len(set(masses)) == len(masses)  # once per mass, although the answers repeat a notice
    by_mass = summary[0].detail["by_mass"]
    assert isinstance(by_mass, list)
    assert len(by_mass) == len(masses)
    assert summary[0].detail["re"] == 3.0e4
    assert "curve samples" in summary[0].message


async def test_the_stall_warnings_of_the_level_root_are_forwarded_with_the_scalar() -> None:
    _, ctx = await run(EnvelopeOpti(stall_warning_above=0.0))  # every stall solve warns
    plain = [
        w for w in ctx.warnings if w.code == "reynolds_outside_band" and "masses_kg" not in w.detail
    ]
    assert len(plain) >= 2  # the level root's and the take-off root's, forwarded as they happen


# --- one stall solve per mass ---------------------------------------------------------------------------------


async def test_a_stall_is_solved_once_per_mass_and_configuration() -> None:
    opti = EnvelopeOpti()
    await run(opti)
    keyed = list(zip(opti.stall_masses, opti.stall_airplanes, strict=True))
    seen = {(m, id(a)) for m, a in keyed}
    assert len(seen) == len(keyed)  # no mass of a configuration was solved twice
