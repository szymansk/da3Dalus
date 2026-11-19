"""Where the scan of the powered-performance formulas starts (gh-1419, fast tier).

The scan starts at a speed tied to the airplane, not at a fixed speed: the clean stall speed ``v_s`` for the
formulas that carry at least the weight (level speed, turns) and the dive (its zero-lift drag at ``v_s`` is
``C_D0 / C_L,max`` of the weight, below the weight plus the thrust, so the root lies above), and
``v_s sqrt(cos gamma_T)`` for the climbs, with ``sin gamma_T = T_0 / W`` the steepest angle the static thrust
holds (a climb at ``gamma`` carries ``W cos gamma``, so it can fly down to the stall speed at that load factor).
The stub polar of ``powered_builders`` has ``V_S = 9.52 m/s`` at 3.4 kg and a static thrust of 60 N.
"""

import math
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.best_angle_of_climb import best_angle_of_climb
from aero_kernel.formulas.best_rate_of_climb import best_rate_of_climb
from aero_kernel.formulas.dive_speed import dive_speed
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.formulas.max_sustained_turn_rate import max_sustained_turn_rate
from aero_kernel.formulas.min_sustained_turn_radius import min_sustained_turn_radius
from aero_kernel.tests import powered_builders as pb
from aero_kernel.tests.formula_builders import close

pytestmark = pytest.mark.asyncio

Formula = Callable[[Any, Any], Awaitable[dict[str, float]]]
LEVEL_LIKE = [
    ("max-level-speed", max_level_speed),
    ("dive-speed", dive_speed),
    ("max-sustained-turn-rate", max_sustained_turn_rate),
    ("min-sustained-turn-radius", min_sustained_turn_radius),
]
CLIMBS = [("best-rate-of-climb", best_rate_of_climb), ("best-angle-of-climb", best_angle_of_climb)]
ALL = LEVEL_LIKE + CLIMBS
DRAGGY = 0.3  # a draggy stub, so the dive ends inside the propeller table


def drag_of(slug: str) -> float:
    return DRAGGY if slug == "dive-speed" else pb.CD0


SCAN_FLOOR = 0.5  # config powered_climb_scan_floor


def climb_start(mass: float) -> float:
    """The start of the climb scan by the rule, from the independent thrust of the stub drive train."""
    ratio = min(1.0, pb.thrust(0.0) / (mass * pb.G))
    fraction = max(SCAN_FLOOR, (1.0 - ratio * ratio) ** 0.25)
    return pb.stall_speed(mass) * fraction


@pytest.mark.parametrize(("slug", "formula"), ALL)
async def test_a_sweep_without_a_peak_below_the_scan_start_does_not_end_the_formula(
    slug: str, formula: Formula
) -> None:
    mass = 8.0 if slug in dict(CLIMBS) else 3.4
    start = climb_start(mass) if slug in dict(CLIMBS) else pb.stall_speed(mass)
    opti = pb.PolarOpti(cd0=drag_of(slug), no_peak_below=start - 0.5)
    got = await formula(pb.bound_inputs(slug, mass=mass), pb.context(slug, opti))
    assert all(math.isfinite(v) for v in got.values())
    assert min(v for v, _ in opti.evaluations) >= start - 1e-9


@pytest.mark.parametrize(("slug", "formula"), ALL)
async def test_a_solver_failure_inside_the_flyable_range_still_ends_the_formula(
    slug: str, formula: Formula
) -> None:
    mass = 8.0 if slug in dict(CLIMBS) else 3.4
    start = climb_start(mass) if slug in dict(CLIMBS) else pb.stall_speed(mass)
    opti = pb.PolarOpti(no_peak_below=start + 3.0)
    with pytest.raises(FormulaError) as caught:
        await formula(pb.bound_inputs(slug, mass=mass), pb.context(slug, opti))
    assert caught.value.category is ErrorCategory.NOT_CONVERGED


@pytest.mark.parametrize(("slug", "formula"), LEVEL_LIKE)
async def test_the_level_and_turn_and_dive_scans_start_at_the_stall_speed(
    slug: str, formula: Formula
) -> None:
    opti = pb.PolarOpti(cd0=drag_of(slug))
    await formula(pb.bound_inputs(slug), pb.context(slug, opti))
    assert close(min(v for v, _ in opti.evaluations), pb.stall_speed(3.4), 1e-9)


@pytest.mark.parametrize(("slug", "formula"), CLIMBS)
async def test_the_climb_scans_start_at_the_stall_speed_of_the_steepest_angle_the_thrust_holds(
    slug: str, formula: Formula
) -> None:
    mass = 8.0  # W = 78.5 N, T_0 = 60 N: gamma_T = 49.9 deg, n = 0.64, start = 0.80 V_S
    opti = pb.PolarOpti()
    ctx = pb.context(slug, opti)
    await formula(pb.bound_inputs(slug, mass=mass), ctx)
    assert close(min(v for v, _ in opti.evaluations), climb_start(mass), 1e-9)
    assert "scan_floor" not in pb.limits(ctx)


@pytest.mark.parametrize(("slug", "formula"), CLIMBS)
async def test_a_climb_that_can_be_vertical_starts_at_the_floor_and_declares_it(
    slug: str, formula: Formula
) -> None:
    opti = pb.PolarOpti()  # 3.4 kg: T_0 = 60 N > W = 33.3 N, no lower stall bound from the angle
    ctx = pb.context(slug, opti)
    await formula(pb.bound_inputs(slug), ctx)
    assert close(min(v for v, _ in opti.evaluations), SCAN_FLOOR * pb.stall_speed(3.4), 1e-9)
    assert "scan_floor" in pb.limits(ctx)
