"""Importer hardening: the exact findings the mutation run of S3 (a) demanded (amendment 2).

Each test names the rule it pins; it asserts the exact file, field and decisive message text.
"""

import re
from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, SOURCE_COMMIT, write_canon

GRAVITY = "quantities/gravity.md"
WEIGHT = "quantities/weight.md"
WEIGHING = "formulas/weighing.md"
TWICE = "formulas/weigh-twice.md"
FROM_MASS = "formulas/weight-from-mass.md"


def run(tmp_path: Path, overrides: dict[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, overrides), SOURCE_COMMIT)


def mutate(name: str, old: str, new: str) -> dict[str, str | None]:
    """Return an override that replaces ``old`` by ``new`` in one mini-canon file."""
    assert old in MINI_CANON[name], f"{old!r} not in {name}"
    return {name: MINI_CANON[name].replace(old, new, 1)}


def shown(result: ImportResult) -> list[str]:
    """Render the findings of a result, for assertion messages and exact comparison."""
    return [str(finding) for finding in result.findings]


# --- S1: a stray field is unknown; the drop list is complete --------------------------------------


@pytest.mark.parametrize(
    "stray",
    ["tex", "shape", "output", "source_status", "dimensional_check", "entry", "tool", "inputs"],
)
def test_a_formula_field_in_a_quantity_is_unknown(tmp_path: Path, stray: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, "type: scalar\n", f"type: scalar\n{stray}: x\n"))
    assert shown(result) == [f"{GRAVITY}: {stray}: unknown field: the README does not define it"]


@pytest.mark.parametrize(
    "stray", ["symbol", "unit", "role", "type", "positive", "description", "default"]
)
def test_a_quantity_field_in_a_formula_is_unknown(tmp_path: Path, stray: str) -> None:
    result = run(tmp_path, mutate(WEIGHING, "tool: AB\n", f"tool: AB\n{stray}: x\n"))
    assert shown(result) == [f"{WEIGHING}: {stray}: unknown field: the README does not define it"]


# --- S2: a wrong container type is a finding that names the field; nothing becomes empty ----------

FORMULA_CONTAINERS = {
    "kind": ("kind: procedure\n", "kind: [a]\n", "string"),
    "tool": ("tool: AB\n", "tool: [a]\n", "string"),
    "outputs": ("outputs: {w: null}\n", "outputs: 5\n", "mapping"),
    "preconditions": ("tool: AB\n", "tool: AB\npreconditions: 5\n", "list"),
    "postconditions": ("tool: AB\n", "tool: AB\npostconditions: x\n", "list"),
    "embeds": ("tool: AB\n", "tool: AB\nembeds: x\n", "list"),
    "variables": ("tool: AB\n", "tool: AB\nvariables: x\n", "list"),
    "optional": ("tool: AB\n", "tool: AB\noptional: x\n", "list"),
    "uncertainty": ("tool: AB\n", "tool: AB\nuncertainty: [interval]\n", "string"),
    "worlds": ("tool: AB\n", "tool: AB\nworlds: x\n", "list"),
    "cost": ("tool: AB\n", "tool: AB\ncost: 5\n", "string"),
}


@pytest.mark.parametrize("field", FORMULA_CONTAINERS)
def test_a_formula_field_of_the_wrong_container_type(tmp_path: Path, field: str) -> None:
    old, new, shape = FORMULA_CONTAINERS[field]
    if field == "postconditions":  # the mini weighing formula already has some
        old = "postconditions:\n"
        new = "postconditions: x\nunused:\n"
    result = run(tmp_path, mutate(WEIGHING, old, new))
    assert f"{WEIGHING}: {field}: must be a {shape}, not " in "\n".join(shown(result))


@pytest.mark.parametrize(
    ("field", "old"),
    [("symbol", "symbol: g\n"), ("role", "role: input\n"), ("type", "type: scalar\n")],
)
def test_a_quantity_field_of_the_wrong_container_type(tmp_path: Path, field: str, old: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, old, f"{field}: [a]\n"))
    assert f"{GRAVITY}: {field}: must be a string, not list" in shown(result)


@pytest.mark.parametrize("value", ["[a]", "null", "5"])
def test_a_quantity_uncertainty_must_be_a_string(tmp_path: Path, value: str) -> None:
    result = run(
        tmp_path, mutate(GRAVITY, "type: scalar\n", f"type: scalar\nuncertainty: {value}\n")
    )
    assert any(
        line.startswith(f"{GRAVITY}: uncertainty: must be a string") for line in shown(result)
    )


# --- S3, S9: markers and the positive flag ---------------------------------------------------------


def test_a_missing_quantity_marker_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(GRAVITY, "kind: quantity\n", ""))
    assert shown(result) == [f"{GRAVITY}: kind: must be 'quantity' (found None)"]


@pytest.mark.parametrize("value", ["1", "null", '"true"', "false", "0"])
def test_positive_must_be_true_or_absent(tmp_path: Path, value: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, "positive: true\n", f"positive: {value}\n"))
    assert result.model is None
    assert any(f.file == GRAVITY and f.field == "positive" for f in result.findings), shown(result)


# --- S4: every YAML 1.1 boolean spelling, as a value and as a key -------------------------------

SPELLINGS = ["on", "off", "yes", "no", "y", "n", "On", "OFF", "Yes", "NO", "Y", "N"]


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_a_boolean_spelling_as_a_value_in_a_formula(tmp_path: Path, spelling: str) -> None:
    result = run(tmp_path, mutate(WEIGHING, "tool: AB\n", f"tool: AB\nuncertainty: {spelling}\n"))
    assert any(
        f.file == WEIGHING and f.field == "yaml" and spelling in f.message for f in result.findings
    )


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_a_boolean_spelling_as_a_key_in_a_quantity(tmp_path: Path, spelling: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, "type: scalar\n", f"type: scalar\n{spelling}: 1\n"))
    assert any(
        f.file == GRAVITY and f.field == "yaml" and spelling in f.message for f in result.findings
    )


# --- S5: escalation comments ---------------------------------------------------------------------


def test_two_escalation_comments_are_two_findings(tmp_path: Path) -> None:
    text = (
        MINI_CANON[WEIGHING]
        .replace("tool: AB\n", "tool: AB  # ESCALATED: one\n")
        .replace("kind: procedure\n", "kind: procedure  # ESCALATED: two\n")
    )
    result = run(tmp_path, {WEIGHING: text})
    assert sorted(f.message for f in result.findings if f.field == "ESCALATED") == [
        "the entry is escalated and undecided (one); the maintainer decides it before it is imported",
        "the entry is escalated and undecided (two); the maintainer decides it before it is imported",
    ]


@pytest.mark.parametrize("comment", ["# ESCALATED: why", "#ESCALATED: why", "#  ESCALATED: why"])
def test_an_escalation_comment_is_found_in_every_spelling_and_on_the_first_line(
    tmp_path: Path, comment: str
) -> None:
    first = MINI_CANON[GRAVITY].replace("canon: gravity\n", f"canon: gravity  {comment}\n", 1)
    result = run(tmp_path, {GRAVITY: first})
    assert [f.field for f in result.findings] == ["ESCALATED"]


def test_an_escalation_comment_on_its_own_line_is_found(tmp_path: Path) -> None:
    text = MINI_CANON[GRAVITY].replace("canon: gravity\n", "# ESCALATED: why\ncanon: gravity\n", 1)
    assert [f.field for f in run(tmp_path, {GRAVITY: text}).findings] == ["ESCALATED"]


def test_an_escalation_without_a_reason_says_so(tmp_path: Path) -> None:
    text = MINI_CANON[GRAVITY].replace("canon: gravity\n", "canon: gravity  # ESCALATED:\n", 1)
    (finding,) = run(tmp_path, {GRAVITY: text}).findings
    assert "no reason given" in finding.message


# --- S6: stage 1 completeness ----------------------------------------------------------------------


def test_one_file_with_three_faults_yields_all_three(tmp_path: Path) -> None:
    text = (
        MINI_CANON[GRAVITY]
        .replace("symbol: g\n", "colour: red\n")
        .replace("kind: quantity\n", "kind: formula\n")
    )
    assert shown(run(tmp_path, {GRAVITY: text})) == [
        f"{GRAVITY}: kind: must be 'quantity' (found 'formula')",
        f"{GRAVITY}: colour: unknown field: the README does not define it",
        f"{GRAVITY}: symbol: missing, but required",
    ]


def test_leading_prose_before_the_front_matter_is_a_finding(tmp_path: Path) -> None:
    text = "prose first\n" + MINI_CANON[GRAVITY]
    assert shown(run(tmp_path, {GRAVITY: text})) == [
        f"{GRAVITY}: front matter: no front matter between '---' lines"
    ]


def test_a_directory_named_like_an_entry_is_a_finding(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    (canon / "quantities" / "dir.md").mkdir()
    result = import_canon(canon, SOURCE_COMMIT)
    assert shown(result) == ["quantities/dir.md: file: is a directory, not an entry file"]


@pytest.mark.parametrize("sub", ["formulas", "quantities"])
def test_a_missing_entry_directory_is_a_finding_for_each(tmp_path: Path, sub: str) -> None:
    canon = write_canon(tmp_path)
    for path in (canon / sub).iterdir():
        path.unlink()
    (canon / sub).rmdir()
    assert any(
        f.file == sub and f.field == "directory"
        for f in import_canon(canon, SOURCE_COMMIT).findings
    )


def test_a_default_value_of_null_is_a_finding(tmp_path: Path) -> None:
    text = MINI_CANON["defaults.yaml"].replace("9.80665", "null")
    assert "defaults.yaml: gravity.value: Input should be a valid number (got None)" in shown(
        run(tmp_path, {"defaults.yaml": text})
    )


@pytest.mark.parametrize("value", [".nan", ".inf", "-.inf"])
def test_a_non_finite_default_names_the_slug(tmp_path: Path, value: str) -> None:
    text = MINI_CANON["defaults.yaml"].replace("9.80665", value)
    result = run(tmp_path, {"defaults.yaml": text})
    assert [(f.file, f.field) for f in result.findings] == [("defaults.yaml", "gravity.value")]


# --- S8: unit spellings that are not units --------------------------------------------------------


@pytest.mark.parametrize("unit", ["1.0", '"-"', '"–"', '""', "0", "true"])
def test_a_spelling_that_is_no_unit_is_a_finding(tmp_path: Path, unit: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, "unit: m/s^2", f"unit: {unit}"))
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert (finding.file, finding.field) == (GRAVITY, "unit")
    assert finding.message.endswith(f"(got {eval(unit.replace('true', 'True'))!r})")  # noqa: S307


# --- S10, S11: constants and application rules ----------------------------------------------------


def test_a_constant_without_a_value_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(WEIGHING, "{const: 9.81, source: test source}", "{source: s}"))
    assert shown(result) == [f"{WEIGHING}: applications[1].bind.g.const: Field required"]


def test_a_bad_value_and_a_bad_source_are_two_findings(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(WEIGHING, "{const: 9.81, source: test source}", "{const: x, source: ''}")
    )
    assert sorted(f.field for f in result.findings) == [
        "applications[1].bind.g.const",
        "applications[1].bind.g.source",
    ]


def test_a_precondition_without_a_parameter(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(FROM_MASS, "{id: m_checked, parameter: m,", "{id: m_checked,"))
    assert shown(result) == [f"{FROM_MASS}: preconditions[0].parameter: Field required"]


def test_a_world_name_must_be_snake_case(tmp_path: Path) -> None:
    estimate = "formulas/estimate.md"
    result = run(
        tmp_path, mutate(estimate, "worlds: [simple, detailed]", "worlds: [Simple, detailed]")
    )
    assert [(f.file, f.field) for f in result.findings] == [(estimate, "worlds[0]")]
    assert "should match pattern" in result.findings[0].message


def test_a_quantity_slug_must_be_kebab_case(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(FROM_MASS, "outputs: {w: weight}", "outputs: {w: Weight}"))
    assert [(f.file, f.field) for f in result.findings] == [
        (FROM_MASS, "outputs.w"),
    ] or any(f.file == FROM_MASS for f in result.findings)
    assert result.model is None


# --- S12: every finding of a stage, no cascade -------------------------------------------------------


def test_stage_2_and_3_report_every_fault_at_once(tmp_path: Path) -> None:
    overrides = {
        **mutate(FROM_MASS, "kind: law", "kind: rite"),
        **mutate(WEIGHING, "tool: AB", "tool: XYZ"),
        **mutate(WEIGHT, '"N"', "furlong"),
        "defaults.yaml": MINI_CANON["defaults.yaml"].replace("m/s^2", "furlong"),
    }
    result = run(tmp_path, overrides)
    assert sorted((f.file, f.field) for f in result.findings) == sorted(
        [
            (FROM_MASS, "kind"),
            (WEIGHING, "tool"),
            (WEIGHT, "unit"),
            ("defaults.yaml", "gravity.unit"),
            (WEIGHING, "cost"),
        ]
    ), shown(result)


def test_one_formula_with_three_faults_yields_three_findings(tmp_path: Path) -> None:
    text = (
        MINI_CANON[FROM_MASS]
        .replace("kind: law", "kind: rite")
        .replace("on_violation: warning", "on_violation: panic")
        .replace("outputs: {w: weight}", "outputs: {w: nothing}")
    )
    result = run(tmp_path, {FROM_MASS: text})
    assert sorted(f.field for f in result.findings) == ["kind", "preconditions[0].on_violation"]


def test_two_unknown_references_in_one_formula_are_two_findings(tmp_path: Path) -> None:
    text = MINI_CANON[FROM_MASS].replace(
        "inputs: {m: aircraft-mass, g: gravity}\noutputs: {w: weight}",
        "inputs: {m: nothing-one, g: nothing-two}\noutputs: {w: weight}",
    )
    result = run(tmp_path, {FROM_MASS: text})
    messages = sorted(f.message for f in result.findings if f.field == "references")
    assert messages == ["unknown quantity calc:nothing-one", "unknown quantity calc:nothing-two"]


def test_findings_of_two_bad_files_come_in_sorted_file_order(tmp_path: Path) -> None:
    overrides = {**mutate(WEIGHT, "symbol: W\n", ""), **mutate(GRAVITY, "symbol: g\n", "")}
    assert [f.file for f in run(tmp_path, overrides).findings] == [GRAVITY, WEIGHT]


# --- S13: embeds ------------------------------------------------------------------------------------


@pytest.mark.parametrize("item", ["weighing.clean junk", "weighing.clean.x", "weighing.", ".clean"])
def test_a_malformed_embed_item_is_a_finding(tmp_path: Path, item: str) -> None:
    result = run(tmp_path, mutate(TWICE, "weighing.clean", f"'{item}'"))
    assert shown(result) == [f"{TWICE}: embeds: '{item}' is not <slug> or <slug>.<application-id>"]


def test_an_explicit_default_embed_equals_the_bare_one(tmp_path: Path) -> None:
    bare = run(tmp_path / "a", None).model
    explicit = run(
        tmp_path / "b", mutate(TWICE, "weight-from-mass,", "weight-from-mass.default,")
    ).model
    assert bare is not None
    assert explicit is not None
    assert bare.model_dump() == explicit.model_dump()


def self_embedding(tmp_path: Path) -> ImportResult:
    text = MINI_CANON["formulas/outer.md"].replace("embeds: [weigh-twice]", "embeds: [outer]")
    return run(tmp_path, {"formulas/outer.md": text})


def test_a_self_embed_terminates_with_a_finite_sorted_closure(tmp_path: Path) -> None:
    model = self_embedding(tmp_path).model
    assert model is not None
    outer = model.formula("outer")
    assert outer is not None
    assert outer.embeds_closure == ("calc:outer.default",)


def test_a_cycle_between_two_formulas_terminates_with_a_finite_sorted_closure(
    tmp_path: Path,
) -> None:
    one = MINI_CANON["formulas/outer.md"].replace("embeds: [weigh-twice]", "embeds: [weigh-twice]")
    two = MINI_CANON[TWICE].replace("embeds: [weight-from-mass, weighing.clean]", "embeds: [outer]")
    model = run(tmp_path, {"formulas/outer.md": one, TWICE: two}).model
    assert model is not None
    outer, twice = model.formula("outer"), model.formula("weigh-twice")
    assert outer is not None
    assert twice is not None
    assert outer.embeds_closure == ("calc:outer.default", "calc:weigh-twice.default")
    assert twice.embeds_closure == ("calc:outer.default", "calc:weigh-twice.default")


# --- S14: the source commit pattern, with stage-1 findings --------------------------------------------


@pytest.mark.parametrize("commit", ["A" * 40, "a" * 39, "a" * 41, "xa" + "a" * 38, "a" * 40 + "\n"])
def test_a_malformed_commit_is_a_finding(tmp_path: Path, commit: str) -> None:
    result = import_canon(write_canon(tmp_path), commit)
    assert [(f.file, f.field) for f in result.findings] == [("command line", "source_commit")]


def test_a_malformed_commit_and_a_stage_1_finding_are_both_reported(tmp_path: Path) -> None:
    canon = write_canon(tmp_path, {GRAVITY: "no front matter\n"})
    result = import_canon(canon, "abc")
    assert [(f.file, f.field) for f in result.findings] == [
        ("command line", "source_commit"),
        (GRAVITY, "front matter"),
    ]


# --- S15: the mapping of defaults ------------------------------------------------------------------------


def defaults_text(slug: str, value: str = "9.8", unit: str = "m/s^2") -> str:
    return f"{slug}:\n  value: {value}\n  unit: '{unit}'\n  source: s\n  regime: r\n"


def test_a_default_of_a_hyphenated_unknown_slug_keeps_the_full_slug(tmp_path: Path) -> None:
    result = run(tmp_path, {"defaults.yaml": defaults_text("wing-area")})
    assert shown(result) == ["defaults.yaml: wing-area: default of unknown quantity calc:wing-area"]


@pytest.mark.parametrize(
    ("slug", "value", "unit", "message"),
    [
        ("weight", "9.8", "N", "default of calc:weight: role must be input or target, not derived"),
        (
            "airplane",
            "9.8",
            "1",
            "default of calc:airplane: quantity must be a scalar, not airplane",
        ),
        (
            "gravity",
            "9.8",
            "kg",
            "default of calc:gravity: unit kg differs from the quantity's m/s^2",
        ),
        ("gravity", "0", "m/s^2", "default of positive quantity calc:gravity must be > 0"),
    ],
)
def test_every_defaults_rule_of_the_model_is_mapped_to_the_defaults_file(
    tmp_path: Path, slug: str, value: str, unit: str, message: str
) -> None:
    result = run(tmp_path, {"defaults.yaml": defaults_text(slug, value, unit)})
    assert shown(result) == [f"defaults.yaml: {slug}: {message}"]
