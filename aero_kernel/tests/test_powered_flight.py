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


def flight(slug: str = "max-level-speed", mass: float = 3.4) -> pf.PoweredFlight:
    return pf.PoweredFlight(pb.bound_inputs(slug, mass=mass), pb.context(slug, pb.PolarOpti()))


# --- the numerical searches ------------------------------------------------------------------------


async def test_the_scan_runs_from_the_configured_start_to_the_limit_in_steps() -> None:
    speeds = list(pf.scan_speeds())
    assert (speeds[0], speeds[1], speeds[-1], len(speeds)) == (2.0, 4.0, 150.0, 75)


async def test_illinois_finds_the_cube_root_of_two() -> None:
    async def f(x: float) -> float:
        return x**3 - 2.0

    root = await pf.illinois_root(f, (0.0, -2.0), (2.0, 6.0), 1.0)
    assert close(root, 2.0 ** (1.0 / 3.0), 1e-7)


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


async def test_the_golden_section_finds_the_top_of_a_parabola() -> None:
    async def f(x: float) -> float | None:
        return -((x - 3.0) ** 2)

    x, value = await pf.golden_maximum(f, 0.5, 10.0)
    assert close(x, 3.0, 2e-4)
    assert abs(value) < 1e-6


async def test_the_golden_section_keeps_a_defined_point_where_the_maximum_is_on_the_edge() -> None:
    async def f(x: float) -> float | None:
        return x if x <= 5.0 else None

    x, value = await pf.golden_maximum(f, 1.0, 9.0)
    assert 4.99 < x <= 5.0
    assert value == x


async def test_the_golden_section_with_no_defined_point_is_not_converged() -> None:
    async def nothing(x: float) -> float | None:
        return None

    with pytest.raises(FormulaError) as caught:
        await pf.golden_maximum(nothing, 1.0, 9.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_the_maximum_over_the_speed_is_found_between_the_scan_points() -> None:
    async def f(v: float) -> float | None:
        return -((v - 21.3) ** 2)

    optimum = await pf.maximise_over_speed(f)
    assert close(optimum.v, 21.3, 5e-4)
    assert not optimum.on_wing_limit


async def test_an_objective_that_is_undefined_below_a_speed_gives_an_optimum_on_that_edge() -> None:
    async def f(v: float) -> float | None:
        return None if v < 12.3 else -v

    optimum = await pf.maximise_over_speed(f)
    assert 12.3 <= optimum.v < 12.32
    assert optimum.on_wing_limit


async def test_a_scan_with_no_defined_speed_is_the_declared_no_feasible_speed() -> None:
    async def never(v: float) -> float | None:
        return None

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(never)
    assert caught.value.code == "no_feasible_speed"


async def test_a_table_failure_after_feasible_speeds_is_not_relabelled() -> None:
    async def f(v: float) -> float | None:
        if v > 10.0:
            raise FormulaError(
                ErrorCategory.UNSUPPORTED_CONFIGURATION, "outside_propeller_table", "edge", "none"
            )
        return v

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(f)
    assert caught.value.code == "outside_propeller_table"


async def test_another_failure_before_feasible_speeds_is_not_relabelled_either() -> None:
    async def f(v: float) -> float | None:
        raise FormulaError(ErrorCategory.INVALID_INPUT, "missing_input", "absent", "give it")

    with pytest.raises(FormulaError) as caught:
        await pf.maximise_over_speed(f)
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
    assert got is not None
    assert expected is not None
    assert close(got, expected, 1e-7)


async def test_no_climb_where_the_thrust_is_below_the_level_drag() -> None:
    assert await pf.climb_angle(flight(), 32.0) is None  # T = 8.8 N, D = 11.7 N


async def test_no_climb_just_below_the_stall_where_a_steep_angle_is_not_held_by_the_thrust() -> (
    None
):
    assert await pf.climb_angle(flight(mass=6.0), 11.0) is None  # level C_L 1.4 > 1.2, thrust 26 N


async def test_the_vertical_upper_edge_needs_an_end_inside_the_scan(
    endless_thrust: None,
) -> None:
    airplane = flight(mass=0.8)
    with pytest.raises(FormulaError) as caught:
        await pf.vertical_upper_edge(airplane, 10.0)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


async def test_a_state_where_level_flight_is_not_held_gives_no_sustained_turn() -> None:
    assert await pf.sustained_load_factor(flight(), 32.0, 6.0) is None  # thrust below drag
    assert await pf.sustained_load_factor(flight(), 5.0, 6.0) is None  # below the stall


async def test_the_sustained_load_factor_is_the_closed_form_one() -> None:
    airplane = flight()
    got = await pf.sustained_load_factor(airplane, 20.0, 6.0)
    expected = pb.sustained_n(20.0, 3.4, 6.0)
    assert got is not None
    assert expected is not None
    assert close(got.n, expected[0], 2e-4)
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
    assert math.isclose(caught.value.detail["v_ms"], 150.0)  # type: ignore[index]


async def test_a_dive_whose_drag_never_reaches_weight_plus_thrust_is_not_converged(
    endless_thrust: None,
) -> None:
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=1e-3))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert caught.value.category is ErrorCategory.NOT_CONVERGED
    assert "scan limit" in caught.value.message


async def test_a_dive_that_is_already_dragged_to_a_stop_at_the_first_speed_is_not_converged() -> (
    None
):
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=3000.0))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert "first scan speed" in caught.value.message
