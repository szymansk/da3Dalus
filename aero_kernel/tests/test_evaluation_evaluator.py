"""The evaluator: a pure function from a rule table and a kernel result to verdicts."""

from aero_kernel.evaluation.evaluator import (
    RuleStatus,
    RuleVerdict,
    evaluate_rules,
    quantities_to_request,
)
from aero_kernel.evaluation.rules import Severity
from aero_kernel.graph import WhenFacts
from aero_kernel.schema import ComputeResult
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


def test_a_condition_without_a_fact_yet_is_not_available() -> None:
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
        ok("spiral-parameter", 5.0),
    )
    verdicts = {v.rule_id: v for v in evaluate_rules(table, result, facts(has_vertical_tail=True))}
    assert verdicts["static-margin-design"].status is RuleStatus.INSIDE
    assert verdicts["static-margin-measured"].status is RuleStatus.NOT_AVAILABLE
    assert verdicts["vertical-tail-volume"].status is RuleStatus.BELOW
    assert verdicts["spiral-stability"].status is RuleStatus.BELOW  # B = 5 is neutral, not stable
    assert verdicts["horizontal-tail-volume"].status is RuleStatus.NOT_AVAILABLE
    assert verdicts["turn-sideslip"].status is RuleStatus.NOT_AVAILABLE


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
