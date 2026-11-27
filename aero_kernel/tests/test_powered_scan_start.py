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
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas import powered_flight as pf
from aero_kernel.formulas.best_angle_of_climb import best_angle_of_climb
from aero_kernel.formulas.best_rate_of_climb import best_rate_of_climb
from aero_kernel.formulas.dive_speed import dive_speed
from aero_kernel.formulas.max_level_speed import max_level_speed
from aero_kernel.formulas.max_sustained_turn_rate import max_sustained_turn_rate
from aero_kernel.formulas.min_sustained_turn_radius import min_sustained_turn_radius
from aero_kernel.schema import AircraftInput, QuantityStatus
from aero_kernel.solvers.opti import Stall
from aero_kernel.tests import powered_builders as pb
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, solvers_with
from aero_kernel.tests.wing_builders import airplane_document

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


SLUGS = [slug for slug, _ in ALL]


async def test_the_scan_has_no_point_beyond_the_limit() -> None:
    assert list(pf.scan_speeds(200.0)) == []
    assert list(pf.scan_speeds(150.0)) == [150.0]


@pytest.mark.parametrize("slug", SLUGS)
async def test_every_entry_carries_the_stall_speed_precondition(slug: str) -> None:
    formula = shipped_build().model.formula(slug)
    assert formula is not None
    (check,) = [p for p in formula.preconditions if p.id == "stall_speed_usable"]
    assert (check.parameter, check.on_violation) == ("v_s", "error")


@pytest.mark.parametrize("v_s", [9.5, 150.0])
async def test_a_usable_stall_speed_passes_its_precondition(v_s: float) -> None:
    x = pb.bound_inputs("max-level-speed", **{"stall-speed": v_s})
    assert pf.stall_speed_usable(x).state == "held"


@pytest.mark.parametrize("v_s", [0.0, -3.0, math.nan, math.inf, 150.5])
async def test_a_stall_speed_that_is_not_positive_finite_and_inside_the_scan_violates_it(
    v_s: float,
) -> None:
    x = pb.bound_inputs("max-level-speed", **{"stall-speed": v_s})
    result = pf.stall_speed_usable(x)
    assert result.state == "violated"
    assert "stall speed" in result.message


def table_end(v: float) -> FormulaError:
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION, "outside_propeller_table", f"edge at {v}", "none"
    )


async def test_without_a_static_thrust_the_climb_starts_at_the_floor_and_says_why(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A table without a J = 0 point: the thrust at no airspeed does not exist (declared, no extrapolation)."""

    def thrust(*args: Any, **kwargs: Any) -> float:
        if args[2] == 0.0:
            raise table_end(0.0)
        return 20.0

    monkeypatch.setattr(pf, "full_throttle_thrust", thrust)
    airplane = pf.PoweredFlight(
        pb.bound_inputs("best-angle-of-climb"), pb.context("best-angle-of-climb", pb.PolarOpti())
    )
    assert close(airplane.climb_scan_start(), SCAN_FLOOR * pb.stall_speed(3.4), 1e-12)
    await airplane.answer(20.0, 1.0)
    (notice,) = [w for w in airplane.ctx.warnings if w.detail.get("limit") == "scan_floor"]
    assert "no static thrust" in notice.message


async def test_a_thrust_above_the_static_thrust_at_some_speed_is_declared(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The start rests on the static thrust being the largest; where the table gives more at a speed, the
    start may have been too high, and that is declared."""

    def rising(*args: Any, **kwargs: Any) -> float:
        return 25.0 + args[2]

    monkeypatch.setattr(pf, "full_throttle_thrust", rising)
    airplane = pf.PoweredFlight(
        pb.bound_inputs("best-angle-of-climb"), pb.context("best-angle-of-climb", pb.PolarOpti())
    )
    airplane.climb_scan_start()
    assert airplane.thrust(10.0) == 35.0
    await airplane.answer(20.0, 1.0)
    (notice,) = [
        w for w in airplane.ctx.warnings if w.detail.get("limit") == "static_thrust_not_largest"
    ]
    assert notice.detail["v_ms"] == 10.0


async def test_a_static_thrust_that_is_the_largest_declares_nothing_more(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def falling(*args: Any, **kwargs: Any) -> float:
        return 40.0 - args[2]

    monkeypatch.setattr(pf, "full_throttle_thrust", falling)
    airplane = pf.PoweredFlight(
        pb.bound_inputs("best-angle-of-climb"), pb.context("best-angle-of-climb", pb.PolarOpti())
    )
    airplane.climb_scan_start()
    airplane.thrust(10.0)
    await airplane.answer(20.0, 1.0)
    assert not [
        w for w in airplane.ctx.warnings if w.detail.get("limit") == "static_thrust_not_largest"
    ]


STALL_FAILURE = "the optimum of the stall problem lies on the bound of alpha"


class FailingStallOpti(pb.PolarOpti):
    """The stall problem of the airframe does not converge (the message AERONCA_CHAMP gave before gh-1423)."""

    async def stall(self, *args: Any, **kwargs: Any) -> Stall:
        raise FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", STALL_FAILURE, "none")


QUANTITIES = [
    "max-level-speed",
    "dive-speed",
    "best-rate-of-climb-speed",
    "best-angle-of-climb-speed",
    "max-sustained-turn-rate",
    "min-sustained-turn-radius",
]


@pytest.mark.parametrize("slug", QUANTITIES)
async def test_a_stall_speed_that_does_not_converge_ends_the_powered_formula_upstream_failed(
    slug: str,
) -> None:
    """The single-producer coupling: no stall speed, no powered value, no substitute (gh-1419)."""
    document = {
        "airplane": airplane_document(),
        "values": {"aircraft-mass": 3.4, "altitude": 0.0},
        "components": complete_components_with_table().model_dump(),
    }
    result = await evaluate(
        shipped_build(),
        AircraftInput.model_validate(document),
        request(slug, "stall-speed"),
        solvers=solvers_with(opti=FailingStallOpti()),
    )
    got = {q.slug: q for q in result.quantities}
    powered = [q for q in result.quantities if q.slug != "stall-speed"]
    assert got["stall-speed"].error is not None
    assert got["stall-speed"].error.message == STALL_FAILURE
    for quantity in powered:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.error is not None
        assert quantity.error.code == "upstream_failed"
        assert "stall-speed" in quantity.error.message
