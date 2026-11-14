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


#: quantities of the review reproductions (#1384): (slug, symbol, unit)
REPRO_UNITS = [
    ("lift", "L", "N"),
    ("speed", "V", "m/s"),
    ("approach-speed", "V_app", "m/s"),
    ("mass", "m", "kg"),
    ("gravity", "g", "m/s^2"),
    ("radius", "R", "m"),
    ("distance", "x", "m"),
    ("wing-span", "b_ref", "m"),
    ("distance-mm", "x_mm", "mm"),
    ("dynamic-pressure", "q", "Pa"),
    ("wing-area", "S_ref", "m^2"),
    ("roll-rate", "p", "deg/s"),
    ("climb-angle", "gamma", "deg"),
    ("bank-angle", "phi", "deg"),
    ("lift-coefficient", "C_L", "1"),
    ("wing-moment", "C_m0_w", "1"),
    ("energy-height-rate", "P_s", "m/s"),
]
REPRO_IN = {
    "v": "speed",
    "v_app": "approach-speed",
    "m": "mass",
    "g": "gravity",
    "r": "radius",
    "b_ref": "wing-span",
    "x_mm": "distance-mm",
    "q": "dynamic-pressure",
    "s_ref": "wing-area",
    "p": "roll-rate",
    "gamma": "climb-angle",
    "phi": "bank-angle",
    "c_l": "lift-coefficient",
    "c_m0_w": "wing-moment",
}
REPRO_OUT = {"l": "lift", "x": "distance"}


def _read(tmp_path, form, inputs=None, outputs=None, units=None):
    """The verdicts the statement check gives one canonical form, in order."""
    canon = _statement_canon(
        tmp_path / f"form-{len(list(tmp_path.iterdir()))}",
        form,
        REPRO_IN if inputs is None else inputs,
        REPRO_OUT if outputs is None else outputs,
        REPRO_UNITS if units is None else units,
    )
    return [s.verdict for s in check_canon.check_statements(canon)]


def test_a_statement_is_not_cut_at_a_run_of_blanks(tmp_path):
    """Review finding 1: the part after two blanks belongs to the statement."""
    assert _read(tmp_path, "L = m * g  - V") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L = m  * g") == ["OK"]
    assert _read(tmp_path, "x = R * (1 + V / V)  + V") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L = m  * g  + V") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L = m * g      level flight") == ["UNPARSEABLE"]


def test_a_statement_continues_on_the_next_line_after_a_dangling_operator(tmp_path):
    assert _read(tmp_path, "L = m * g\n    + V") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L = m *\n    g") == ["OK"]
    assert _read(tmp_path, "L = m * (g\n    + V)") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L = m * g *\nV = V_app\nx := R") == ["UNPARSEABLE", "OK"]
    assert _read(tmp_path, "1) L = m * g\nV = m") == ["UNPARSEABLE", "MISMATCH"]


def test_two_blanks_separate_statements_that_each_have_one_equals_sign(tmp_path):
    assert _read(tmp_path, "L = m * g     V = V_app") == ["OK", "OK"]
    assert _read(tmp_path, "L = m * g,   x = R;   V = L") == ["OK", "OK", "MISMATCH"]
    assert _read(tmp_path, "L = m * g          (V = V_app)") == ["OK", "OK"]


def test_a_bracket_inside_a_statement_is_read_not_dropped(tmp_path):
    """Review finding 1: a bracket is a grouping or it makes the statement unreadable."""
    assert _read(tmp_path, "x = R * [1 + V]") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "x = R * [1 + V / V]") == ["OK"]
    assert _read(tmp_path, "L = q * S_ref[i] * C_L") == ["UNPARSEABLE"]


def test_a_trailing_citation_or_remark_is_dropped_and_the_statement_still_judged(tmp_path):
    assert _read(tmp_path, "V = m  [Anderson 5.3]") == ["MISMATCH"]
    assert _read(tmp_path, "V = m          (catalogue mass in g -> kg)") == ["MISMATCH"]
    assert _read(tmp_path, "V = m          # the mass") == ["MISMATCH"]


def test_a_trailing_group_that_reads_as_an_expression_is_not_taken_for_a_remark(tmp_path):
    assert _read(tmp_path, "x = R  (m)") == ["UNPARSEABLE"]
    assert _read(tmp_path, "L = m * g [N]") == ["UNPARSEABLE"]


def test_a_line_with_two_equals_signs_in_one_statement_is_reported_unparseable(tmp_path):
    """Review finding 15: such a line must not vanish from the tally."""
    assert _read(tmp_path, "E = L / W = C_L / C_L") == ["UNPARSEABLE"]


def test_a_sum_of_unlike_quantities_beside_a_number_is_found(tmp_path):
    """Review finding 2: a number on one side skips the balance, not the reading."""
    assert _read(tmp_path, "0 = L - V") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "L + V = 0") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "0 = L - m * g") == ["CONSTANT"]
    assert _read(tmp_path, "0 = L - stranger") == ["UNKNOWN_SYMBOL"]


def test_a_defined_name_keeps_the_degrees_of_its_right_side(tmp_path):
    """Review finding 3: a renamed angle in degrees is still an angle in degrees."""
    assert _read(tmp_path, "x = R * gamma") == ["ANGLE"]
    assert _read(tmp_path, "gamma_r = gamma\nx = R * gamma_r") == ["DEFINES", "ANGLE"]
    assert _read(tmp_path, "gamma_r = (pi/180) * gamma\nx = R * gamma_r") == ["DEFINES", "OK"]


def test_a_name_with_a_letter_outside_ascii_is_unknown_and_never_stored(tmp_path):
    """Review finding 4: `η_p` is not `p`, and `ρ` defines nothing that `μ` could find."""
    assert _read(tmp_path, "η_p = L / m") == ["UNKNOWN_SYMBOL"]
    assert _read(tmp_path, "ρ = m / S_ref\nμ = L / m\nV = μ") == ["UNKNOWN_SYMBOL"] * 3


def test_tau_is_a_name_like_any_other(tmp_path):
    """Review finding 5: only `pi` is a constant of the statement check."""
    assert _read(tmp_path, "tau = m / q") == ["DEFINES"]
    assert _read(tmp_path, "x = 2 * pi * R") == ["OK"]


def test_a_name_with_a_digit_and_a_float_in_scientific_notation_are_read_whole(tmp_path):
    """Review finding 6: `C_m0_w` is one name and `1e-3` one number."""
    assert _read(tmp_path, "L = C_m0_w * q * S_ref") == ["OK"]
    assert _read(tmp_path, "L = m * g * 1e-3") == ["OK"]
    assert _read(tmp_path, "L = 2m * g") == ["OK"]


def test_the_argument_of_a_function_must_be_dimensionless(tmp_path):
    """Review finding 7."""
    assert _read(tmp_path, "x = R * sin(V)") == ["MISMATCH"]
    assert _read(tmp_path, "x = R * exp(m)") == ["MISMATCH"]
    assert _read(tmp_path, "x = R * exp(V / V_app)") == ["OK"]


def test_degrees_inside_a_trigonometric_function_need_a_conversion(tmp_path):
    """Review finding 7: the degree rule holds for the argument too."""
    assert _read(tmp_path, "C_L = sin(gamma)") == ["ANGLE"]
    assert _read(tmp_path, "C_L = sin((pi/180) * gamma)") == ["OK"]
    assert _read(tmp_path, "0 = cos(gamma)") == ["ANGLE"]


def test_millimetres_do_not_balance_metres(tmp_path, capsys):
    """Review finding 8: the length scale is compared, a visible power of ten settles it."""
    assert _read(tmp_path, "x = x_mm") == ["SCALE"]
    assert _read(tmp_path, "x = R + x_mm") == ["SCALE"]
    assert _read(tmp_path, "x = x_mm / 1000") == ["OK"]
    assert _read(tmp_path, "x = 1e-3 * x_mm") == ["OK"]
    assert "SCALE" in check_canon.STATEMENT_ERRORS


def test_a_binding_in_another_case_wins_over_an_exact_register_match(tmp_path):
    """Review finding 9: bindings first. `P` is the bound shaft power, not the pressure."""
    units = [
        ("shaft-power", "P_shaft", "W"),
        ("static-pressure", "P", "Pa"),
        ("torque", "Q_m", "N*m"),
        ("omega", "omega", "1/s"),
    ]
    inputs, outputs = {"q_m": "torque", "omega": "omega"}, {"p": "shaft-power"}
    assert _read(tmp_path, "P = Q_m * omega", inputs, outputs, units) == ["OK"]
    units = [
        ("stall-speed", "V_S", "m/s"),
        ("shear", "V_s", "N"),
        ("margin", "k_S", "1"),
        ("approach-speed", "V_app", "m/s"),
    ]
    inputs, outputs = {"k_s": "margin", "v_s": "stall-speed"}, {"v_app": "approach-speed"}
    assert _read(tmp_path, "V_app = k_S * V_s", inputs, outputs, units) == ["OK"]


def test_a_name_matches_without_regard_to_case_when_nothing_matches_exactly(tmp_path):
    assert _read(tmp_path, "V = V_APP") == ["OK"]
    assert _read(tmp_path, "x = V_APP") == ["MISMATCH"]


def test_a_single_letter_never_matches_in_another_case(tmp_path):
    """`M` is not the bound mass `m`: the statement defines it."""
    assert _read(tmp_path, "M = L * R") == ["DEFINES"]


def test_two_names_that_differ_only_in_case_are_both_read(tmp_path):
    units = [("power", "P", "W"), ("pressure", "p", "Pa"), ("flow", "Vdot", "m^3/s")]
    inputs, outputs = {"p": "pressure", "vdot": "flow"}, {"power": "power"}
    assert _read(tmp_path, "P = p * Vdot", inputs, outputs, units) == ["OK"]
    assert _read(tmp_path, "P = p * P", inputs, outputs, units) == ["MISMATCH"]


def test_a_trailing_qualifier_is_dropped_only_after_a_separator(tmp_path):
    """Review finding 10: `psi` is a name of its own, never `P_s` with a qualifier `i`."""
    assert _read(tmp_path, "V = V_app,max") == ["OK"]
    assert _read(tmp_path, "x = V_app_max") == ["MISMATCH"]
    assert _read(tmp_path, "psi = L / m") == ["DEFINES"]
    assert _read(tmp_path, "V = psi * 2") == ["UNKNOWN_SYMBOL"]


def test_a_qualifier_is_not_dropped_down_to_a_single_letter(tmp_path):
    """`x_1` is a name of its own beside the bound `x`."""
    assert _read(tmp_path, "x_1 = L\nV = x_1") == ["DEFINES", "MISMATCH"]


def test_register_names_that_differ_only_in_case_match_as_written_or_not_at_all(tmp_path):
    units = [("stall-speed", "V_S", "m/s"), ("shear", "V_s", "N"), ("speed", "V", "m/s")]
    assert _read(tmp_path, "V = V_S,max", {}, {"v": "speed"}, units) == ["OK"]
    assert _read(tmp_path, "V = V_s,max", {}, {"v": "speed"}, units) == ["MISMATCH"]
    assert _read(tmp_path, "V = v_s", {}, {"v": "speed"}, units) == ["UNKNOWN_SYMBOL"]


def test_the_arguments_of_max_and_min_are_compared(tmp_path):
    """Review finding 11."""
    assert _read(tmp_path, "x = max(R, b_ref)") == ["OK"]
    assert _read(tmp_path, "x = max(R, V)") == ["ADDS_UNLIKE"]
    assert _read(tmp_path, "x = min(V_app,b_ref)") == ["UNPARSEABLE"]


def test_a_name_before_a_parenthesised_expression_is_no_point_call(tmp_path):
    """Review finding 12: only a plain list of names is a quantity taken at a point."""
    assert _read(tmp_path, "L(V, gamma) = m * g") == ["OK"]
    assert _read(tmp_path, "L = q*S_ref(C_L + V)") == ["UNPARSEABLE"]


def test_an_arithmetic_error_makes_the_statement_unparseable(tmp_path):
    """Review finding 13: the scale of `x_mm ^ 400` underflows to zero."""
    assert _read(tmp_path, "x_mm = x_mm ^ 400 / x_mm ^ 399") == ["UNPARSEABLE"]
    assert _read(tmp_path, "L = m * g * 10 ^ 400") == ["UNPARSEABLE"]


def test_an_unlike_sum_is_a_finding_that_fails_the_run(tmp_path, capsys):
    canon = _statement_canon(tmp_path, "L = m * g + V", REPRO_IN, REPRO_OUT, REPRO_UNITS)
    rows = check_canon.check_statements(canon)
    assert [r.verdict for r in rows] == ["ADDS_UNLIKE"]
    assert check_canon.print_statements(rows) == 1
    assert "f [ADDS_UNLIKE] L = m * g + V" in capsys.readouterr().out


def test_the_cli_exits_1_on_a_statement_finding_and_0_without(tmp_path, typed_quantities):
    """The fixture formula reads `v = a + b`; with `b` in metres the sum is unlike."""
    clean = _canon(tmp_path / "clean", quantities=typed_quantities)
    assert check_canon.cli([str(clean)]) == 0
    unlike = dict(typed_quantities)
    unlike["speed-b"] = unlike["speed-b"].replace("unit: m/s", "unit: m")
    assert check_canon.cli([str(_canon(tmp_path / "unlike", quantities=unlike))]) == 1


def test_degrees_beside_radians_need_a_conversion_even_when_the_angles_cancel(tmp_path):
    units = [
        ("lift-coefficient", "C_L", "1"),
        ("lift-slope", "C_L_alpha", "1/rad"),
        ("angle-of-attack", "alpha", "deg"),
    ]
    inputs, outputs = (
        {"c_l_alpha": "lift-slope", "alpha": "angle-of-attack"},
        {"c_l": "lift-coefficient"},
    )
    assert _read(tmp_path, "C_L = C_L_alpha * alpha", inputs, outputs, units) == ["ANGLE"]
    assert _read(tmp_path, "C_L = C_L_alpha * alpha * pi/180", inputs, outputs, units) == ["OK"]


def test_bars_are_read_as_the_absolute_value(tmp_path):
    assert _read(tmp_path, "L = |m| * g") == ["OK"]
    assert _read(tmp_path, "L = |m + V| * g") == ["ADDS_UNLIKE"]


def test_the_bindings_of_the_applications_are_read(tmp_path):
    """`k` and `t` are bound by the application only, and the register has other units for them."""
    units = [
        ("stiffness", "k", "N/m"),
        ("margin", "k_S", "1"),
        ("duration", "t", "s"),
        ("stall-speed", "V_S0", "m/s"),
        ("approach-speed", "V_app", "m/s"),
    ]
    _statement_canon(
        tmp_path, "t = k * V_S0", {"k": None, "v_s0": "stall-speed"}, {"t": None}, units
    )
    path = tmp_path / "canon" / "formulas" / "f.md"
    front, body = path.read_text(encoding="utf-8").split("---\n", 2)[1:]
    applications = [{"bind": {"k": "margin"}, "produce": {"t": "approach-speed"}}]
    front = yaml.safe_dump({**yaml.safe_load(front), "applications": applications})
    path.write_text(f"---\n{front}---\n{body}", encoding="utf-8")
    canon = check_canon.load_canon(tmp_path / "canon")
    assert _verdicts(canon) == [("t = k * V_S0", "OK")]


def test_a_statement_defines_nothing_while_other_names_are_unknown(tmp_path):
    form = "tau = m / stranger\nL = tau"
    assert _read(tmp_path, form) == ["UNKNOWN_SYMBOL", "UNKNOWN_SYMBOL"]


def test_roots_and_exponents_are_evaluated(tmp_path):
    assert _read(tmp_path, "V = sqrt(L / m * R / R * x / x) * sqrt(g * R) / V") == ["MISMATCH"]
    assert _read(tmp_path, "V = sqrt(g * R)") == ["OK"]
    assert _read(tmp_path, "V = (g * R)^0.5") == ["OK"]
    assert _read(tmp_path, "V = (g * R)^(1/2)") == ["OK"]
    assert _read(tmp_path, "V = g * R") == ["MISMATCH"]
    assert _read(tmp_path, "S_ref = R^2") == ["OK"]
    assert _read(tmp_path, "S_ref = R^3") == ["MISMATCH"]
    assert _read(tmp_path, "S_ref = R^gamma") == ["UNPARSEABLE"]


def test_a_defined_name_is_checked_where_it_is_used_again(tmp_path):
    assert _read(tmp_path, "a_c = V^2 / R\nL = m * a_c\nV = a_c") == ["DEFINES", "OK", "MISMATCH"]


#: simple laws of the real canon whose every symbol is bound by the formula itself; while the
#: check reads the real canon they balance, and a reader that stops reading them shows here
REAL_ANCHORS = {
    ("dynamic-pressure", "q = 0.5 * rho * V^2"),
    ("weight-from-mass", "W = m * g"),
    ("aspect-ratio", "AR = b_ref^2 / S_ref"),
    ("stall-speed", "L(V, alpha) = n * m * g"),
}


def test_the_real_canon_has_no_statement_finding():
    canon = check_canon.load_canon(REAL_CANON)
    rows = check_canon.check_statements(canon)
    assert [(r.formula, r.text) for r in rows if r.verdict in check_canon.STATEMENT_ERRORS] == []
    assert {(r.formula, r.text) for r in rows if r.verdict == "OK"} >= REAL_ANCHORS
