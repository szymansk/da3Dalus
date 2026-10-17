"""Tests for the authoring checks of scripts/check_canon.py.

The structural rules of the canon live in the importer (`aero_kernel/importer`, #1174); this checker
keeps what the importer never reads: the "Produces … from" line, the "Used by" / "Produced by" links,
the `output` field and the README examples. Each test builds a small canon directory and asserts
which findings the checker reports; the last test runs it over the real canon document.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_canon  # noqa: E402

REPO = SCRIPTS.parent
REAL_CANON = REPO / "_reversa_sdd" / "calculations" / "canon"

README = """# Canon

## Machine-readable fields
"""

GOOD_FRONT = """
inputs: {a: speed-a, b: speed-b}
outputs: {v: speed-v}
"""


def _quantity(slug, produced_by=(), used_by=(), extra=""):
    lines = [
        "---",
        f"canon: {slug}",
        "kind: quantity",
        f"symbol: {slug.replace('-', '_')}",
        "unit: m/s",
        "role: derived",
        "status: draft",
        "tags:",
        "  - canon/quantity",
    ]
    if extra:
        lines.append(extra)
    lines += ["---", "", f"# {slug}", ""]
    if produced_by:
        lines.append("**Produced by.** " + " · ".join(f"[[{p}]]" for p in produced_by))
        lines.append("")
    if used_by:
        lines.append("**Used by.** " + " · ".join(f"[[{u}]]" for u in used_by))
    return "\n".join(lines) + "\n"


def _formula(slug, produces, inputs_line, front):
    lines = [
        "---",
        f"canon: {slug}",
        "entry: formula",
        "kind: law",
        "tool: APP",
        "shape: law",
        "status: draft",
        "output: " + ", ".join(produces),
        "tags:",
        "  - canon/formula",
        front.strip("\n"),
        "---",
        "",
        f"# {slug}",
        "",
        "**Canonical form**",
        "",
        "```",
        "v = a * b",
        "```",
        "",
        "**Produces** "
        + " · ".join(f"[[{p}]]" for p in produces)
        + "  ·  **from** "
        + " · ".join(f"[[{i}]]" for i in inputs_line),
    ]
    return "\n".join(lines) + "\n"


def _canon(
    tmp_path,
    front=GOOD_FRONT,
    quantities=None,
    inputs_line=("speed-a", "speed-b"),
    produces=("speed-v",),
    extra_formulas=(),
):
    root = tmp_path / "canon"
    (root / "formulas").mkdir(parents=True)
    (root / "quantities").mkdir()
    (root / "README.md").write_text(README, encoding="utf-8")
    if quantities is None:
        quantities = {
            "speed-a": _quantity("speed-a", used_by=["f"]),
            "speed-b": _quantity("speed-b", used_by=["f"]),
            "speed-v": _quantity("speed-v", produced_by=["f"]),
        }
    for slug, text in quantities.items():
        (root / "quantities" / f"{slug}.md").write_text(text, encoding="utf-8")
    (root / "formulas" / "f.md").write_text(
        _formula("f", produces, inputs_line, front), encoding="utf-8"
    )
    for slug, text in extra_formulas:
        (root / "formulas" / f"{slug}.md").write_text(text, encoding="utf-8")
    return root


def _with_type(quantities):
    """Give every fixture quantity the `type` field the checker requires."""
    return {
        s: t.replace("status: draft", "status: draft\ntype: scalar") for s, t in quantities.items()
    }


def _findings(root):
    return check_canon.check_authoring(check_canon.load_canon(root))


def _errors(root):
    return _findings(root)


def _messages(findings):
    return [f"{f.entry} {f.field}: {f.message}" for f in findings]


@pytest.fixture
def typed_quantities():
    return _with_type(
        {
            "speed-a": _quantity("speed-a", used_by=["f"]),
            "speed-b": _quantity("speed-b", used_by=["f"]),
            "speed-v": _quantity("speed-v", produced_by=["f"]),
        }
    )


def test_a_consistent_canon_has_no_findings(tmp_path, typed_quantities):
    assert _findings(_canon(tmp_path, quantities=typed_quantities)) == []


def test_input_missing_from_the_from_line_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities, inputs_line=("speed-a",))
    msgs = _messages(_errors(root))
    assert any("f inputs" in m and "speed-b" in m for m in msgs), msgs


def test_output_disagreeing_with_the_produces_line_is_reported(tmp_path, typed_quantities):
    front = "inputs: {a: speed-a, b: speed-b}\noutputs: {v: speed-a}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("f outputs" in m and "speed-v" in m for m in msgs), msgs


def test_missing_inputs_field_is_reported(tmp_path, typed_quantities):
    front = "outputs: {v: speed-v}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("f inputs" in m for m in msgs), msgs


def test_used_by_missing_a_consumer_is_reported(tmp_path):
    quantities = _with_type(
        {
            "speed-a": _quantity("speed-a", used_by=["f"]),
            "speed-b": _quantity("speed-b"),
            "speed-v": _quantity("speed-v", produced_by=["f"]),
        }
    )
    msgs = _messages(_errors(_canon(tmp_path, quantities=quantities)))
    assert any("speed-b used_by" in m and "f" in m for m in msgs), msgs


def test_produced_by_naming_a_non_producer_is_reported(tmp_path):
    quantities = _with_type(
        {
            "speed-a": _quantity("speed-a", produced_by=["f"], used_by=["f"]),
            "speed-b": _quantity("speed-b", used_by=["f"]),
            "speed-v": _quantity("speed-v", produced_by=["f"]),
        }
    )
    msgs = _messages(_errors(_canon(tmp_path, quantities=quantities)))
    assert any("speed-a produced_by" in m for m in msgs), msgs


def test_application_quantities_count_towards_the_from_line(tmp_path, typed_quantities):
    """A quantity bound only inside an application still belongs on the `from` line."""
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: speed-b}
"""
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_the_produces_line_alone_disagreeing_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    path = root / "formulas" / "f.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "**Produces** [[speed-v]]", "**Produces** [[speed-b]]"
        ),
        encoding="utf-8",
    )
    msgs = _messages(_errors(root))
    assert any("f outputs: only in the Produces line: ['speed-b']" in m for m in msgs), msgs
    assert not any("output field" in m for m in msgs), msgs


def test_the_output_field_alone_disagreeing_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    path = root / "formulas" / "f.md"
    path.write_text(
        path.read_text(encoding="utf-8").replace("output: speed-v", "output: speed-b"),
        encoding="utf-8",
    )
    msgs = _messages(_errors(root))
    assert any("f outputs: only in the output field: ['speed-b']" in m for m in msgs), msgs
    assert not any("Produces line" in m for m in msgs), msgs


def _readme_with_example(root, slug, yaml_text):
    readme = root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8")
        + f"\n### One example per kind\n\nA **law** (`{slug}`):\n\n```yaml\n{yaml_text}```\n",
        encoding="utf-8",
    )


def test_a_readme_example_that_matches_its_entry_is_accepted(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    _readme_with_example(
        root, "f", "kind: law\ninputs: {a: speed-a, b: speed-b}\noutputs: {v: speed-v}\n"
    )
    assert _findings(root) == []


def test_a_readme_example_missing_a_machine_readable_key_of_its_entry_is_reported(
    tmp_path, typed_quantities
):
    """Review round 2, B: the entry gained `optional:`, the example did not."""
    root = _canon(tmp_path, front=GOOD_FRONT + "optional: [b]\n", quantities=typed_quantities)
    _readme_with_example(
        root, "f", "kind: law\ninputs: {a: speed-a, b: speed-b}\noutputs: {v: speed-v}\n"
    )
    msgs = _messages(_errors(root))
    assert any("README" in m and "optional" in m for m in msgs), msgs


def test_a_default_overridden_in_every_application_is_not_read(tmp_path, typed_quantities):
    """Only the quantities an application actually binds belong on the from line."""
    front = """
inputs: {a: speed-a, b: speed-v}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: speed-b}
"""
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_a_readme_example_that_drifted_from_its_entry_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    _readme_with_example(root, "f", "kind: law\ninputs: {a: speed-a}\n")
    msgs = _messages(_errors(root))
    assert any("README" in m and "f" in m and "inputs" in m for m in msgs), msgs


def test_a_readme_example_naming_an_unknown_entry_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    _readme_with_example(root, "nope", "kind: law\n")
    msgs = _messages(_errors(root))
    assert any("README" in m and "nope" in m for m in msgs), msgs


def test_cli_exits_zero_on_a_consistent_canon(tmp_path, typed_quantities):
    assert check_canon.cli([str(_canon(tmp_path, quantities=typed_quantities))]) == 0


def _fix_used_by(root, slug, used_by):
    """Rewrite a fixture quantity's Used-by line (a quantity no formula reads any more)."""
    path = root / "quantities" / f"{slug}.md"
    head = path.read_text(encoding="utf-8").split("**Used by.**")[0]
    if used_by:
        head += "**Used by.** " + " · ".join(f"[[{u}]]" for u in used_by) + "\n"
    path.write_text(head, encoding="utf-8")


def test_cli_exits_non_zero_on_an_authoring_error(tmp_path, capsys):
    assert check_canon.cli([str(_canon(tmp_path, inputs_line=("speed-a",)))]) == 1
    assert "speed-b" in capsys.readouterr().out


def test_the_real_canon_has_no_authoring_errors():
    errors = _findings(REAL_CANON)
    assert errors == [], "\n".join(_messages(errors))


def test_an_entry_without_front_matter_does_not_crash_the_checker(tmp_path, typed_quantities):
    """The importer reports it; the authoring check just has nothing to read."""
    root = _canon(tmp_path, quantities=typed_quantities)
    (root / "quantities" / "speed-b.md").write_text(
        "just prose, no front matter\n", encoding="utf-8"
    )
    assert check_canon.load_canon(root).quantities["speed-b"].front == {}
    msgs = _messages(_errors(root))
    assert any("speed-b" in m for m in msgs), msgs


# --- the kept authoring checks, boundaries -----------------------------------------------------------------------


def test_a_formula_without_the_produces_from_line_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    path = root / "formulas" / "f.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text[: text.index("**Produces**")], encoding="utf-8")
    assert _messages(_errors(root)) == ["f body: no '**Produces** … **from** …' line"]


def test_a_constant_binding_is_not_read(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: {const: 3, source: x}}
"""
    typed_quantities["speed-b"] = _with_type({"speed-b": _quantity("speed-b")})["speed-b"]
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    assert _messages(_errors(root)) == []


def test_a_name_that_is_no_quantity_is_not_read(tmp_path, typed_quantities):
    front = "inputs: {a: speed-a, b: not-a-quantity}\noutputs: {v: speed-v}\n"
    typed_quantities["speed-b"] = _with_type({"speed-b": _quantity("speed-b")})["speed-b"]
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    assert _messages(_errors(root)) == []


def test_a_readme_example_for_a_quantity_compares_the_quantity_keys(tmp_path, typed_quantities):
    typed_quantities["speed-a"] = typed_quantities["speed-a"].replace(
        "type: scalar", "type: scalar\npositive: true"
    )
    root = _canon(tmp_path / "full", quantities=typed_quantities)
    _readme_with_example(root, "speed-a", "type: scalar\npositive: true\n")
    assert _errors(root) == []
    root = _canon(tmp_path / "short", quantities=typed_quantities)
    _readme_with_example(root, "speed-a", "type: scalar\n")
    assert _messages(_errors(root)) == [
        "README examples: speed-a: positive differs from the entry's front matter"
    ]


def test_a_readme_example_of_the_wrong_quantity_type_is_reported(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    _readme_with_example(root, "speed-a", "type: airplane\n")
    assert _messages(_errors(root)) == [
        "README examples: speed-a: type differs from the entry's front matter"
    ]


# --- the dimensional check ---------------------------------------------------------------------------------------


def _dimensional_canon(tmp_path):
    root = tmp_path / "dim"
    (root / "quantities").mkdir(parents=True)
    (root / "formulas").mkdir()
    for slug, symbol, unit in (
        ("distance", "d", "m"),
        ("duration", "t", "s"),
        ("speed", "V_s", "m/s"),
        ("accel", "a", "m/s^2"),
    ):
        (root / "quantities" / f"{slug}.md").write_text(
            f"---\ncanon: {slug}\nsymbol: {symbol}\nunit: {unit}\n---\n", encoding="utf-8"
        )
    forms = {
        "ratio": ("speed", "V_s = d / t"),
        "root": ("speed", "V_s = sqrt(a * d)"),
        "qualified": ("speed", "V_s = d_max / t_clean"),
        "named": ("distance", "d = V_s * t"),
        "unlike": ("distance", "d = d + t"),
        "wrong": ("speed", "V_s = d * t"),
        "procedure": ("speed", "minimize over V:  d"),
        "stranger": ("speed", "V_s = zz / t"),
    }
    for slug, (output, form) in forms.items():
        (root / "formulas" / f"{slug}.md").write_text(
            f"---\ncanon: {slug}\noutput: {output}\nkind: law\n---\n\n"
            f"**Canonical form**\n\n```\n{form}\n```\n",
            encoding="utf-8",
        )
    return root


def test_the_dimensional_check_classifies_each_canonical_form(tmp_path):
    rows = check_canon.dimensional_rows(check_canon.build_canon_json(_dimensional_canon(tmp_path)))
    assert {f["slug"]: verdict for verdict, f, *_ in rows} == {
        "ratio": "BALANCES",
        "root": "BALANCES",
        "qualified": "BALANCES",
        "named": "BALANCES",
        "unlike": "ADDS_UNLIKE",
        "wrong": "MISMATCH",
        "procedure": "PROCEDURAL",
        "stranger": "UNKNOWN_SYMBOL",
    }


def test_the_dimensional_check_runs_from_an_extraction_json(tmp_path, capsys):
    import json

    root = _dimensional_canon(tmp_path)
    extraction = tmp_path / "canon.json"
    extraction.write_text(json.dumps(check_canon.build_canon_json(root)), encoding="utf-8")
    assert check_canon.cli([str(extraction)]) == 0
    out = capsys.readouterr().out
    assert "dimensional check over 8 canonical formulas" in out
    assert "MISMATCH" in out
