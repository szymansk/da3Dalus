"""Importer stage 1 (parse): one test per finding class (ARCHITECTURE ch. 8.9, ADR 0020)."""

from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, SOURCE_COMMIT, write_canon


def run(tmp_path: Path, overrides: dict[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, overrides), SOURCE_COMMIT)


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
        {"defaults.yaml": "1:\n  value: 9.8\n  unit: m/s^2\n  source: s\n  regime: r\n"},
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
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  source: s\n",
        },
        "defaults.yaml",
        "gravity.regime",
        "missing",
    ),
    "default with an empty source": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  source: ''\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.source",
        "non-empty",
    ),
    "default value is no number": (
        {
            "defaults.yaml": "gravity:\n  value: high\n  unit: m/s^2\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.value",
        "number",
    ),
    "default value is a boolean": (
        {
            "defaults.yaml": "gravity:\n  value: true\n  unit: m/s^2\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.value",
        "number",
    ),
    "default with an extra key": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: m/s^2\n  source: s\n  regime: r\n  note: x\n",
        },
        "defaults.yaml",
        "gravity.note",
        "unknown field",
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
    result = import_canon(canon, SOURCE_COMMIT)
    assert any(f.file == GRAVITY and "unreadable" in f.message for f in result.findings)


def test_a_missing_entry_directory_is_a_finding(tmp_path: Path) -> None:
    canon = write_canon(tmp_path)
    for path in (canon / "quantities").iterdir():
        path.unlink()
    (canon / "quantities").rmdir()
    result = import_canon(canon, SOURCE_COMMIT)
    assert any(f.file == "quantities" and f.field == "directory" for f in result.findings)


def test_an_empty_defaults_file_means_no_defaults(tmp_path: Path) -> None:
    result = run(tmp_path, {"defaults.yaml": ""})
    assert result.model is not None
    assert result.model.namespaces["calc"].defaults == {}


def test_a_canon_without_defaults_file_has_no_defaults(tmp_path: Path) -> None:
    result = run(tmp_path, {"defaults.yaml": None})
    assert result.model is not None
    assert result.model.namespaces["calc"].defaults == {}
