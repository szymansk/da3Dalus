"""The shared searches and states of the powered-performance formulas (gh-1414, fast tier).

Plain functions with a known answer for the searches (cubic root, parabola, an objective that is undefined
below a speed) and the closed-form airplane of ``powered_builders`` for the states and the declared failures.
"""

import math
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas import powered_flight as pf
from aero_kernel.formulas.dive_speed import dive_speed
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import LevelFlightPoint
from aero_kernel.tests import powered_builders as pb
from aero_kernel.tests.formula_builders import close

pytestmark = pytest.mark.asyncio

START = (
    2.0  # the start of the scans of these tests of the search itself (a parameter of the search)
)


def flight(slug: str = "max-level-speed", mass: float = 3.4) -> pf.PoweredFlight:
    return pf.PoweredFlight(pb.bound_inputs(slug, mass=mass), pb.context(slug, pb.PolarOpti()))


# --- the numerical searches ------------------------------------------------------------------------


async def test_the_scan_runs_from_the_given_start_to_the_limit_in_steps() -> None:
    speeds = list(pf.scan_speeds(START))
    assert (speeds[0], speeds[1], speeds[-1], len(speeds)) == (2.0, 4.0, 150.0, 75)
    from_stall = list(pf.scan_speeds(9.5))
    assert (from_stall[0], from_stall[1], from_stall[-1]) == (9.5, 11.5, 149.5)


async def test_illinois_finds_the_cube_root_of_two() -> None:
    async def f(x: float) -> float:
        return x**3 - 2.0

    root = await pf.illinois_root(f, (0.0, -2.0), (2.0, 6.0), 1.0)
    assert close(root, 2.0 ** (1.0 / 3.0), 1e-4)  # the residual tolerance is 1e-5 of the scale


async def test_illinois_returns_an_end_that_is_already_the_root() -> None:
    async def f(x: float) -> float:
        raise AssertionError(x)

    assert await pf.illinois_root(f, (1.0, 0.0), (2.0, 5.0), 1.0) == 1.0
    assert await pf.illinois_root(f, (1.0, -5.0), (2.0, 0.0), 1.0) == 2.0


async def test_illinois_on_a_jump_ends_as_not_converged() -> None:
    async def jump(x: float) -> float:
        return 1.0 if x > 1.0 else -1.0

    with pytest.raises(FormulaError) as caught:
        await pf.illinois_root(jump, (0.0, -1.0), (2.0, 1.0), 1.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_illinois_terminates_on_an_evaluation_that_carries_noise_of_the_lift_accuracy() -> (
    None
):
    """The points are made with a lift tolerance of 1e-6 of the weight: the root search must not chase it."""
    calls = 0

    async def noisy(x: float) -> float:
        nonlocal calls
        calls += 1
        return (x - 1.0) + 4e-6 * math.sin(1000.0 * x)  # noise of 4e-6 of the scale 1

    root = await pf.illinois_root(noisy, (0.0, -1.0), (3.0, 2.0), 1.0)
    assert abs(root - 1.0) < 1e-4
    assert calls < 30  # far from the 60-step limit


async def test_the_golden_section_finds_the_top_of_a_parabola() -> None:
    async def f(x: float) -> float | pf.Unflyable:
        return -((x - 3.0) ** 2)

    result = await pf.golden_maximum(f, 0.5, 10.0)
    assert close(result.v, 3.0, 2e-4)
    assert abs(result.value) < 1e-6
    assert result.above is None  # an interior maximum


async def test_the_golden_section_names_the_bound_a_maximum_lies_against() -> None:
    async def f(x: float) -> float | pf.Unflyable:
        return x if x <= 5.0 else pf.Unflyable.TABLE

    result = await pf.golden_maximum(f, 1.0, 9.0)
    assert 4.99 < result.v <= 5.0
    assert result.value == result.v
    assert result.above is pf.Unflyable.TABLE


async def test_the_golden_section_with_no_point_with_a_value_is_not_converged() -> None:
    async def nothing(x: float) -> float | pf.Unflyable:
        return pf.Unflyable.WING

    with pytest.raises(FormulaError) as caught:
        await pf.golden_maximum(nothing, 1.0, 9.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_the_maximum_over_the_speed_is_found_between_the_scan_points() -> None:
    async def f(v: float) -> float | pf.Unflyable:
        return -((v - 21.3) ** 2)

    optimum = await pf.maximise_over_speed(f, flight(), START)
    assert close(optimum.v, 21.3, 5e-4)
    assert not optimum.on_wing_limit


async def test_an_objective_without_a_value_below_a_speed_gives_an_optimum_on_that_corner() -> None:
    async def f(v: float) -> float | pf.Unflyable:
        return pf.Unflyable.WING if v < 12.3 else -v

    optimum = await pf.maximise_over_speed(f, flight(), START)
    assert 12.3 <= optimum.v < 12.32
    assert optimum.on_wing_limit


async def test_the_speeds_skipped_below_the_first_value_are_declared_with_the_answer() -> None:
    async def f(v: float) -> float | pf.Unflyable:
        return pf.Unflyable.WING if v < 12.3 else -((v - 20.0) ** 2)

    airplane = flight()
    await pf.maximise_over_speed(f, airplane, START)
    await airplane.answer(20.0, 1.0)
    (skipped,) = [w for w in airplane.ctx.warnings if w.code == "powered_speeds_skipped"]
    assert skipped.detail["count"] == 6  # 2, 4, ... 12 m/s
    assert (skipped.detail["v_min_ms"], skipped.detail["v_max_ms"]) == (2.0, 12.0)
    assert skipped.detail["reasons"] == ["wing"]


async def test_a_scan_with_no_value_names_what_stopped_every_speed() -> None:
    async def never(v: float) -> float | pf.Unflyable:
        return pf.Unflyable.WING

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(never, flight(), START)
    assert caught.value.code == "no_feasible_speed"
    assert "wing cannot carry" in caught.value.message
    assert "thrust" not in caught.value.message  # no drag was ever short of thrust


async def test_a_thrust_that_is_never_enough_is_named_as_such() -> None:
    async def short(v: float) -> float | pf.Unflyable:
        return pf.Unflyable.THRUST

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(short, flight(), START)
    assert "thrust at full throttle is below" in caught.value.message
    assert "wing" not in caught.value.message


def table_end(v: float) -> FormulaError:
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "outside_propeller_table", f"edge at {v}", "none"
    )


async def test_an_optimum_on_the_table_edge_is_the_declared_table_failure() -> None:
    async def f(v: float) -> float | pf.Unflyable:
        if v > 10.0:
            raise table_end(v)
        return v

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(f, flight(), START)
    assert caught.value.code == "outside_propeller_table"
    assert "optimum lies on the end of the table" in caught.value.message


async def test_an_optimum_bracketed_below_the_table_edge_is_returned() -> None:
    async def f(v: float) -> float:
        if v > 10.0:
            raise table_end(v)
        return -((v - 7.3) ** 2)

    optimum = await pf.maximise_over_speed(f, flight(), START)
    assert close(optimum.v, 7.3, 1e-3)


async def test_a_table_that_ends_before_any_value_is_the_failure_with_the_table_named() -> None:
    async def f(v: float) -> float:
        raise table_end(v)

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(f, flight(), START)
    assert caught.value.code == "no_feasible_speed"
    assert "propeller table ends" in caught.value.message


async def test_another_failure_before_feasible_speeds_is_not_relabelled() -> None:
    async def f(v: float) -> float | pf.Unflyable:
        raise FormulaError(ErrorCategory.INVALID_INPUT, "missing_input", "absent", "give it")

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(f, flight(), START)
    assert caught.value.code == "missing_input"


# --- the states ------------------------------------------------------------------------------------


async def test_the_wing_limit_is_none_but_another_failure_is_raised() -> None:
    airplane = flight(mass=3.4)
    assert await airplane.drag(5.0, 1.0) is None  # C_L = 2.2 > 1.2
    assert await airplane.drag(20.0, 1.0) is not None

    class Broken(pb.PolarOpti):
        async def level_flight_point(
            self,
            airplane: AirplaneGeometry,
            mass_kg: float,
            gravity: float,
            air: AirState,
            v_ms: float,
            n_load: float,
        ) -> LevelFlightPoint:
            raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "no lift slope", "x")

    broken = pf.PoweredFlight(
        pb.bound_inputs("max-level-speed"), pb.context("max-level-speed", Broken())
    )
    with pytest.raises(FormulaError):
        await broken.drag(20.0, 1.0)


async def test_a_state_inside_a_bracket_must_be_flyable() -> None:
    with pytest.raises(FormulaError) as caught:
        await flight().required_drag(5.0, 1.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_the_thrust_is_computed_once_per_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    asked: list[float] = []

    def counted(*args: Any, **kwargs: Any) -> float:
        asked.append(args[2])
        return 12.5

    monkeypatch.setattr(pf, "full_throttle_thrust", counted)
    airplane = flight()
    assert (airplane.thrust(10.0), airplane.thrust(10.0), airplane.thrust(12.0)) == (12.5,) * 3
    assert asked == [10.0, 12.0]


async def test_the_climb_angle_has_the_hand_value_at_a_level_speed() -> None:
    """At 24 m/s and 6 kg the stub's thrust excess gives a shallow climb: the angle matches the bisection."""
    airplane = flight(mass=6.0)
    got = await pf.climb_angle(airplane, 24.0)
    expected = pb.climb_angle(24.0, 6.0)
    assert not isinstance(got, pf.Unflyable)
    assert expected is not None
    assert close(got, expected, 1e-5)


async def test_no_climb_where_the_thrust_is_below_the_level_drag() -> None:
    assert await pf.climb_angle(flight(), 32.0) is pf.Unflyable.THRUST  # T = 8.8 N, D = 11.7 N


async def test_no_climb_just_below_the_stall_where_a_steep_angle_is_not_held_by_the_thrust() -> (
    None
):
    assert await pf.climb_angle(flight(mass=6.0), 11.0) is pf.Unflyable.WING  # level C_L 1.4 > 1.2


async def test_the_vertical_upper_edge_needs_an_end_inside_the_scan(
    endless_thrust: None,
) -> None:
    airplane = flight(mass=0.8)
    with pytest.raises(FormulaError) as caught:
        await pf.vertical_upper_edge(airplane, 10.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_a_state_where_level_flight_is_not_held_gives_no_sustained_turn() -> None:
    assert await pf.sustained_load_factor(flight(), 32.0, 6.0) is pf.Unflyable.THRUST
    assert await pf.sustained_load_factor(flight(), 5.0, 6.0) is pf.Unflyable.WING


async def test_the_sustained_load_factor_is_the_closed_form_one() -> None:
    airplane = flight()
    got = await pf.sustained_load_factor(airplane, 20.0, 6.0)
    expected = pb.sustained_n(20.0, 3.4, 6.0)
    assert not isinstance(got, pf.Unflyable)
    assert expected is not None
    assert close(got.n, expected[0], 1e-5)
    assert got.limit == expected[1]


# --- the declared failures at the end of a scan ----------------------------------------------------


@pytest.fixture
def endless_thrust(monkeypatch: pytest.MonkeyPatch) -> None:
    """A drive train that never runs out of table: 10 N at every speed."""

    def endless(*args: Any, **kwargs: Any) -> float:
        return 1000.0

    monkeypatch.setattr(pf, "full_throttle_thrust", endless)


async def test_a_thrust_above_the_drag_up_to_the_scan_limit_is_not_converged(
    endless_thrust: None,
) -> None:
    ctx = pb.context("max-level-speed", pb.PolarOpti(cd0=1e-4))
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED
    assert 148.0 < caught.value.detail["v_ms"] <= 150.0  # type: ignore[index]  # the last scan speed


async def test_a_dive_whose_drag_never_reaches_weight_plus_thrust_is_not_converged(
    endless_thrust: None,
) -> None:
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=1e-3))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED
    assert "scan limit" in caught.value.message


async def test_a_dive_that_leaves_the_table_names_the_speed_it_left_at() -> None:
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=0.04))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert caught.value.code == "outside_propeller_table"
    assert "the dive left the propeller table at" in caught.value.message


async def test_a_dive_that_is_already_dragged_to_a_stop_at_the_first_speed_is_not_converged() -> (
    None
):
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=3000.0))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert "first scan speed" in caught.value.message


# --- the declared skips, the corner notice and the load factor -------------------------------------


async def test_the_corner_notice_carries_what_a_reader_needs_to_understand_the_climb_speed() -> (
    None
):
    ctx_flight = flight("best-angle-of-climb", mass=3.4)
    await ctx_flight.drag(20.0, 1.0)  # the lowest level speed that is known to the flight
    optimum = pf.Optimum(12.0, 0.5, on_wing_limit=True)
    await pf.finish_climb(ctx_flight, optimum, 0.5)
    (notice,) = [w for w in ctx_flight.ctx.warnings if w.code == "powered_limit_declared"]
    assert notice.detail["limit"] == "wing"
    assert set(notice.detail) >= {"v_ms", "cl", "gamma_deg", "cos_gamma"}
    assert notice.detail["cos_gamma"] == math.cos(0.5)
    assert notice.detail["lowest_evaluated_level_flight_speed_ms"] == 20.0


async def test_the_lowest_level_speed_is_the_lowest_speed_where_level_flight_was_possible() -> None:
    airplane = flight()
    for v in (30.0, 12.0, 5.0, 20.0):  # 5 m/s: the wing cannot carry the weight
        await airplane.drag(v, 1.0)
    assert airplane.lowest_level_speed == 12.0


async def test_the_sustained_load_factor_is_resolved_far_below_the_speed_resolution() -> None:
    """The bisection of n runs to 1e-6, so the turn rate is not a staircase at the 1e-4 of the speed search."""
    airplane = flight()
    first = await pf.sustained_load_factor(airplane, 20.0, 6.0)
    second = await pf.sustained_load_factor(airplane, 20.0 + 1e-3, 6.0)
    assert not isinstance(first, pf.Unflyable)
    assert not isinstance(second, pf.Unflyable)
    expected = pb.sustained_n(20.0, 3.4, 6.0)
    assert expected is not None
    assert abs(first.n - expected[0]) <= 2e-6 * expected[0]


async def test_a_zero_lift_point_that_does_not_exist_surfaces_and_is_not_skipped() -> None:
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=0.3, zero_lift_floor=12.0))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED
    assert "zero-lift" in caught.value.message


async def test_a_sweep_without_a_peak_surfaces_from_the_level_speed_scan() -> None:
    ctx = pb.context("max-level-speed", pb.PolarOpti(no_peak_below=12.0))
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED
    assert "no peak" in caught.value.message


async def test_a_level_speed_that_dips_and_recovers_is_the_last_crossing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The thrust dips below the drag between 18 and 26 m/s and recovers: the answer is the last crossing."""

    def thrust(v: float) -> float:
        base = 60.0 - 1.5 * v
        return base - 25.0 if 18.0 <= v <= 26.0 else base

    def dipping(*args: Any, **kwargs: Any) -> float:
        return thrust(args[2])

    monkeypatch.setattr(pf, "full_throttle_thrust", dipping)
    got = await max_level_speed(
        pb.bound_inputs("max-level-speed"), pb.context("max-level-speed", pb.PolarOpti())
    )

    def excess(v: float) -> float:
        drag = pb.drag(v, 1.0, 3.4)
        assert drag is not None
        return thrust(v) - drag

    crossings = [
        v / 100.0 for v in range(1000, 4000) if excess(v / 100.0) > 0 >= excess(v / 100.0 + 0.01)
    ]
    assert (
        len(crossings) >= 2
    )  # the first crossing is inside the dip's start, the last is the top speed
    assert abs(got["v_max"] - crossings[-1]) <= 1e-2


async def test_the_level_speed_scan_declares_the_table_edge_as_the_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The thrust is still above the drag where the table ends: the declared failure, not a value."""

    def short_table(*args: Any, **kwargs: Any) -> float:
        if args[2] > 30.0:
            raise table_end(args[2])
        return 40.0

    monkeypatch.setattr(pf, "full_throttle_thrust", short_table)
    ctx = pb.context("max-level-speed", pb.PolarOpti())
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert caught.value.code == "outside_propeller_table"
    assert "last speed the table covers" in caught.value.message


async def test_a_crossing_below_the_table_edge_is_returned_although_the_table_ends_later(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def thrust(*args: Any, **kwargs: Any) -> float:
        if args[2] > 36.0:
            raise table_end(args[2])
        return 30.0 - 0.5 * args[2]

    monkeypatch.setattr(pf, "full_throttle_thrust", thrust)
    got = await max_level_speed(
        pb.bound_inputs("max-level-speed"), pb.context("max-level-speed", pb.PolarOpti())
    )

    def excess(v: float) -> float:
        drag = pb.drag(v, 1.0, 3.4)
        assert drag is not None
        return 30.0 - 0.5 * v - drag

    expected = pb.bisect(excess, 12.0, 36.0)
    assert close(got["v_max"], expected, 1e-4)


async def test_the_speeds_the_wing_cannot_fly_are_declared_in_the_result() -> None:
    """A stall speed below the one the solver finds (another method): the scan starts at 8 m/s, and the
    speed 8 m/s, where the stub wing (stalls at 9.52 m/s) cannot carry the weight, is skipped and declared."""
    ctx = pb.context("max-level-speed", pb.PolarOpti())
    await max_level_speed(pb.bound_inputs("max-level-speed", **{"stall-speed": 8.0}), ctx)
    (skipped,) = [w for w in ctx.warnings if w.code == "powered_speeds_skipped"]
    assert skipped.detail["v_min_ms"] == 8.0
    assert skipped.detail["reasons"] == ["wing"]
    assert skipped.detail["count"] == 1
