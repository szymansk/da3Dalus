"""The rule table: bands, levels, planned quantities, and its check against the canon model."""

from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.evaluation.rules import (
    Band,
    Position,
    RuleTable,
    Severity,
    check_rule_table,
    shipped_rule_table,
)
from aero_kernel.importer.rule_table import load_rule_table, main, render_rule_table
from aero_kernel.tests.evaluation_builders import rule_of, table_of
from pydantic import ValidationError

REPO = Path(__file__).resolve().parents[2]
DRELA = REPO / "_reversa_sdd" / "calculations" / "evaluation" / "drela.yaml"


def test_band_positions_include_both_ends_by_default() -> None:
    band = Band(min=0.05, max=0.15)
    assert band.position(0.05) is Position.INSIDE
    assert band.position(0.15) is Position.INSIDE
    assert band.position(0.049) is Position.BELOW
    assert band.position(0.151) is Position.ABOVE


def test_an_open_end_never_leaves_the_band_on_that_side() -> None:
    band = Band(min=5.0)
    assert band.position(1.0e9) is Position.INSIDE
    assert band.position(4.0) is Position.BELOW


def test_an_exclusive_end_is_outside() -> None:
    band = Band(min=5.0, min_inclusive=False)
    assert band.position(5.0) is Position.BELOW
    assert band.position(5.1) is Position.INSIDE


def test_a_band_needs_a_bound_and_min_below_max() -> None:
    with pytest.raises(ValidationError):
        Band()
    with pytest.raises(ValidationError):
        Band(min=2.0, max=1.0)


def test_a_side_may_have_no_meaning_where_the_source_names_none() -> None:
    rule = rule_of(above=None)
    assert rule.above is None
    assert rule.below == "Negative: unstable."


def test_a_meaning_for_a_side_the_band_lacks_is_rejected() -> None:
    with pytest.raises(ValidationError):
        rule_of(band={"min": 5.0})


def test_a_planned_marker_is_a_ticket_reference() -> None:
    with pytest.raises(ValidationError):
        rule_of(quantity={"slug": "x", "planned": "soon"})


def test_rule_ids_are_unique() -> None:
    rules = (rule_of(), rule_of())
    with pytest.raises(ValidationError):
        RuleTable(source="s", rules=rules)


def test_levels_are_matched_in_order() -> None:
    rule = rule_of(
        band={"min": 5.0, "min_inclusive": False},
        below="Unstable.",
        above=None,
        levels=[
            {"id": "manageable", "min": 3.0, "max": 4.0, "meaning": "Fine for an expert."},
            {"id": "unstable", "max": 5.0, "meaning": "Spirally unstable."},
        ],
    )
    assert rule.level_of(3.5) == "manageable"
    assert rule.level_of(4.5) == "unstable"
    assert rule.level_of(6.0) is None


def test_the_check_accepts_a_known_quantity_with_its_unit() -> None:
    model = load_canon_model()
    assert check_rule_table(table_of(rule_of()), model) == []


def test_the_check_rejects_an_unknown_quantity() -> None:
    model = load_canon_model()
    rule = rule_of(quantity={"slug": "no-such-quantity"})
    assert any("no-such-quantity" in p for p in check_rule_table(table_of(rule), model))


def test_the_check_rejects_a_unit_that_differs_from_the_canon() -> None:
    model = load_canon_model()
    problems = check_rule_table(table_of(rule_of(unit="deg")), model)
    assert any("unit" in p for p in problems)


def test_the_check_accepts_a_planned_quantity_the_canon_lacks() -> None:
    model = load_canon_model()
    rule = rule_of(quantity={"slug": "horizontal-tail-volume", "planned": "#1273"})
    assert check_rule_table(table_of(rule), model) == []


def test_the_check_rejects_a_stale_planned_marker() -> None:
    model = load_canon_model()
    rule = rule_of(quantity={"slug": "static-margin-target", "planned": "#1"})
    assert any("planned" in p for p in check_rule_table(table_of(rule), model))


def test_the_shipped_drela_table_is_consistent_with_the_canon() -> None:
    table = load_rule_table(DRELA)
    assert check_rule_table(table, load_canon_model()) == []


def test_the_shipped_table_holds_drelas_bands() -> None:
    table = {rule.id: rule for rule in load_rule_table(DRELA).rules}
    for rule_id, slug in (
        ("static-margin-design", "static-margin-target"),
        ("static-margin-measured", "static-margin-measured"),
    ):
        assert (table[rule_id].band.min, table[rule_id].band.max) == (0.05, 0.15)
        assert table[rule_id].quantity.slug == slug
    assert (table["horizontal-tail-volume"].band.min, table["horizontal-tail-volume"].band.max) == (
        0.30,
        0.60,
    )
    assert (table["vertical-tail-volume"].band.min, table["vertical-tail-volume"].band.max) == (
        0.02,
        0.05,
    )
    assert table["spiral-stability"].band.min == 5.0
    assert (table["rudder-roll-authority"].band.min, table["rudder-roll-authority"].band.max) == (
        0.10,
        0.20,
    )
    assert table["turn-sideslip"].band.max == 15.0
    assert table["turn-sideslip"].band.min is None


def test_every_not_yet_computable_rule_names_its_ticket() -> None:
    table = load_rule_table(DRELA)
    planned = {r.id: r.quantity.planned for r in table.rules if r.quantity.planned}
    assert planned == {
        "horizontal-tail-volume": "#1273",
        "rudder-roll-authority": "#1274",
        "turn-sideslip": "#1275",
    }


def test_the_shipped_json_equals_the_yaml() -> None:
    assert shipped_rule_table() == load_rule_table(DRELA)


def test_the_shipped_json_is_current() -> None:
    assert main([str(DRELA), "--check"]) == 0


def test_the_json_rendering_is_stable() -> None:
    table = load_rule_table(DRELA)
    first = render_rule_table(table)
    second = render_rule_table(load_rule_table(DRELA))
    assert first == second
    assert first.endswith("}\n")


def test_the_two_applications_of_the_static_margin_rule_do_not_drift_apart() -> None:
    table = {rule.id: rule for rule in load_rule_table(DRELA).rules}
    design, measured = table["static-margin-design"], table["static-margin-measured"]
    assert (design.band, design.below, design.above, design.source) == (
        measured.band,
        measured.below,
        measured.above,
        measured.source,
    )


def test_severity_defaults_to_bad_on_both_sides() -> None:
    rule = rule_of()
    assert rule.below_severity is Severity.BAD
    assert rule.above_severity is Severity.BAD


def test_a_side_can_be_a_caution_with_its_basis() -> None:
    rule = rule_of(above_severity="caution", above_basis="maintainer 2026-10-25")
    assert rule.above_severity is Severity.CAUTION
    assert rule.above_basis == "maintainer 2026-10-25"


def test_a_severity_for_a_side_the_band_lacks_is_rejected() -> None:
    with pytest.raises(ValidationError):
        rule_of(band={"min": 5.0}, above=None, above_severity="caution")


def test_a_basis_for_a_side_the_band_lacks_is_rejected() -> None:
    with pytest.raises(ValidationError):
        rule_of(band={"min": 5.0}, above=None, above_basis="x")


def test_the_rudder_roll_authority_above_side_is_a_caution_with_the_maintainers_basis() -> None:
    rule = {r.id: r for r in load_rule_table(DRELA).rules}["rudder-roll-authority"]
    assert rule.above_severity is Severity.CAUTION
    assert rule.above_basis is not None
    assert "maintainer 2026-10-25" in rule.above_basis
    assert (rule.band.min, rule.band.max) == (0.10, 0.20)


def test_a_rule_table_outside_the_working_directory_is_refused(tmp_path: Path) -> None:
    outside = tmp_path / "rules.yaml"
    outside.write_text("source: x\nrules: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inside"):
        load_rule_table(outside)


def test_a_rule_table_that_is_not_yaml_is_refused() -> None:
    with pytest.raises(ValueError, match="YAML"):
        load_rule_table(REPO / "aero_kernel" / "evaluation" / "rule_table.json")
