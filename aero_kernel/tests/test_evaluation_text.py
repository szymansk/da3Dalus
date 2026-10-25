"""The evaluation layer's LLM-facing contract: a self-contained text per verdict, a summary, and the run log."""

import logging
import math
from pathlib import Path

import pytest
from aero_kernel.evaluation.evaluator import RuleStatus, evaluate_rules, summarize_verdicts
from aero_kernel.evaluation.rules import Severity
from aero_kernel.importer.rule_table import load_rule_table
from aero_kernel.tests.evaluation_builders import (
    facts,
    not_applicable,
    ok,
    result_of,
    rule_of,
    spread,
    table_of,
)

SM = "static-margin-target"
LOGGER = "aero_kernel.evaluation"
DRELA = Path(__file__).resolve().parents[2] / "_reversa_sdd/calculations/evaluation/drela.yaml"
CAUTION_ABOVE = {"above_severity": "caution", "above_basis": "maintainer 2026-10-25"}


def verdict_text(value: float, **rule_fields: object) -> str:
    table = table_of(rule_of(**rule_fields))
    (verdict,) = evaluate_rules(table, result_of(ok(SM, value)), facts())
    return verdict.text


def test_the_text_of_a_value_above_the_band_is_self_contained() -> None:
    text = verdict_text(0.4, **CAUTION_ABOVE)
    assert text == (
        "Static margin (rule `static-margin`, Drela, Lab 11 Notes, Eq. (2)): "
        "`static-margin-target` = 0.4 lies above the band 0.05…0.15 — caution: "
        "Large trim changes with speed. (basis: maintainer 2026-10-25)"
    )


def test_the_text_of_a_value_below_the_band_names_its_severity_and_meaning() -> None:
    text = verdict_text(-0.02)
    assert "= -0.02 lies below the band 0.05…0.15 — bad: Negative: unstable." in text


def test_the_text_of_a_value_inside_the_band_says_so() -> None:
    assert verdict_text(0.1).endswith("= 0.1 lies inside the band 0.05…0.15.")


def test_the_unit_is_shown_unless_it_is_dimensionless() -> None:
    table = table_of(rule_of(unit="deg", band={"max": 15.0}, below=None))
    (verdict,) = evaluate_rules(table, result_of(ok(SM, 20.0, "deg")), facts())
    assert "= 20 deg lies above" in verdict.text


def test_an_interval_text_lists_its_worlds() -> None:
    table = table_of(rule_of())
    (verdict,) = evaluate_rules(table, result_of(spread(SM, 0.10, 0.30)), facts())
    assert "0.1…0.3" in verdict.text
    assert "neutral-point=a: 0.1" in verdict.text
    assert "neutral-point=b: 0.3" in verdict.text
    assert verdict.status is RuleStatus.PARTLY


def test_a_verdict_without_a_judgement_still_names_rule_and_quantity() -> None:
    table = table_of(rule_of())
    (missing,) = evaluate_rules(table, result_of(), facts())
    (inapplicable,) = evaluate_rules(table, result_of(not_applicable(SM)), facts())
    for verdict in (missing, inapplicable):
        assert verdict.text.startswith("Static margin (rule `static-margin`, ")
        assert f"`{SM}`" in verdict.text
        assert verdict.quantity == SM


def test_the_shipped_table_words_a_vertical_tail_volume_caution() -> None:
    table = load_rule_table(DRELA)
    verdicts = evaluate_rules(
        table, result_of(ok("vertical-tail-volume", 0.061)), facts(has_vertical_tail=True)
    )
    text = {v.rule_id: v.text for v in verdicts}["vertical-tail-volume"]
    assert "`vertical-tail-volume` = 0.061 lies above the band 0.02…0.05 — caution:" in text
    assert "drag and mass" in text
    assert "maintainer 2026-10-25" in text


def test_the_summary_counts_then_lists_red_before_yellow() -> None:
    table = table_of(
        rule_of(id="fine"),
        rule_of(id="yellow", quantity={"slug": "q-yellow"}, **CAUTION_ABOVE),
        rule_of(id="red", quantity={"slug": "q-red"}),
        rule_of(id="gone", quantity={"slug": "q-gone"}),
        rule_of(id="later", quantity={"slug": "q-later", "planned": "#9"}),
    )
    result = result_of(
        ok(SM, 0.1), ok("q-yellow", 0.4), ok("q-red", -0.1), not_applicable("q-gone")
    )
    verdicts = evaluate_rules(table, result, facts())
    summary = summarize_verdicts(table, verdicts)
    lines = summary.splitlines()
    assert lines[0] == (
        "Evaluation against Drela, Lab 11 Notes: 5 rules, 1 inside, 1 bad (red), "
        "1 caution (yellow), 1 not applicable, 1 not available."
    )
    assert lines[1] == "Red:"
    assert "`q-red`" in lines[2]
    assert lines[3] == "Yellow:"
    assert "`q-yellow`" in lines[4]
    assert len(lines) == 5


def test_a_clean_summary_has_no_red_or_yellow_section() -> None:
    table = table_of(rule_of())
    summary = summarize_verdicts(table, evaluate_rules(table, result_of(ok(SM, 0.1)), facts()))
    assert summary == (
        "Evaluation against Drela, Lab 11 Notes: 1 rules, 1 inside, 0 bad (red), "
        "0 caution (yellow), 0 not applicable, 0 not available."
    )


def records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.name == LOGGER]


def test_a_red_verdict_is_logged_at_info_with_structured_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    table = table_of(rule_of())
    with caplog.at_level(logging.INFO, logger=LOGGER):
        evaluate_rules(table, result_of(ok(SM, -0.02)), facts(), call_id="abc123")
    (record,) = records(caplog)
    assert record.levelno == logging.INFO
    assert record.getMessage() == evaluate_rules(table, result_of(ok(SM, -0.02)), facts())[0].text
    fields = record.__dict__
    assert fields["verdict"] == "evaluation"
    assert fields["call_id"] == "abc123"
    assert fields["rule_id"] == "static-margin"
    assert fields["quantity"] == SM
    assert fields["severity"] == Severity.BAD.value
    assert fields["status"] == RuleStatus.BELOW.value
    assert math.isclose(fields["value"], -0.02)
    assert math.isclose(fields["band_min"], 0.05)
    assert math.isclose(fields["band_max"], 0.15)


def test_a_yellow_verdict_is_logged_at_info_with_severity_caution(
    caplog: pytest.LogCaptureFixture,
) -> None:
    table = table_of(rule_of(**CAUTION_ABOVE))
    with caplog.at_level(logging.INFO, logger=LOGGER):
        evaluate_rules(table, result_of(ok(SM, 0.4)), facts())
    (record,) = records(caplog)
    assert record.levelno == logging.INFO
    assert record.__dict__["severity"] == "caution"


def test_an_interval_verdict_logs_its_ends(caplog: pytest.LogCaptureFixture) -> None:
    table = table_of(rule_of())
    with caplog.at_level(logging.INFO, logger=LOGGER):
        evaluate_rules(table, result_of(spread(SM, 0.10, 0.30)), facts())
    (record,) = records(caplog)
    fields = record.__dict__
    assert fields["value"] is None
    assert math.isclose(fields["interval_min"], 0.1)
    assert math.isclose(fields["interval_max"], 0.3)


def test_inside_and_unjudged_verdicts_are_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    table = table_of(
        rule_of(id="fine"),
        rule_of(id="gone", quantity={"slug": "q-gone"}),
        rule_of(id="later", quantity={"slug": "q-later", "planned": "#9"}),
    )
    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        evaluate_rules(table, result_of(ok(SM, 0.1), not_applicable("q-gone")), facts())
    assert records(caplog) == []
