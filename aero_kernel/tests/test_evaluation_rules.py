"""The rule table: bands, levels, planned quantities, and its check against the canon model."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from aero_kernel.canon.load import load_canon_model
from aero_kernel.evaluation import rules as rules_module
from aero_kernel.evaluation.evaluator import RuleStatus, RuleVerdict, evaluate_rules
from aero_kernel.evaluation.rules import (
    Band,
    Position,
    RuleTable,
    Severity,
    check_rule_table,
    shipped_rule_table,
)
from aero_kernel.importer.rule_table import load_rule_table, main, render_rule_table
from aero_kernel.tests.evaluation_builders import facts, ok, result_of, rule_dict, rule_of, table_of
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


def test_an_exclusive_upper_end_is_outside() -> None:
    """P7b-F05: with max_inclusive False the value on the edge is above, just under it inside."""
    band = Band(max=15.0, max_inclusive=False)
    assert band.position(15.0) is Position.ABOVE
    assert band.position(14.9) is Position.INSIDE


def test_a_band_with_both_ends_exclusive_excludes_both_edges() -> None:
    band = Band(min=0.0, max=1.0, min_inclusive=False, max_inclusive=False)
    assert band.position(0.0) is Position.BELOW
    assert band.position(1.0) is Position.ABOVE
    assert band.position(0.5) is Position.INSIDE


def test_a_band_needs_a_bound_and_min_below_max() -> None:
    with pytest.raises(ValidationError):
        Band()
    with pytest.raises(ValidationError):
        Band(min=2.0, max=1.0)


def test_a_band_of_zero_width_is_rejected() -> None:
    """P7b-F13: min == max is no band; the boundary of ``min < max``."""
    with pytest.raises(ValidationError, match="must be below max"):
        Band(min=1.0, max=1.0)


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
    rule = rule_of(quantity={"slug": "a-quantity-still-to-come", "planned": "#9999"})
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


def test_no_shipped_rule_is_still_planned() -> None:
    table = load_rule_table(DRELA)
    planned = {r.id: r.quantity.planned for r in table.rules if r.quantity.planned}
    assert planned == {}


def test_the_shipped_json_equals_the_yaml() -> None:
    assert shipped_rule_table() == load_rule_table(DRELA)


def test_the_shipped_json_is_current() -> None:
    assert main([str(DRELA), "--check"]) == 0


def test_the_json_rendering_does_not_depend_on_the_key_order_of_the_input() -> None:
    """P7b-F18: keys in reversed order render the same text, in the rule order given."""
    forward = {"source": "s", "rules": [rule_dict(id="first"), rule_dict(id="second")]}
    reverse = {
        "rules": [dict(reversed(rule_dict(id=i).items())) for i in ("first", "second")],
        "source": "s",
    }
    text = render_rule_table(RuleTable.model_validate(forward))
    assert render_rule_table(RuleTable.model_validate(reverse)) == text
    assert text.endswith("}\n")
    parsed = json.loads(text)
    assert [rule["id"] for rule in parsed["rules"]] == ["first", "second"]
    assert next(iter(parsed)) == "source"


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


@pytest.mark.parametrize("rule_id", ["horizontal-tail-volume", "vertical-tail-volume"])
def test_a_tail_volume_above_the_band_is_a_caution_below_it_stays_bad(rule_id: str) -> None:
    rule = {r.id: r for r in load_rule_table(DRELA).rules}[rule_id]
    assert rule.above_severity is Severity.CAUTION
    assert rule.below_severity is Severity.BAD
    assert rule.above_basis is not None
    assert "maintainer 2026-10-25" in rule.above_basis
    assert "drag and mass" in rule.above_basis
    assert rule.below is not None


def test_the_circling_rules_hold_drelas_threshold_and_the_maintainers_severities() -> None:
    """P7b-F04: Drela rule 9 (B > 5 stable, B = 5 neutral); severity per maintainer 2026-10-26."""
    table = {rule.id: rule for rule in load_rule_table(DRELA).rules}
    aileron = table["spiral-stability-circling-aileron"]
    rudder_only = table["spiral-stability-circling-rudder-only"]
    for rule in (aileron, rudder_only):
        assert rule.quantity.slug == "spiral-parameter-mp"
        assert rule.band.min == 5.0
        assert rule.band.min_inclusive is False
        assert rule.band.max is None
    assert aileron.below_severity is Severity.CAUTION
    assert aileron.below_basis is not None
    assert "maintainer 2026-10-26" in aileron.below_basis
    assert aileron.when == ("has_vertical_tail", "has_aileron")
    assert rudder_only.below_severity is Severity.BAD
    assert rudder_only.when_not == ("has_aileron",)


def test_the_sideslip_levels_split_at_5_and_15_degrees() -> None:
    """P7b-F04: Drela rule 11 gives 5...15 deg; 5 itself still belongs to the lower level."""
    rule = {r.id: r for r in load_rule_table(DRELA).rules}["turn-sideslip"]
    assert rule.level_of(5.0) == "below-typical-limit"
    assert rule.level_of(5.0001) == "within-typical-limit-range"
    assert rule.level_of(15.0) == "within-typical-limit-range"
    assert rule.level_of(15.1) is None


def test_the_spiral_levels_cover_b_3_to_4() -> None:
    """P7b-F04: Drela names B = 3...4 as manageable for an experienced pilot."""
    rule = {r.id: r for r in load_rule_table(DRELA).rules}["spiral-stability"]
    assert rule.level_of(3.0) == "manageable-for-experienced-pilot"
    assert rule.level_of(4.0) == "manageable-for-experienced-pilot"
    assert rule.level_of(4.5) is None


def test_the_circling_aileron_verdict_below_the_threshold_is_a_caution() -> None:
    """P7b-F04, through the evaluator: B = 4.5 < 5 at V_mp with ailerons is a caution."""
    table = load_rule_table(DRELA)
    flags = facts(has_vertical_tail=True, has_aileron=True)
    verdicts = {
        v.rule_id: v
        for v in evaluate_rules(table, result_of(ok("spiral-parameter-mp", 4.5)), flags)
    }
    aileron = verdicts["spiral-stability-circling-aileron"]
    assert aileron.status is RuleStatus.BELOW
    assert aileron.severity is Severity.CAUTION
    assert verdicts["spiral-stability-circling-rudder-only"].status is RuleStatus.NOT_APPLICABLE
    boundary = evaluate_rules(table, result_of(ok("spiral-parameter-mp", 5.0)), flags)
    assert {v.rule_id: v.status for v in boundary}["spiral-stability-circling-aileron"] is (
        RuleStatus.BELOW
    )


@pytest.mark.parametrize(
    "build_rule",
    [
        lambda: rule_of(abov_severity="caution"),
        lambda: rule_of(band={"min": 0.05, "max": 0.15, "min_inclusiv": False}),
        lambda: rule_of(quantity={"slug": "x", "plannd": "#1"}),
        lambda: rule_of(levels=[{"id": "l", "min": 0.0, "meaning": "m", "extra": 1}]),
        lambda: RuleTable.model_validate({"source": "s", "rules": [rule_dict()], "extra": 1}),
    ],
)
def test_the_rule_table_types_reject_an_unknown_key(build_rule: Callable[[], object]) -> None:
    """P7b-F02: a mistyped key in the YAML must fail, not be dropped and default silently."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        build_rule()


def test_the_rule_table_types_are_frozen() -> None:
    rule = rule_of(levels=[{"id": "l", "min": 0.0, "meaning": "m"}])
    table = table_of(rule)
    for target, field in (
        (rule.band, "min"),
        (rule, "title"),
        (rule.quantity, "slug"),
        (rule.levels[0], "meaning"),
        (table, "source"),
    ):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(target, field, None)


def test_a_verdict_rejects_an_unknown_key_and_is_frozen() -> None:
    """P7b-F02 / probe M29: RuleVerdict carries the same strictness."""
    (verdict,) = evaluate_rules(
        table_of(rule_of()), result_of(ok("static-margin-target", 0.1)), facts()
    )
    with pytest.raises(ValidationError, match="Extra inputs"):
        RuleVerdict.model_validate({**verdict.model_dump(), "extra": 1})
    with pytest.raises(ValidationError, match="frozen"):
        setattr(verdict, "text", "x")  # noqa: B010 - a frozen model rejects the assignment


@pytest.fixture
def shipped_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in for the evaluation package directory, so the importer writes into tmp."""
    monkeypatch.setattr(rules_module, "__file__", str(tmp_path / "rules.py"))
    return tmp_path


def test_the_importer_writes_the_json_the_check_then_accepts(
    shipped_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P7a-F06: writing yields exactly the rendering; --check on it passes."""
    assert main([str(DRELA)]) == 0
    written = (shipped_directory / "rule_table.json").read_text(encoding="utf-8")
    assert written == render_rule_table(load_rule_table(DRELA))
    assert "wrote rule_table.json" in capsys.readouterr().out
    assert main([str(DRELA), "--check"]) == 0
    assert "rule_table.json is current" in capsys.readouterr().out


def test_the_check_fails_on_a_stale_json(
    shipped_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P7a-F06: a CI gate that exits 0 on a stale file would let the table drift from the YAML."""
    (shipped_directory / "rule_table.json").write_text("{}", encoding="utf-8")
    assert main([str(DRELA), "--check"]) == 1
    assert "rule_table.json is stale" in capsys.readouterr().out
    assert (shipped_directory / "rule_table.json").read_text(encoding="utf-8") == "{}"


def test_the_check_fails_on_a_missing_json(
    shipped_directory: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert not (shipped_directory / "rule_table.json").exists()
    assert main([str(DRELA), "--check"]) == 1
    assert "rule_table.json is stale" in capsys.readouterr().out
    assert not (shipped_directory / "rule_table.json").exists()
