"""The extraction of ``highest_level_speed`` and ``best_climb`` left the two formulas unchanged (gh-1420).

``mass-envelope`` evaluates the search functions of ``max-level-speed`` and ``best-rate-of-climb`` at each mass of
its sweep, so the two formulas were split into a search function and the evaluation of the answer. The values
and warnings below are the ones recorded from ``github/main`` before the extraction, on the same stub polar and
drive train as ``test_powered_performance`` (a pure move: bit-identical). The flag ``declare`` of
``PoweredFlight.answer`` is pinned here too.
"""

from typing import Any

import pytest
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.best_rate_of_climb import best_climb, best_rate_of_climb
from aero_kernel.formulas.max_level_speed import highest_level_speed, max_level_speed
from aero_kernel.formulas.powered_flight import LEVEL_FLIGHT, PoweredFlight, Unflyable, finish_climb
from aero_kernel.schema import KernelWarning
from aero_kernel.tests import powered_builders as pb

pytestmark = pytest.mark.asyncio

NOTICE = KernelWarning.of("induced_drag_viscous_factor_removed", "the stub's drag notice")
RECORDED_V_MAX = 31.59250015577315  # from github/main, before the extraction
RECORDED_V_Y, RECORDED_ROC = 17.13578192930768, 9.317399210317785


async def test_max_level_speed_is_the_value_and_the_warnings_recorded_before_the_extraction() -> (
    None
):
    ctx = pb.context("max-level-speed", pb.PolarOpti(warnings=(NOTICE,)))
    got = await max_level_speed(pb.bound_inputs("max-level-speed"), ctx)
    assert got == {"v_max": RECORDED_V_MAX}
    assert [w.code for w in ctx.warnings] == [
        "induced_drag_viscous_factor_removed",
        "powertrain_route_winding_resistance",
    ]


async def test_best_rate_of_climb_is_the_value_the_warnings_and_the_limit_recorded_before_the_extraction() -> (
    None
):
    ctx = pb.context("best-rate-of-climb", pb.PolarOpti(warnings=(NOTICE,)))
    got = await best_rate_of_climb(pb.bound_inputs("best-rate-of-climb"), ctx)
    assert got == {"v_y": RECORDED_V_Y, "roc_max": RECORDED_ROC}
    assert [w.code for w in ctx.warnings] == [
        "induced_drag_viscous_factor_removed",
        "powertrain_route_winding_resistance",
        "powered_speeds_skipped",
        "powered_limit_declared",
    ]
    assert pb.limits(ctx) == ["scan_floor"]


@pytest.mark.parametrize(
    ("slug", "cd0", "code"),
    [
        ("max-level-speed", 2.0, "no_feasible_speed"),
        ("max-level-speed", 1e-5, "outside_propeller_table"),
        ("best-rate-of-climb", 2.0, "no_feasible_speed"),
    ],
)
async def test_the_failure_codes_of_the_two_formulas_are_those_recorded_before_the_extraction(
    slug: str, cd0: float, code: str
) -> None:
    formula = max_level_speed if slug == "max-level-speed" else best_rate_of_climb
    ctx = pb.context(slug, pb.PolarOpti(cd0=cd0))
    with pytest.raises(FormulaError) as caught:
        await formula(pb.bound_inputs(slug), ctx)
    assert caught.value.code == code


@pytest.mark.parametrize("slug", ["max-level-speed", "best-rate-of-climb"])
async def test_an_absent_winding_resistance_is_missing_input_in_both_formulas(slug: str) -> None:
    formula = max_level_speed if slug == "max-level-speed" else best_rate_of_climb
    absent: dict[str, Any] = {"motor-circuit-resistance": None}
    with pytest.raises(FormulaError) as caught:
        await formula(pb.bound_inputs(slug, **absent), pb.context(slug))
    assert caught.value.code == "missing_input"


async def test_the_search_functions_alone_forward_and_declare_nothing_and_give_the_formulas_values() -> (
    None
):
    """``highest_level_speed`` and ``best_climb`` are the formulas' searches without the answer: the same
    values, no warning, no route notice (the caller evaluates its answer)."""
    ctx = pb.context("max-level-speed", pb.PolarOpti(warnings=(NOTICE,)))
    flight = PoweredFlight(pb.bound_inputs("max-level-speed"), ctx)
    assert await highest_level_speed(flight) == RECORDED_V_MAX
    assert ctx.warnings == ()
    ctx = pb.context("best-rate-of-climb", pb.PolarOpti(warnings=(NOTICE,)))
    flight = PoweredFlight(pb.bound_inputs("best-rate-of-climb"), ctx)
    optimum, _ = await best_climb(flight)
    assert (optimum.v, optimum.value) == (RECORDED_V_Y, RECORDED_ROC)
    assert ctx.warnings == ()


async def test_declare_false_forwards_the_answers_warnings_and_declares_neither_route_nor_skipped_speeds() -> (
    None
):
    ctx = pb.context("max-level-speed", pb.PolarOpti(warnings=(NOTICE,)))
    flight = PoweredFlight(pb.bound_inputs("max-level-speed"), ctx)
    flight.note_skipped(2.0, Unflyable.WING)  # a skipped speed to declare
    await flight.answer(RECORDED_V_MAX, LEVEL_FLIGHT, declare=False)
    assert [w.code for w in ctx.warnings] == ["induced_drag_viscous_factor_removed"]


async def test_declare_true_is_the_default_and_declares_the_route_and_the_skipped_speeds() -> None:
    ctx = pb.context("max-level-speed", pb.PolarOpti(warnings=(NOTICE,)))
    flight = PoweredFlight(pb.bound_inputs("max-level-speed"), ctx)
    flight.note_skipped(2.0, Unflyable.WING)
    await flight.answer(RECORDED_V_MAX, LEVEL_FLIGHT)
    assert [w.code for w in ctx.warnings] == [
        "induced_drag_viscous_factor_removed",
        "powertrain_route_winding_resistance",
        "powered_speeds_skipped",
    ]


async def test_finish_climb_on_the_extracted_search_gives_the_formulas_answer_warnings() -> None:
    ctx = pb.context("best-rate-of-climb", pb.PolarOpti(warnings=(NOTICE,)))
    flight = PoweredFlight(pb.bound_inputs("best-rate-of-climb"), ctx)
    optimum, gamma = await best_climb(flight)
    await finish_climb(flight, optimum, gamma)
    assert next(w.code for w in ctx.warnings) == "induced_drag_viscous_factor_removed"
    assert "powered_limit_declared" in [w.code for w in ctx.warnings]
