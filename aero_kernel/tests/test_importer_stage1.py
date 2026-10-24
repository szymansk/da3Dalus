"""Importer stage 1 (parse): one test per finding class (ARCHITECTURE ch. 8.9, ADR 0020)."""

from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, write_canon


def run(tmp_path: Path, overrides: dict[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, overrides))


def mutate(name: str, old: str, new: str) -> dict[str, str | None]:
    """Return an override that replaces ``old`` by ``new`` in one mini-canon file."""
    assert old in MINI_CANON[name], f"{old!r} not in {name}"
    return {name: MINI_CANON[name].replace(old, new, 1)}


def test_the_mini_canon_imports_without_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert result.findings == ()
    assert result.model is not None


GRAVITY = "quantities/gravity.md"
WEIGHING = "formulas/weighing.md"

STAGE_1_CASES = {
    "non-string field name": (
        mutate(GRAVITY, "type: scalar\n", "type: scalar\n1: x\n"),
        GRAVITY,
        "1",
        "string",
    ),
    "non-string default slug": (
        {
            "defaults.yaml": "1:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n"
        },
        "defaults.yaml",
        "1",
        "string",
    ),
    "no front matter": ({GRAVITY: "just prose\n"}, GRAVITY, "front matter", "front matter"),
    "unterminated front matter": (
        {GRAVITY: "---\ncanon: gravity\n\nprose\n"},
        GRAVITY,
        "front matter",
        "front matter",
    ),
    "invalid yaml": (
        {GRAVITY: "---\ncanon: [unclosed\n---\nprose\n"},
        GRAVITY,
        "front matter",
        "YAML",
    ),
    "front matter is no mapping": (
        {GRAVITY: "---\n- a\n- b\n---\n"},
        GRAVITY,
        "front matter",
        "mapping",
    ),
    "missing canon": (mutate(GRAVITY, "canon: gravity\n", ""), GRAVITY, "canon", "missing"),
    "canon differs from the file name": (
        mutate(GRAVITY, "canon: gravity\n", "canon: gravitation\n"),
        GRAVITY,
        "canon",
        "differs from the file name",
    ),
    "canon is no string": (
        mutate(GRAVITY, "canon: gravity\n", "canon: 5\n"),
        GRAVITY,
        "canon",
        "string",
    ),
    "wrong quantity marker": (
        mutate(GRAVITY, "kind: quantity\n", "kind: formula\n"),
        GRAVITY,
        "kind",
        "quantity",
    ),
    "wrong formula marker": (
        mutate(WEIGHING, "entry: formula\n", "entry: quantity\n"),
        WEIGHING,
        "entry",
        "formula",
    ),
    "missing formula marker": (
        mutate(WEIGHING, "entry: formula\n", ""),
        WEIGHING,
        "entry",
        "formula",
    ),
    "unknown quantity field": (
        mutate(GRAVITY, "type: scalar\n", "type: scalar\ncolour: red\n"),
        GRAVITY,
        "colour",
        "unknown field",
    ),
    "unknown formula field": (
        mutate(WEIGHING, "tool: AB\n", "tool: AB\nspeed: fast\n"),
        WEIGHING,
        "speed",
        "unknown field",
    ),
    "escalated comment": (
        mutate(WEIGHING, "tool: AB\n", "tool: AB  # ESCALATED: undecided binding\n"),
        WEIGHING,
        "ESCALATED",
        "undecided binding",
    ),
    "yaml 1.1 boolean": (
        mutate(GRAVITY, "positive: true\n", "positive: yes\n"),
        GRAVITY,
        "yaml",
        "boolean",
    ),
    "default in a quantity": (
        mutate(GRAVITY, "type: scalar\n", "type: scalar\ndefault: 9.8\n"),
        GRAVITY,
        "default",
        "defaults.yaml",
    ),
    "missing symbol": (mutate(GRAVITY, "symbol: g\n", ""), GRAVITY, "symbol", "missing"),
    "missing unit": (mutate(GRAVITY, "unit: m/s^2\n", ""), GRAVITY, "unit", "missing"),
    "missing role": (mutate(GRAVITY, "role: input\n", ""), GRAVITY, "role", "missing"),
    "missing type": (mutate(GRAVITY, "type: scalar\n", ""), GRAVITY, "type", "missing"),
    "symbol is no string": (
        mutate(GRAVITY, "symbol: g\n", "symbol: [g]\n"),
        GRAVITY,
        "symbol",
        "string",
    ),
    "missing tool": (mutate(WEIGHING, "tool: AB\n", ""), WEIGHING, "tool", "missing"),
    "missing kind": (mutate(WEIGHING, "kind: procedure\n", ""), WEIGHING, "kind", "missing"),
    "missing inputs": (
        mutate(WEIGHING, "inputs: {m: aircraft-mass, g: gravity}\n", ""),
        WEIGHING,
        "inputs",
        "missing",
    ),
    "inputs is no mapping": (
        mutate(WEIGHING, "inputs: {m: aircraft-mass, g: gravity}\n", "inputs: [m, g]\n"),
        WEIGHING,
        "inputs",
        "mapping",
    ),
    "missing outputs": (
        mutate(WEIGHING, "outputs: {w: null}\n", ""),
        WEIGHING,
        "outputs",
        "missing",
    ),
    "applications is no list": (
        mutate(WEIGHING, "applications:\n", "applications: clean\nxx:\n"),
        WEIGHING,
        "applications",
        "list",
    ),
    "defaults is no mapping": (
        {"defaults.yaml": "- gravity\n"},
        "defaults.yaml",
        "document",
        "mapping",
    ),
    "defaults is invalid yaml": (
        {"defaults.yaml": "gravity: [unclosed\n"},
        "defaults.yaml",
        "document",
        "YAML",
    ),
    "default entry is no mapping": (
        {"defaults.yaml": "gravity: 9.8\n"},
        "defaults.yaml",
        "gravity",
        "mapping",
    ),
    "default without regime": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: s\n",
        },
        "defaults.yaml",
        "gravity.regime",
        "Field required",
    ),
    "default with an empty source": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: ''\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.source",
        "at least 1 character",
    ),
    "default value is infinite": (
        {
            "defaults.yaml": "gravity:\n  value: .inf\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.value",
        "finite",
    ),
    "default with a blank regime": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: '  '\n",
        },
        "defaults.yaml",
        "gravity.regime",
        "should match pattern",
    ),
    "default value is no number": (
        {
            "defaults.yaml": "gravity:\n  value: high\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.value",
        "number",
    ),
    "default value is a boolean": (
        {
            "defaults.yaml": "gravity:\n  value: true\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.value",
        "number",
    ),
    "default with an extra key": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n  note: x\n",
        },
        "defaults.yaml",
        "gravity.note",
        "Extra inputs",
    ),
}


@pytest.mark.parametrize(
    ("overrides", "file", "field", "text"), STAGE_1_CASES.values(), ids=STAGE_1_CASES.keys()
)
def test_stage_1_finding(
    tmp_path: Path, overrides: dict[str, str | None], file: str, field: str, text: str
) -> None:
    result = run(tmp_path, overrides)
    assert result.model is None
    matching = [
        finding
        for finding in result.findings
        if finding.file == file and finding.field == field and text in finding.message
    ]
    assert matching, [str(finding) for finding in result.findings]


def test_a_duplicate_slug_is_a_finding(tmp_path: Path) -> None:
    other = MINI_CANON[GRAVITY]
    result = run(tmp_path, {"quantities/gravity-again.md": other})
    messages = [str(finding) for finding in result.findings]
    assert any("duplicate" in message and "gravity-again.md" in message for message in messages)


def test_a_duplicate_default_slug_is_a_finding(tmp_path: Path) -> None:
    text = MINI_CANON["defaults.yaml"] * 2
    result = run(tmp_path, {"defaults.yaml": text})
    assert any("duplicate" in finding.message for finding in result.findings)


def test_the_prose_is_never_read(tmp_path: Path) -> None:
    """The mini canon's prose is invalid YAML on purpose; it must not matter."""
    assert run(tmp_path).findings == ()


def test_a_finding_prints_as_file_field_message(tmp_path: Path) -> None:
    result = run(tmp_path, {GRAVITY: "just prose\n"})
    assert str(result.findings[0]).startswith(f"{GRAVITY}: front matter: ")


def test_all_findings_of_a_stage_are_reported_together(tmp_path: Path) -> None:
    overrides = {**mutate(GRAVITY, "symbol: g\n", ""), **mutate(WEIGHING, "tool: AB\n", "")}
    files = {finding.file for finding in run(tmp_path, overrides).findings}
    assert files == {GRAVITY, WEIGHING}


def test_a_file_that_is_not_utf8_is_a_finding(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    (canon / GRAVITY).write_bytes(b"---\ncanon: gravity\nsymbol: \xff\n---\n")
    result = import_canon(canon)
    assert any(f.file == GRAVITY and "unreadable" in f.message for f in result.findings)


def test_a_missing_entry_directory_is_a_finding(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    for path in (canon / "quantities").iterdir():
        path.unlink()
    (canon / "quantities").rmdir()
    result = import_canon(canon)
    assert any(f.file == "quantities" and f.field == "directory" for f in result.findings)


def test_an_empty_defaults_file_means_no_defaults(tmp_path: Path) -> None:
    result = run(tmp_path, {"defaults.yaml": ""})
    assert result.model is not None
    assert result.model.namespaces["calc"].defaults == {}


def test_a_missing_defaults_file_is_a_finding(tmp_path: Path) -> None:
    """A canon without defaults says so with an empty file, never by leaving it out (T3)."""
    result = run(tmp_path, {"defaults.yaml": None})
    assert result.model is None
    assert [(f.file, f.field, f.message) for f in result.findings] == [
        ("defaults.yaml", "document", "missing: an empty file or {} means no defaults")
    ]


def test_an_empty_mapping_in_the_defaults_file_means_no_defaults(tmp_path: Path) -> None:
    result = run(tmp_path, {"defaults.yaml": "{}\n"})
    assert result.model is not None
    assert result.model.namespaces["calc"].defaults == {}


# --- duplicate keys at every depth (a repeated key is never silently last-wins) -------------------


DUPLICATE_KEY_CASES = {
    "top level of an entry": mutate(WEIGHING, "tool: AB\n", "tool: AB\ntool: APP\n"),
    "inside a flow mapping": mutate(
        WEIGHING,
        "inputs: {m: aircraft-mass, g: gravity}",
        "inputs: {m: aircraft-mass, m: gravity, g: gravity}",
    ),
    "inside a block mapping of an application": mutate(
        WEIGHING, "    when: has_aileron\n", "    when: has_aileron\n    when: null\n"
    ),
    "inside a default": {
        "defaults.yaml": "gravity:\n  value: 9.8\n  value: 9.9\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n"
    },
}


@pytest.mark.parametrize("overrides", DUPLICATE_KEY_CASES.values(), ids=DUPLICATE_KEY_CASES.keys())
def test_a_duplicate_key_is_a_finding_with_key_and_line(
    tmp_path: Path, overrides: dict[str, str | None]
) -> None:
    result = run(tmp_path, overrides)
    assert result.model is None
    assert any(
        "duplicate key" in finding.message and "line " in finding.message
        for finding in result.findings
    ), [str(finding) for finding in result.findings]


def test_the_line_of_a_duplicate_key_counts_from_the_top_of_the_file(tmp_path: Path) -> None:
    text = "---\ncanon: gravity\ncanon: gravity\n---\n"
    result = run(tmp_path, {GRAVITY: text})
    assert any("duplicate key 'canon' (line 3)" in f.message for f in result.findings)


# --- defaults.yaml is scanned like an entry -------------------------------------------------------


def test_defaults_with_an_escalated_comment_are_a_finding(tmp_path: Path) -> None:
    text = MINI_CANON["defaults.yaml"].replace("gravity:", "gravity:  # ESCALATED: undecided", 1)
    result = run(tmp_path, {"defaults.yaml": text})
    assert any(f.file == "defaults.yaml" and f.field == "ESCALATED" for f in result.findings)


def test_defaults_with_a_yaml_boolean_are_a_finding(tmp_path: Path) -> None:
    text = MINI_CANON["defaults.yaml"].replace("regime-independent", "yes")
    result = run(tmp_path, {"defaults.yaml": text})
    assert any(f.file == "defaults.yaml" and f.field == "yaml" for f in result.findings)


@pytest.mark.parametrize("spelling", ["on", "off", "yes", "no", "y", "n"])
def test_every_yaml_1_1_boolean_spelling_is_a_finding(tmp_path: Path, spelling: str) -> None:
    result = run(tmp_path, mutate(GRAVITY, "positive: true\n", f"positive: {spelling}\n"))
    (finding,) = [f for f in result.findings if f.field == "yaml"]
    assert spelling in finding.message
    assert "true or false" in finding.message  # a boolean field is not fixed by quoting


def test_a_file_that_is_not_a_markdown_entry_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, {"formulas/Extra.MD": MINI_CANON[WEIGHING]})
    assert any(
        f.file == "formulas/Extra.MD" and f.field == "file" and ".md" in f.message
        for f in result.findings
    )


def test_an_unhashable_mapping_key_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(GRAVITY, "type: scalar\n", "type: scalar\n? [a, b]\n: x\n"))
    assert any(f.file == GRAVITY and "unhashable" in f.message for f in result.findings)


def test_hidden_files_and_subdirectories_are_ignored(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    (canon / "formulas" / ".DS_Store").write_bytes(b"\x00")
    (canon / "quantities" / "drafts").mkdir()
    assert import_canon(canon).findings == ()
