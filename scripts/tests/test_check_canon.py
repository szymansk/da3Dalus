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
import yaml

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
        "v = a + b",
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
        ("volume", "Vol", "m^3"),
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
        "cuberoot": ("distance", "d = cbrt(Vol)"),
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
        "cuberoot": "BALANCES",
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
    assert "dimensional check over 9 canonical formulas" in out
    assert "MISMATCH" in out


def test_run_as_a_script_the_authoring_check_exits_1_on_a_finding(tmp_path):
    """CI runs ``python scripts/check_canon.py``; the entry point must exit with the result."""
    import subprocess

    root = _canon(tmp_path, inputs_line=("speed-a",))
    done = subprocess.run(
        [sys.executable, str(SCRIPTS / "check_canon.py"), str(root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 1
    assert "speed-b" in done.stdout


def test_a_file_with_exactly_one_separator_does_not_crash_and_keeps_its_prose(
    tmp_path, typed_quantities
):
    """A lone ``---`` is no front matter (the importer reports it); the prose is still read."""
    root = _canon(tmp_path, quantities=typed_quantities)
    path = root / "quantities" / "speed-b.md"
    path.write_text(
        "---\ncanon: speed-b\n\nonly one separator\n**Used by.** [[f]]\n", encoding="utf-8"
    )
    entry = check_canon.load_canon(root).quantities["speed-b"]
    assert entry.front == {}
    assert "**Used by.** [[f]]" in entry.body
    assert _errors(root) == []


def test_a_file_without_front_matter_keeps_its_prose(tmp_path, typed_quantities):
    root = _canon(tmp_path, quantities=typed_quantities)
    (root / "quantities" / "speed-b.md").write_text("prose\n**Used by.** [[f]]\n", encoding="utf-8")
    entry = check_canon.load_canon(root).quantities["speed-b"]
    assert entry.front == {}
    assert entry.body == "prose\n**Used by.** [[f]]\n"
    assert _errors(root) == []


def test_the_cli_runs_the_dimensional_check_over_a_canon_directory(tmp_path, capsys):
    root = _dimensional_canon(tmp_path)
    (root / "README.md").write_text("# Canon\n", encoding="utf-8")
    check_canon.cli([str(root)])
    out = capsys.readouterr().out
    assert "dimensional check over 9 canonical formulas" in out
    assert "MISMATCH" in out
    assert "ADDS_UNLIKE" in out


def test_the_procedural_pattern_decides_before_the_dimensions_are_compared(tmp_path):
    """Without the pattern these forms would be reported as unlike sums or wrong dimensions."""
    root = _dimensional_canon(tmp_path)
    for slug, form in (
        ("where", "d = d + t  where t is measured"),
        ("solve", "V_s = d * t, solve for d"),
        ("table", "V_s = d * t from a table"),
        ("maximize", "d = d + t, maximize d"),
        ("maximise", "d = d + t, maximise d"),
        ("minimise", "d = d + t, minimise d"),
    ):
        (root / "formulas" / f"{slug}.md").write_text(
            f"---\ncanon: {slug}\noutput: speed\nkind: law\n---\n\n"
            f"**Canonical form**\n\n```\n{form}\n```\n",
            encoding="utf-8",
        )
    rows = check_canon.dimensional_rows(check_canon.build_canon_json(root))
    verdicts = {f["slug"]: verdict for verdict, f, *_ in rows}
    decided = ("where", "solve", "table", "maximize", "maximise", "minimise")
    assert {verdicts[slug] for slug in decided} == {"PROCEDURAL"}


# --- dimensional check per statement, through the formula's bindings (#1379) -------------------


def _statement_canon(tmp_path, form, inputs, outputs, units):
    """A canon with one formula `f` and one quantity per (slug, symbol, unit) triple."""
    root = tmp_path / "canon"
    (root / "formulas").mkdir(parents=True)
    (root / "quantities").mkdir()
    (root / "README.md").write_text(README, encoding="utf-8")
    for slug, symbol, unit in units:
        (root / "quantities" / f"{slug}.md").write_text(
            f'---\ncanon: {slug}\nsymbol: "{symbol}"\nunit: "{unit}"\n---\n\n# {slug}\n',
            encoding="utf-8",
        )
    front = yaml.safe_dump({"canon": "f", "inputs": inputs, "outputs": outputs})
    (root / "formulas" / "f.md").write_text(
        f"---\n{front}---\n\n# f\n\n**Canonical form**\n\n```\n{form}\n```\n", encoding="utf-8"
    )
    return check_canon.load_canon(root)


ROLL_UNITS = [
    ("roll-rate", "p", "deg/s"),
    ("roll-helix", "p_hat", "1"),
    ("wing-span", "b_ref", "m"),
    ("approach-speed", "V_app", "m/s"),
]
ROLL_IN = {"b_ref": "wing-span", "v_app": "approach-speed"}
ROLL_OUT = {"p": "roll-rate", "p_hat": "roll-helix"}


def _verdicts(canon):
    return [(s.text, s.verdict) for s in check_canon.check_statements(canon)]


def test_a_statement_of_a_procedural_form_is_checked(tmp_path):
    """The second line of a `solve for` form is a statement like any other (review finding W4)."""
    form = "solve for alpha, p:   L(V, alpha) = m * g\nevaluated at V = V_app;   p_hat = p * b_ref / (2 * V_app)"
    canon = _statement_canon(tmp_path, form, ROLL_IN, ROLL_OUT, ROLL_UNITS)
    assert ("p_hat = p * b_ref / (2 * V_app)", "ANGLE") in _verdicts(canon)


def test_a_visible_conversion_settles_the_angle(tmp_path):
    form = "p_hat = (pi/180) * p * b_ref / (2 * V_app)"
    canon = _statement_canon(tmp_path, form, ROLL_IN, ROLL_OUT, ROLL_UNITS)
    assert _verdicts(canon) == [(form, "OK")]


def test_radians_count_as_dimensionless(tmp_path):
    units = [("gain", "kappa", "rad"), ("c-l-r", "C_l_r", "1/rad"), ("c-l-b", "C_l_beta", "1/rad")]
    form = "kappa      = -C_l_r / C_l_beta        # rad"
    canon = _statement_canon(
        tmp_path, form, {"c_l_r": "c-l-r", "c_l_beta": "c-l-b"}, {"kappa": "gain"}, units
    )
    assert _verdicts(canon) == [("kappa = -C_l_r / C_l_beta", "OK")]


def test_a_wrong_dimension_is_a_mismatch(tmp_path):
    form = "subject to:   p = b_ref * V_app"
    canon = _statement_canon(tmp_path, form, ROLL_IN, ROLL_OUT, ROLL_UNITS)
    assert _verdicts(canon) == [("p = b_ref * V_app", "MISMATCH")]


def test_the_binding_decides_between_two_quantities_with_one_symbol(tmp_path):
    """`w` is the sink rate here because the formula binds it, whatever the register lists first."""
    units = [
        ("a-weight", "w", "N"),
        ("sink-rate", "w", "m/s"),
        ("speed", "V", "m/s"),
        ("angle", "g_sin", "1"),
    ]
    form = "w = V * g_sin"
    canon = _statement_canon(
        tmp_path, form, {"v": "speed", "g_sin": "angle"}, {"w": "sink-rate"}, units
    )
    assert _verdicts(canon) == [(form, "OK")]


def test_case_is_kept_for_a_single_letter(tmp_path):
    """`Q` is not the dynamic pressure `q`: unknown, so the statement defines it."""
    units = [("dynamic-pressure", "q", "Pa"), ("speed", "V", "m/s"), ("power", "P", "W")]
    form = "Q = P / V\nP = Q * V"
    canon = _statement_canon(tmp_path, form, {"v": "speed"}, {"p": "power"}, units)
    assert _verdicts(canon) == [("Q = P / V", "DEFINES"), ("P = Q * V", "OK")]


def test_what_cannot_be_read_is_not_judged(tmp_path):
    form = "g_0 = 9.81\np = unknown_thing * b_ref\nt = crossing of p with b_ref\nn >= 1,  p := solver(b_ref)"
    canon = _statement_canon(tmp_path, form, ROLL_IN, ROLL_OUT, ROLL_UNITS)
    assert [v for _, v in _verdicts(canon)] == ["CONSTANT", "UNKNOWN_SYMBOL", "UNPARSEABLE"]


def test_a_statement_finding_fails_the_run(tmp_path, capsys):
    form = "p = b_ref * V_app"
    canon = _statement_canon(tmp_path, form, ROLL_IN, ROLL_OUT, ROLL_UNITS)
    assert check_canon.print_statements(check_canon.check_statements(canon)) == 1
    assert "f [MISMATCH] p = b_ref * V_app" in capsys.readouterr().out


def test_the_real_canon_has_no_statement_finding():
    canon = check_canon.load_canon(REAL_CANON)
    rows = check_canon.check_statements(canon)
    assert [(r.formula, r.text) for r in rows if r.verdict in check_canon.STATEMENT_ERRORS] == []
    assert sum(r.verdict == "OK" for r in rows) >= 50
