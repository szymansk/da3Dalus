"""The evaluator: a pure function from a rule table and a kernel result to verdicts."""

import logging
from collections.abc import Callable

import pytest
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.evaluation.evaluator import (
    RuleStatus,
    RuleVerdict,
    evaluate_rules,
    judge_result,
    quantities_to_request,
)
from aero_kernel.evaluation.rules import Severity, shipped_rule_table
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import WhenFacts
from aero_kernel.reference_fleet import FleetMember, reference_document
from aero_kernel.schema import (
    ComputeResult,
    CurveResult,
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
)
from aero_kernel.tests.evaluation_builders import (
    facts,
    not_applicable,
    not_given,
    ok,
    result_of,
    rule_of,
    spread,
    table_of,
)

SM = "static-margin-target"
LOGGER = "aero_kernel.evaluation"


def errored(slug: str) -> QuantityResult:
    """A quantity the kernel could not compute: status error with its KernelError."""
    error = KernelError(
        code="internal",
        category=ErrorCategory.INTERNAL,
        message="the formula failed",
        hint="a hint",
    )
    return QuantityResult(slug=slug, status=QuantityStatus.ERROR, error=error)


def skipped(slug: str) -> QuantityResult:
    """A quantity the kernel left out of this run: status skipped with its Reason."""
    return QuantityResult(
        slug=slug,
        status=QuantityStatus.SKIPPED,
        reason=Reason(code=ReasonCode.LONG_RUN_NOT_INCLUDED, message="Long run left out."),
    )


def judge(
    result: ComputeResult, geometry: WhenFacts | None = None, **rule_fields: object
) -> RuleVerdict:
    """The single verdict of one rule over ``static-margin-target``."""
    verdicts = evaluate_rules(table_of(rule_of(**rule_fields)), result, geometry or facts())
    assert len(verdicts) == 1
    return verdicts[0]


def test_a_value_in_the_band_is_inside() -> None:
    verdict = judge(result_of(ok(SM, 0.10)))
    assert verdict.status is RuleStatus.INSIDE
    assert verdict.value is not None
    assert abs(verdict.value - 0.10) < 1e-12
    assert "Eq. (2)" in verdict.text


def test_a_value_below_the_band_carries_drelas_meaning() -> None:
    verdict = judge(result_of(ok(SM, -0.02)))
    assert verdict.status is RuleStatus.BELOW
    assert "Negative: unstable." in verdict.explanation


def test_a_value_above_the_band_carries_drelas_meaning() -> None:
    verdict = judge(result_of(ok(SM, 0.4)))
    assert verdict.status is RuleStatus.ABOVE
    assert "Large trim changes with speed." in verdict.explanation


def test_an_interval_inside_the_band_is_inside() -> None:
    verdict = judge(result_of(spread(SM, 0.06, 0.14)))
    assert verdict.status is RuleStatus.INSIDE
    assert verdict.interval is not None
    assert verdict.value is None


def test_an_interval_that_straddles_the_band_is_partly_inside() -> None:
    verdict = judge(result_of(spread(SM, 0.10, 0.30)))
    assert verdict.status is RuleStatus.PARTLY
    assert "Large trim changes with speed." in verdict.explanation


def test_an_interval_wholly_below_is_below() -> None:
    assert judge(result_of(spread(SM, -0.1, 0.0))).status is RuleStatus.BELOW


def test_an_interval_wholly_above_is_above() -> None:
    assert judge(result_of(spread(SM, 0.2, 0.3))).status is RuleStatus.ABOVE


def test_an_interval_straddling_both_ends_names_both_meanings() -> None:
    verdict = judge(result_of(spread(SM, 0.0, 0.3)))
    assert verdict.status is RuleStatus.PARTLY
    assert "Negative: unstable." in verdict.explanation
    assert "Large trim changes with speed." in verdict.explanation


def test_a_quantity_missing_from_the_result_is_not_available() -> None:
    verdict = judge(result_of())
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert verdict.value is None


def test_a_value_per_control_surface_is_not_judged_by_a_band() -> None:
    per_surface = QuantityResult(
        slug=SM,
        unit="1",
        status=QuantityStatus.OK,
        surfaces={"Main wing.aileron_right": {"aileron": 0.1}},
        tool="AVL",
        application="aileron",
    )
    verdict = judge(result_of(per_surface))
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "per control surface" in verdict.explanation


def test_a_curve_is_not_judged_by_a_band() -> None:
    curve = QuantityResult(
        slug=SM,
        unit="1",
        status=QuantityStatus.OK,
        curve=CurveResult(x=(0.0, 1.0), y=(0.1, 0.2), x_quantity="crow-mix", x_unit="1"),
        tool="OPT",
        application="crow",
    )
    verdict = judge(result_of(curve))
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "is a curve" in verdict.explanation


def test_a_planned_quantity_is_not_available_and_names_its_ticket() -> None:
    verdict = judge(result_of(), quantity={"slug": "horizontal-tail-volume", "planned": "#1273"})
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "#1273" in verdict.explanation


def test_a_quantity_the_kernel_found_not_applicable_is_not_applicable() -> None:
    verdict = judge(result_of(not_applicable(SM)))
    assert verdict.status is RuleStatus.NOT_APPLICABLE
    assert "No fin." in verdict.explanation


def test_a_missing_geometry_condition_makes_the_rule_not_applicable() -> None:
    verdict = judge(result_of(ok(SM, 0.1)), facts(), when=["has_vertical_tail"])
    assert verdict.status is RuleStatus.NOT_APPLICABLE
    assert "has_vertical_tail" in verdict.explanation


def test_a_met_geometry_condition_lets_the_rule_apply() -> None:
    verdict = judge(
        result_of(ok(SM, 0.1)), facts(has_vertical_tail=True), when=["has_vertical_tail"]
    )
    assert verdict.status is RuleStatus.INSIDE


def test_an_excluded_term_that_holds_makes_the_rule_not_applicable() -> None:
    verdict = judge(result_of(ok(SM, 0.1)), facts(has_aileron=True), when_not=["has_aileron"])
    assert verdict.status is RuleStatus.NOT_APPLICABLE
    assert "has_aileron" in verdict.explanation


def test_an_excluded_term_that_does_not_hold_lets_the_rule_apply() -> None:
    verdict = judge(result_of(ok(SM, 0.1)), facts(), when_not=["has_aileron"])
    assert verdict.status is RuleStatus.INSIDE


def test_a_condition_without_a_fact_yet_is_not_available(pending_horizontal_tail: None) -> None:
    verdict = judge(result_of(ok(SM, 0.1)), when=["has_horizontal_tail"])
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "has_horizontal_tail" in verdict.explanation


def test_not_applicable_wins_over_planned() -> None:
    verdict = judge(
        result_of(),
        facts(has_aileron=True),
        quantity={"slug": "x", "planned": "#9"},
        when_not=["has_aileron"],
    )
    assert verdict.status is RuleStatus.NOT_APPLICABLE


def test_the_level_of_a_value_is_reported() -> None:
    verdict = judge(
        result_of(ok(SM, 0.03)),
        levels=[{"id": "weak", "min": 0.0, "max": 0.05, "meaning": "Weakly stable."}],
    )
    assert verdict.level == "weak"
    assert "Weakly stable." in verdict.explanation


def test_one_verdict_per_rule_in_table_order() -> None:
    table = table_of(rule_of(id="a"), rule_of(id="b"))
    verdicts = evaluate_rules(table, result_of(ok(SM, 0.1)), facts())
    assert [v.rule_id for v in verdicts] == ["a", "b"]


def test_the_quantities_a_table_needs_exclude_the_planned_ones() -> None:
    table = table_of(
        rule_of(id="a"),
        rule_of(id="b", quantity={"slug": "later", "planned": "#5"}),
        rule_of(id="c"),
    )
    assert quantities_to_request(table) == (SM,)


def test_the_shipped_table_judges_a_hand_made_result() -> None:
    from pathlib import Path

    from aero_kernel.importer.rule_table import load_rule_table

    path = Path(__file__).resolve().parents[2] / "_reversa_sdd/calculations/evaluation/drela.yaml"
    table = load_rule_table(path)
    result = result_of(
        ok("static-margin-target", 0.08),
        ok("vertical-tail-volume", 0.01),
        ok("spiral-parameter-md", 5.0),
        ok("horizontal-tail-volume", 0.2),
        ok("turn-sideslip", 8.0, "deg"),
        ok("turn-sideslip-gain", 1.1),
    )
    flags = facts(has_vertical_tail=True, has_horizontal_tail=True)
    verdicts = {v.rule_id: v for v in evaluate_rules(table, result, flags)}
    assert verdicts["static-margin-design"].status is RuleStatus.INSIDE
    assert verdicts["static-margin-measured"].status is RuleStatus.NOT_AVAILABLE
    assert verdicts["vertical-tail-volume"].status is RuleStatus.BELOW
    assert verdicts["spiral-stability"].status is RuleStatus.BELOW  # B = 5 is neutral, not stable
    assert verdicts["horizontal-tail-volume"].status is RuleStatus.BELOW
    assert verdicts["turn-sideslip"].status is RuleStatus.INSIDE
    with_aileron = {v.rule_id: v for v in evaluate_rules(table, result, facts(has_aileron=True))}
    assert with_aileron["turn-sideslip"].status is RuleStatus.NOT_APPLICABLE


def test_a_side_without_a_meaning_says_the_source_names_no_consequence() -> None:
    verdict = judge(result_of(ok(SM, 0.4)), above=None)
    assert verdict.status is RuleStatus.ABOVE
    assert "names no consequence" in verdict.explanation


def test_a_quantity_the_caller_did_not_supply_is_not_available_not_not_applicable() -> None:
    verdict = judge(result_of(not_given(SM)))
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "No CG." in verdict.explanation


def test_a_value_below_the_band_carries_that_sides_severity() -> None:
    assert judge(result_of(ok(SM, -0.02))).severity is Severity.BAD
    assert judge(result_of(ok(SM, 0.4)), above_severity="caution").severity is Severity.CAUTION


def test_a_value_inside_the_band_has_no_severity() -> None:
    assert judge(result_of(ok(SM, 0.1)), above_severity="caution").severity is None


def test_an_interval_reaching_both_sides_takes_the_worst_severity() -> None:
    verdict = judge(result_of(spread(SM, 0.0, 0.3)), above_severity="caution")
    assert verdict.severity is Severity.BAD
    verdict = judge(result_of(spread(SM, 0.10, 0.3)), above_severity="caution")
    assert verdict.severity is Severity.CAUTION


def test_the_basis_of_a_side_is_in_the_explanation() -> None:
    verdict = judge(result_of(ok(SM, 0.4)), above_severity="caution", above_basis="maintainer")
    assert "maintainer" in verdict.explanation
    assert "caution" in verdict.explanation


def test_a_vertical_tail_volume_above_the_band_is_a_caution_below_it_is_bad() -> None:
    from pathlib import Path

    from aero_kernel.importer.rule_table import load_rule_table

    path = Path(__file__).resolve().parents[2] / "_reversa_sdd/calculations/evaluation/drela.yaml"
    table = load_rule_table(path)
    flags = facts(has_vertical_tail=True)
    high = {
        v.rule_id: v
        for v in evaluate_rules(table, result_of(ok("vertical-tail-volume", 0.09)), flags)
    }
    low = {
        v.rule_id: v
        for v in evaluate_rules(table, result_of(ok("vertical-tail-volume", 0.01)), flags)
    }
    assert high["vertical-tail-volume"].status is RuleStatus.ABOVE
    assert high["vertical-tail-volume"].severity is Severity.CAUTION
    assert low["vertical-tail-volume"].severity is Severity.BAD


def test_judge_result_applies_the_shipped_table_to_a_fleet_geometry() -> None:
    airplane = AirplaneGeometry.model_validate(reference_document(FleetMember.BRYAN))
    result = result_of(ok("horizontal-tail-volume", 0.5))
    verdicts = judge_result(result, airplane)
    assert [v.rule_id for v in verdicts] == [r.id for r in shipped_rule_table().rules]
    judged = {v.rule_id: v for v in verdicts}
    assert judged["horizontal-tail-volume"].value == 0.5


@pytest.mark.parametrize(
    ("builder", "word"), [(errored, "status error"), (skipped, "status skipped")]
)
def test_a_quantity_without_a_value_is_not_available_not_not_applicable(
    builder: Callable[[str], QuantityResult], word: str, caplog: pytest.LogCaptureFixture
) -> None:
    """P7b-F01: an error or skipped quantity is a missing value, never "the rule does not apply"."""
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        verdict = judge(result_of(builder(SM)))
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert verdict.value is None
    assert verdict.interval is None
    assert verdict.severity is None
    assert word in verdict.explanation
    assert "not applicable" not in verdict.explanation
    assert [r for r in caplog.records if r.name == LOGGER] == []


LEVELS = [
    {"id": "weak", "min": 0.0, "max": 0.05, "meaning": "Weakly stable."},
    {"id": "firm", "min": 0.05, "min_inclusive": False, "max": 0.15, "meaning": "Firmly stable."},
]


def test_an_interval_across_two_levels_has_no_level() -> None:
    """P7b-F06: ends in "weak" (0.03) and "firm" (0.10): one level only if both ends share it."""
    verdict = judge(
        result_of(spread(SM, 0.03, 0.10)), levels=LEVELS, band={"min": 0.0, "max": 0.15}
    )
    assert verdict.status is RuleStatus.INSIDE
    assert verdict.level is None
    assert "Level" not in verdict.explanation


def test_an_interval_within_one_level_has_that_level() -> None:
    """Both ends (0.06, 0.10) lie in "firm" (0.05 < x <= 0.15)."""
    verdict = judge(result_of(spread(SM, 0.06, 0.10)), levels=LEVELS)
    assert verdict.level == "firm"
    assert "Level firm: Firmly stable." in verdict.explanation


def test_an_interval_outside_every_level_has_no_level() -> None:
    """Both ends (0.2, 0.3) lie above the last level (max 0.15)."""
    verdict = judge(result_of(spread(SM, 0.2, 0.3)), levels=LEVELS)
    assert verdict.level is None
    assert "Level" not in verdict.explanation


def test_a_pending_excluded_term_is_not_available(pending_horizontal_tail: None) -> None:
    """P7b-F14: a pending term in when_not has no fact yet, the same as one in when."""
    verdict = judge(result_of(ok(SM, 0.1)), when_not=["has_horizontal_tail"])
    assert verdict.status is RuleStatus.NOT_AVAILABLE
    assert "#1187" in verdict.explanation


def test_values_on_the_band_edges_are_inside() -> None:
    """P7b-F07: band 0.05..0.15 includes both ends; the evaluator hands exact ends to the band."""
    for edge in (0.05, 0.15):
        verdict = judge(result_of(ok(SM, edge)))
        assert verdict.status is RuleStatus.INSIDE
        assert verdict.severity is None
    interval = judge(result_of(spread(SM, 0.05, 0.15)))
    assert interval.status is RuleStatus.INSIDE
    assert interval.severity is None


def test_an_interval_end_just_above_the_band_is_partly() -> None:
    """0.1500001 > 0.15 although it prints as 0.15 at four digits: only the above meaning."""
    verdict = judge(result_of(spread(SM, 0.05, 0.1500001)))
    assert verdict.status is RuleStatus.PARTLY
    assert "Large trim changes with speed." in verdict.explanation
    assert "Negative: unstable." not in verdict.explanation


def test_a_value_just_below_the_band_is_below_although_it_prints_as_the_edge() -> None:
    """0.04999999 < 0.05 although it prints as 0.05 at four digits: no rounding before judging."""
    assert judge(result_of(ok(SM, 0.04999999))).status is RuleStatus.BELOW


def test_an_interval_starting_on_an_exclusive_edge_is_partly() -> None:
    """With min 0.05 exclusive, the end 0.05 is below, the end 0.10 inside: partly."""
    verdict = judge(
        result_of(spread(SM, 0.05, 0.10)), band={"min": 0.05, "max": 0.15, "min_inclusive": False}
    )
    assert verdict.status is RuleStatus.PARTLY
    assert "Negative: unstable." in verdict.explanation
