"""The six powered-performance formulas against an independent solution (gh-1414, fast tier).

AeroBuildup is a stub with a parabolic polar (``C_D = 0.04 + 0.06 C_L^2``, ``C_L,max = 1.2``, ``S = 0.5 m^2``,
m = 3.4 kg, W = 33.3426 N); the drive train is the AT2814 on 14.8 V with the published APC 13x8E table, its
thrust the plain-Python balance of ``powertrain_reference`` (60 N at no speed, falling to zero near 37 m/s).
The expectations are written here without the kernel's searches: a fine scan with bisection for the level
speed, bisection on the climb angle per speed, the closed form of the polar for the turns, the maximum over a
dense speed grid. The hand value: at 20 m/s the drag of level flight is
``122.5 N * (0.04 + 0.06 * 0.27218^2) = 5.4445 N`` (``q S = 0.5 * 1.225 * 400 * 0.5 = 122.5 N``,
``C_L = 33.3426 / 122.5 = 0.27218``).
"""

import math
from collections.abc import Callable
from typing import Any

import pytest
from aero_kernel.errors import FormulaError
from aero_kernel.formulas import powered_flight as pf
from aero_kernel.formulas.best_angle_of_climb import best_angle_of_climb
from aero_kernel.formulas.best_rate_of_climb import best_rate_of_climb
from aero_kernel.formulas.dive_speed import dive_speed
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.formulas.max_sustained_turn_rate import max_sustained_turn_rate
from aero_kernel.formulas.min_sustained_turn_radius import min_sustained_turn_radius
from aero_kernel.schema import KernelWarning
from aero_kernel.tests import powered_builders as pb
from aero_kernel.tests.formula_builders import close

pytestmark = pytest.mark.asyncio

MASS = 3.4
WEIGHT = MASS * pb.G
STUB_NOTICE = KernelWarning.of("induced_drag_viscous_factor_removed", "the stub's drag notice")


async def test_the_hand_value_of_the_level_drag_is_the_stub_polar() -> None:
    drag = pb.drag(20.0, 1.0, MASS)
    assert drag is not None
    assert close(drag, 5.4445, 1e-4)


# --- max-level-speed -------------------------------------------------------------------------------


async def test_the_maximum_level_speed_is_the_root_of_thrust_minus_drag() -> None:
    opti = pb.PolarOpti(warnings=(STUB_NOTICE,))
    ctx = pb.context("max-level-speed", opti)
    got = await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    expected = pb.max_level_speed(MASS)
    assert close(got["v_max"], expected, 1e-4)
    drag = pb.drag(got["v_max"], 1.0, MASS)
    assert drag is not None
    assert close(pb.thrust(got["v_max"]), drag, 1e-4)  # thrust available equals drag at the answer


async def test_only_the_warnings_of_the_answer_are_forwarded_and_the_route_is_declared() -> None:
    opti = pb.PolarOpti(warnings=(STUB_NOTICE,))
    ctx = pb.context("max-level-speed", opti)
    await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    codes = [w.code for w in ctx.warnings]
    assert len(opti.evaluations) > 10  # many evaluations along the search
    assert codes.count("induced_drag_viscous_factor_removed") == 1  # the answer's only
    assert codes.count("powertrain_route_winding_resistance") == 1


async def test_the_embedded_relations_are_the_ones_the_canon_lists() -> None:
    from aero_kernel.build import shipped_build

    ctx = pb.context("max-level-speed")
    await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    formula = shipped_build().model.formula("max-level-speed")
    assert formula is not None
    assert set(ctx.embedded_requests) == set(formula.embeds)


async def test_a_drive_train_that_cannot_hold_level_flight_is_a_declared_failure() -> None:
    ctx = pb.context("max-level-speed", pb.PolarOpti(cd0=2.0))
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert caught.value.code == "no_feasible_speed"
    # C_D0 = 2.0: every speed the wing can fly has D > T, so the thrust is the stated reason, not the wing
    assert "thrust at full throttle is below" in caught.value.message
    assert "wing cannot carry" not in caught.value.message


async def test_a_thrust_that_outlasts_the_propeller_table_is_the_declared_table_failure() -> None:
    ctx = pb.context("max-level-speed", pb.PolarOpti(cd0=1e-5))
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert caught.value.code == "outside_propeller_table"


async def test_an_absent_winding_resistance_is_missing_input() -> None:
    ctx = pb.context("max-level-speed")
    absent: dict[str, Any] = {"motor-circuit-resistance": None}
    with pytest.raises(FormulaError) as caught:
        await max_level_speed(pb.bound_inputs("max-level-speed", **absent), ctx)
    assert caught.value.code == "missing_input"


# --- dive-speed ------------------------------------------------------------------------------------


async def test_the_dive_speed_balances_zero_lift_drag_against_weight_plus_thrust() -> None:
    cd0 = 0.3  # a draggy airplane, so the dive ends inside the propeller table
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=cd0))
    got = await dive_speed(pb.bound_inputs("dive-speed"), ctx)

    def surplus(v: float) -> float:
        return -(0.5 * pb.RHO * v * v * pb.AREA * cd0 - WEIGHT - pb.thrust(v))

    expected = pb.bisect(surplus, 5.0, 30.0)
    assert close(got["v_d"], expected, 1e-4)
    assert [w.code for w in ctx.warnings].count("powertrain_route_winding_resistance") == 1


async def test_a_dive_that_runs_past_the_propeller_table_is_the_declared_table_failure() -> None:
    ctx = pb.context("dive-speed", pb.PolarOpti(cd0=0.03))
    with pytest.raises(FormulaError) as caught:
        await dive_speed(pb.bound_inputs("dive-speed"), ctx)
    assert caught.value.code == "outside_propeller_table"


# --- the climbs ------------------------------------------------------------------------------------


def brute_force(objective: Callable[[float, float], float], mass: float) -> tuple[float, float]:
    """The speed and the value of the maximum of ``objective(v, gamma)`` on a 0.05 m/s grid."""
    best = (0.0, -math.inf)
    v = 3.0
    while v < pb.TABLE_EDGE_MS:
        gamma = pb.climb_angle(v, mass)
        if gamma is not None and objective(v, gamma) > best[1]:
            best = (v, objective(v, gamma))
        v += 0.05
    return best


def slowest_climbing_speed(mass: float) -> float:
    """The lowest speed at which a climb exists: bisection on the predicate, from 3 m/s to 20 m/s."""
    low, high = 3.0, 20.0
    for _ in range(60):
        middle = 0.5 * (low + high)
        if pb.climb_angle(middle, mass) is None:
            low = middle
        else:
            high = middle
    return high


async def test_the_best_rate_of_climb_is_the_maximum_over_the_speed_of_v_sin_gamma() -> None:
    mass = 6.0  # T/W about 0.5: an interior optimum
    ctx = pb.context("best-rate-of-climb")
    got = await best_rate_of_climb(pb.bound_inputs("best-rate-of-climb", mass=mass), ctx)
    v_expected, roc_expected = brute_force(lambda v, gamma: v * math.sin(gamma), mass)
    assert abs(got["v_y"] - v_expected) <= 0.06  # the grid of the brute force
    assert close(got["roc_max"], roc_expected, 1e-4)  # flat at the maximum
    assert got["roc_max"] >= roc_expected - 1e-9
    assert [w.code for w in ctx.warnings].count("powered_limit_declared") == 0  # interior optimum


@pytest.mark.parametrize("mass", [3.4, 6.0])
async def test_the_best_angle_of_climb_lies_on_the_stall_corner_and_says_so(mass: float) -> None:
    """The slower the speed, the steeper the angle the thrust allows, until the wing cannot carry the lift."""
    ctx = pb.context("best-angle-of-climb")
    got = await best_angle_of_climb(pb.bound_inputs("best-angle-of-climb", mass=mass), ctx)
    v_edge = slowest_climbing_speed(mass)
    gamma_edge = pb.climb_angle(v_edge, mass)
    assert gamma_edge is not None
    assert close(got["v_x"], v_edge, 3e-4)
    assert close(math.radians(got["gamma_max"]), gamma_edge, 2e-3)
    ratio = min(1.0, pb.thrust(0.0) / (mass * pb.G))
    floor_binds = (1.0 - ratio * ratio) ** 0.25 < 0.5  # the scan floor of the climbs (gh-1419)
    assert pb.limits(ctx) == (["scan_floor", "wing"] if floor_binds else ["wing"])


async def test_a_thrust_above_the_weight_climbs_vertically_and_declares_it() -> None:
    mass = 0.8  # W = 7.8 N, below the thrust of 40 N up to about 25 m/s
    ctx = pb.context("best-angle-of-climb")
    got = await best_angle_of_climb(pb.bound_inputs("best-angle-of-climb", mass=mass), ctx)
    assert got["gamma_max"] == 90.0
    assert pb.limits(ctx) == [
        "scan_floor",
        "gamma_90_deg",
    ]  # a climb that can be vertical: floor start
    weight = mass * pb.G

    def excess(v: float) -> float:
        return pb.thrust(v) - 0.5 * pb.RHO * v * v * pb.AREA * pb.CD0 - weight

    assert close(got["v_x"], pb.bisect(excess, 5.0, 33.0), 1e-5)  # the upper edge of the range


async def test_the_best_rate_of_climb_vertical_is_declared_too() -> None:
    mass = 0.8
    ctx = pb.context("best-rate-of-climb")
    got = await best_rate_of_climb(pb.bound_inputs("best-rate-of-climb", mass=mass), ctx)
    v_expected, roc_expected = brute_force(lambda v, gamma: v * math.sin(gamma), mass)
    assert abs(got["v_y"] - v_expected) <= 0.06
    assert close(got["roc_max"], roc_expected, 1e-3)
    # T_0 = 40 N exceeds W = 7.8 N: the climb can be vertical, and the notice says so
    assert "gamma_90_deg" in pb.limits(ctx)


async def test_the_best_rate_of_climb_on_the_stall_corner_declares_the_wing() -> None:
    # C_D0 = 0.3 makes the drag so high that the rate of climb is greatest at the slowest speed
    # the wing can fly: the first valued scan point, the stall corner
    ctx = pb.context("best-rate-of-climb", pb.PolarOpti(cd0=0.3))
    await best_rate_of_climb(pb.bound_inputs("best-rate-of-climb", mass=6.0), ctx)
    assert "wing" in pb.limits(ctx)
    notice = next(
        w
        for w in ctx.warnings
        if w.code == "powered_limit_declared" and w.detail["limit"] == "wing"
    )
    assert "cos_gamma" in notice.detail
    assert "cl" in notice.detail


async def test_a_wing_that_cannot_carry_the_weight_anywhere_has_no_feasible_speed() -> None:
    ctx = pb.context("best-rate-of-climb")
    with pytest.raises(FormulaError) as caught:
        await best_rate_of_climb(pb.bound_inputs("best-rate-of-climb", mass=3000.0), ctx)
    assert caught.value.code == "no_feasible_speed"


async def test_a_drive_train_that_cannot_climb_has_no_feasible_speed() -> None:
    ctx = pb.context("best-angle-of-climb", pb.PolarOpti(cd0=2.0))
    with pytest.raises(FormulaError) as caught:
        await best_angle_of_climb(pb.bound_inputs("best-angle-of-climb"), ctx)
    assert caught.value.code == "no_feasible_speed"


# --- the sustained turns ---------------------------------------------------------------------------


def turn_scan(
    objective: Callable[[float, float], float], n_lim: float, cd0: float = pb.CD0
) -> tuple[float, float, str]:
    """The best speed, its value and its limit over a 0.05 m/s grid, from the closed form."""
    best: tuple[float, float, str] = (0.0, -math.inf, "")
    v = 4.0
    while v < pb.TABLE_EDGE_MS:
        found = pb.sustained_n(v, MASS, n_lim, cd0)
        if found is not None and found[0] > 1.0:
            value = objective(v, found[0])
            if value > best[1]:
                best = (v, value, found[1])
        v += 0.05
    return best


def rate(v: float, n: float) -> float:
    return pb.G * math.sqrt(n * n - 1.0) / v


def radius(v: float, n: float) -> float:
    return -(v * v / (pb.G * math.sqrt(n * n - 1.0)))


async def test_the_fastest_sustained_turn_matches_the_closed_form_scan() -> None:
    n_lim = 6.0
    ctx = pb.context("max-sustained-turn-rate")
    got = await max_sustained_turn_rate(pb.bound_inputs("max-sustained-turn-rate"), ctx)
    v_expected, omega_expected, limit_expected = turn_scan(rate, n_lim)
    assert abs(got["v_omega"] - v_expected) <= 0.06
    assert close(math.radians(got["omega_max"]), omega_expected, 2e-3)
    declared = pb.limits(ctx)
    assert declared == [limit_expected] or {*declared, limit_expected} == {"thrust", "wing"}


async def test_the_turn_kinematics_by_hand() -> None:
    # n = 2: sqrt(n^2 - 1) = sqrt(3) = 1.7320508 (the load factor of a 60 degree bank)
    # omega = 9.80665 * 1.7320508 / 20 = 0.849281 rad/s = 48.660 deg/s
    # r = 20^2 / (9.80665 * 1.7320508) = 400 / 16.98558 = 23.5493 m
    from aero_kernel.formulas.max_sustained_turn_rate import turn_rate
    from aero_kernel.formulas.min_sustained_turn_radius import turn_radius

    omega = turn_rate(9.80665, 20.0, 2.0)
    r = turn_radius(9.80665, 20.0, 2.0)
    assert close(omega, 0.849281, 1e-5)
    assert close(math.degrees(omega), 48.660, 1e-5)
    assert close(r, 23.5493, 1e-5)
    assert close(omega, 20.0 / r, 1e-12)  # omega = V / r


async def test_the_tightest_sustained_turn_matches_the_closed_form_scan() -> None:
    n_lim = 6.0
    ctx = pb.context("min-sustained-turn-radius")
    got = await min_sustained_turn_radius(pb.bound_inputs("min-sustained-turn-radius"), ctx)
    v_expected, neg_radius, limit_expected = turn_scan(radius, n_lim)
    assert abs(got["v_r"] - v_expected) <= 0.06
    assert close(got["r_min"], -neg_radius, 2e-3)
    declared = pb.limits(ctx)
    assert declared == [limit_expected] or {*declared, limit_expected} == {"thrust", "wing"}


@pytest.mark.parametrize(
    ("n_lim", "cd0", "limits"),
    [(1.5, 0.04, ("structure", "wing")), (6.0, 0.2, ("wing",))],
)
async def test_the_limit_that_binds_is_declared(
    n_lim: float, cd0: float, limits: tuple[str, ...]
) -> None:
    """With a small limit load factor the optimum is the corner of the structure and the wing limit."""
    ctx = pb.context("max-sustained-turn-rate", pb.PolarOpti(cd0=cd0))
    await max_sustained_turn_rate(pb.bound_inputs("max-sustained-turn-rate", n_lim=n_lim), ctx)
    (declared,) = pb.limits(ctx)
    assert declared in limits
    assert turn_scan(rate, n_lim, cd0)[2] in limits  # the independent scan names the same limit


async def test_a_limit_load_factor_below_the_turn_of_a_speed_is_the_structure_limit() -> None:
    from aero_kernel.tests.test_powered_flight import flight

    got = await pf.sustained_load_factor(flight("max-sustained-turn-rate"), 20.0, 1.5)
    assert got == pf.TurnLimit(1.5, "structure")


async def test_at_the_corner_of_thrust_and_wing_one_of_the_two_is_declared() -> None:
    """The optimum of the turn rate is where the thrust limit meets the wing limit; both bind there."""
    ctx = pb.context("max-sustained-turn-rate")
    await max_sustained_turn_rate(pb.bound_inputs("max-sustained-turn-rate"), ctx)
    declared = pb.limits(ctx)
    assert declared in (["thrust"], ["wing"])


async def test_a_limit_load_factor_of_one_allows_no_turn() -> None:
    ctx = pb.context("max-sustained-turn-rate")
    with pytest.raises(FormulaError) as caught:
        await max_sustained_turn_rate(pb.bound_inputs("max-sustained-turn-rate", n_lim=1.0), ctx)
    assert caught.value.code == "no_feasible_speed"


@pytest.mark.parametrize("n_lim", [2.0, 10.0])
async def test_a_limit_load_factor_above_one_passes_its_precondition(n_lim: float) -> None:
    from aero_kernel.formulas.max_sustained_turn_rate import limit_load_factor_above_one

    x = pb.bound_inputs("max-sustained-turn-rate", n_lim=n_lim)
    assert limit_load_factor_above_one(x).state == "held"


@pytest.mark.parametrize("n_lim", [1.0, 0.5, -3.0])
async def test_a_limit_load_factor_not_above_one_violates_its_precondition(n_lim: float) -> None:
    from aero_kernel.formulas.max_sustained_turn_rate import limit_load_factor_above_one

    x = pb.bound_inputs("min-sustained-turn-radius", n_lim=n_lim)
    result = limit_load_factor_above_one(x)
    assert result.state == "violated"
    assert "no level turn" in result.message


async def test_both_turn_entries_declare_the_precondition_on_n_lim() -> None:
    from aero_kernel.build import shipped_build

    for slug in ("max-sustained-turn-rate", "min-sustained-turn-radius"):
        formula = shipped_build().model.formula(slug)
        assert formula is not None
        (check,) = [p for p in formula.preconditions if p.id == "limit_load_factor_above_one"]
        assert (check.parameter, check.on_violation) == ("n_lim", "error")
