"""Tests for the structural cross-checks of scripts/check_canon.py (#1181).

Each test builds a small canon directory — README with the closed vocabularies, quantity
entries, formula entries — and asserts which findings the checker reports. The last tests
run the checker over the real canon document.
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

#### Vocabulary of `when`

| term | holds when |
|---|---|
| `has_flap` | the main wing carries a flap |

#### Quantity types

| type | what the value is |
|---|---|
| `scalar` | one number |
| `airplane` | the aircraft model |
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


GOOD_FRONT = """
inputs: {a: speed-a, b: speed-b}
outputs: {v: speed-v}
"""


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
    return check_canon.check_structure(check_canon.load_canon(root))


def _errors(root):
    return [f for f in _findings(root) if not f.open]


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


# --- the vocabularies come from the README ------------------------------------------------


def test_vocabulary_and_types_are_read_from_the_readme(tmp_path):
    canon = check_canon.load_canon(_canon(tmp_path))
    assert canon.vocabulary == {"has_flap"}
    assert canon.types == {"scalar", "airplane"}


def test_a_consistent_canon_has_no_findings(tmp_path, typed_quantities):
    assert _findings(_canon(tmp_path, quantities=typed_quantities)) == []


# --- formula front matter against the prose line ---------------------------------------------


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


# --- quantity links against the formulas -----------------------------------------------------


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


# --- references resolve -------------------------------------------------------------------


def test_unknown_quantity_slug_in_a_binding_is_reported(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: no-such-quantity}
"""
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("no-such-quantity" in m for m in msgs), msgs


# --- applications ----------------------------------------------------------------------------


def test_when_term_outside_the_vocabulary_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "applications:\n  - id: one\n    when: has_canard\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("has_canard" in m for m in msgs), msgs


def test_when_term_in_the_vocabulary_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "applications:\n  - id: one\n    when: has_flap\n"
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_parameter_left_unbound_by_an_application_is_reported(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {a: speed-a}
"""
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    msgs = _messages(_errors(root))
    assert any("application one" in m and "'b'" in m for m in msgs), msgs


PRODUCE_FRONT = """
inputs: {a: speed-a, b: speed-b}
outputs: {v: null, w: null}
applications:
  - id: one
    produce: {v: speed-v, w: null}
"""


def test_an_output_explicitly_produced_as_null_is_accepted(tmp_path, typed_quantities):
    """`produce: {w: null}` — the implementation returns it, the application does not expose it."""
    assert _findings(_canon(tmp_path, front=PRODUCE_FRONT, quantities=typed_quantities)) == []


def test_an_output_absent_from_produce_is_reported(tmp_path, typed_quantities):
    front = PRODUCE_FRONT.replace("produce: {v: speed-v, w: null}", "produce: {v: speed-v}")
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("application one" in m and "'w'" in m for m in msgs), msgs


def test_default_application_needs_every_default(tmp_path, typed_quantities):
    front = "inputs: {a: speed-a, b: null}\noutputs: {v: speed-v}\n"
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    msgs = _messages(_errors(root))
    assert any("'b'" in m for m in msgs), msgs


def test_an_escalated_entry_reports_its_gap_as_open_not_as_an_error(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  # ESCALATED: b has no decided binding
  - id: one
    bind: {a: speed-a}
"""
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    findings = _findings(root)
    assert [f for f in findings if not f.open] == []
    assert any(f.open and "'b'" in f.message for f in findings)


def test_constant_binding_needs_a_source(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: {const: 1.3}}
"""
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    msgs = _messages(_errors(root))
    assert any("source" in m for m in msgs), msgs


def test_constant_binding_with_a_source_is_accepted(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: {const: 1.3, source: "CS 25.125"}}
"""
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    assert _errors(root) == []


def test_bind_key_that_is_not_an_input_parameter_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "applications:\n  - id: one\n    bind: {c: speed-a}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("'c'" in m for m in msgs), msgs


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


GIVEN_FRONT = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  - id: one
    bind: {b: speed-b}
    given: [speed-b]
"""


def _as_target(quantities, slug):
    quantities[slug] = quantities[slug].replace("role: derived", "role: target")
    return quantities


def test_given_input_that_the_application_binds_is_accepted(tmp_path, typed_quantities):
    quantities = _as_target(typed_quantities, "speed-b")
    assert _findings(_canon(tmp_path, front=GIVEN_FRONT, quantities=quantities)) == []


def test_given_slug_must_exist(tmp_path, typed_quantities):
    front = GIVEN_FRONT.replace("given: [speed-b]", "given: [no-such-quantity]")
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("given" in m and "no-such-quantity" in m for m in msgs), msgs


def test_given_slug_must_be_an_input_or_target(tmp_path, typed_quantities):
    msgs = _messages(_errors(_canon(tmp_path, front=GIVEN_FRONT, quantities=typed_quantities)))
    assert any("given" in m and "speed-b" in m and "role" in m for m in msgs), msgs


def test_given_slug_must_have_no_default(tmp_path, typed_quantities):
    quantities = _as_target(typed_quantities, "speed-b")
    quantities["speed-b"] = quantities["speed-b"].replace(
        "type: scalar", 'type: scalar\ndefault: {value: 1.0, source: "x"}'
    )
    msgs = _messages(_errors(_canon(tmp_path, front=GIVEN_FRONT, quantities=quantities)))
    assert any("given" in m and "default" in m for m in msgs), msgs


def test_given_slug_must_be_bound_by_the_application(tmp_path, typed_quantities):
    quantities = _as_target(typed_quantities, "speed-a")
    front = GIVEN_FRONT.replace("given: [speed-b]", "given: [speed-a, speed-b]")
    quantities = _as_target(quantities, "speed-b")
    assert _errors(_canon(tmp_path, front=front, quantities=quantities)) == []
    front = GIVEN_FRONT.replace("bind: {b: speed-b}", "bind: {a: speed-b, b: speed-b}").replace(
        "given: [speed-b]", "given: [speed-a]"
    )
    msgs = _messages(_errors(_canon(tmp_path / "x", front=front, quantities=quantities)))
    assert any("given" in m and "speed-a" in m and "not bound" in m for m in msgs), msgs


def _second_formula():
    """A formula `g` that `f` can embed; it reads speed-a and writes nothing anyone else reads."""
    return (
        "g",
        _formula("g", ["speed-w"], ["speed-a"], "inputs: {a: speed-a}\noutputs: {w: speed-w}\n"),
    )


def _with_g(quantities):
    quantities["speed-a"] = quantities["speed-a"].replace("[[f]]", "[[f]] · [[g]]")
    quantities["speed-w"] = _with_type({"w": _quantity("speed-w", produced_by=["g"])})["w"]
    return quantities


def test_embeds_naming_existing_formulas_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "embeds: [g]\nvariables: []\n"
    root = _canon(
        tmp_path,
        front=front,
        quantities=_with_g(typed_quantities),
        extra_formulas=[_second_formula()],
    )
    assert _findings(root) == []


def test_embeds_naming_an_unknown_formula_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "embeds: [no-such-formula]\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("embeds" in m and "no-such-formula" in m for m in msgs), msgs


def test_embeds_must_not_name_the_formula_itself(tmp_path, typed_quantities):
    front = GOOD_FRONT + "embeds: [f]\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("embeds" in m and "itself" in m for m in msgs), msgs


def _embed_canon(tmp_path, formulas):
    """A canon of formulas {slug: (inputs, outputs, extra front)} with consistent quantity links."""
    root = tmp_path / "canon"
    (root / "formulas").mkdir(parents=True)
    (root / "quantities").mkdir()
    (root / "README.md").write_text(README, encoding="utf-8")
    readers, producers = {}, {}
    for slug, (inputs, outputs, extra) in formulas.items():
        for q in inputs.values():
            readers.setdefault(q, []).append(slug)
        for q in outputs.values():
            producers.setdefault(q, []).append(slug)
        front = (
            "inputs: {" + ", ".join(f"{k}: {v}" for k, v in inputs.items()) + "}\n"
            "outputs: {" + ", ".join(f"{k}: {v}" for k, v in outputs.items()) + "}\n" + extra
        )
        text = _formula(slug, list(outputs.values()), list(inputs.values()), front)
        (root / "formulas" / f"{slug}.md").write_text(text, encoding="utf-8")
    for q in sorted(set(readers) | set(producers)):
        text = _with_type({q: _quantity(q, producers.get(q, ()), readers.get(q, ()))})[q]
        (root / "quantities" / f"{q}.md").write_text(text, encoding="utf-8")
    return root


def test_embedded_inputs_bound_produced_inside_or_variables_are_accepted(tmp_path):
    """f embeds g, g embeds h: h's output feeds g inside the closure; flight-speed is f's variable."""
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [g]\nvariables: [flight-speed]\n"),
            "g": (
                {"a": "speed-a", "w": "speed-w"},
                {"x": "speed-x"},
                "embeds: [h]\nvariables: [flight-speed]\n",
            ),
            "h": ({"a": "speed-a", "s": "flight-speed"}, {"w": "speed-w"}, ""),
        },
    )
    assert _findings(root) == []


def test_embedded_input_the_embedder_does_not_supply_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\nvariables: []\n"),
            "h": ({"a": "speed-a", "b": "speed-b"}, {"w": "speed-w"}, ""),
        },
    )
    msgs = _messages(_errors(root))
    assert any("f embeds" in m and "speed-b" in m for m in msgs), msgs


def test_embeds_through_a_chain_is_checked_transitively(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [g]\nvariables: []\n"),
            "g": (
                {"a": "speed-a", "b": "speed-b"},
                {"x": "speed-x"},
                "embeds: [h]\nvariables: []\n",
            ),
            "h": ({"b": "speed-b", "c": "speed-c"}, {"w": "speed-w"}, ""),
        },
    )
    msgs = _messages(_errors(root))
    assert any("f embeds" in m and "speed-b" in m for m in msgs), msgs
    assert any("f embeds" in m and "speed-c" in m for m in msgs), msgs
    assert any("g embeds" in m and "speed-c" in m for m in msgs), msgs


def test_an_embeds_cycle_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [g]\nvariables: []\n"),
            "g": ({"a": "speed-a"}, {"x": "speed-x"}, "embeds: [f]\nvariables: []\n"),
        },
    )
    msgs = _messages(_errors(root))
    assert any("embeds" in m and "cycle" in m for m in msgs), msgs


def test_a_formula_with_worlds_in_the_closure_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\nvariables: []\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, "uncertainty: interval\nworlds: [avl]\n"),
        },
    )
    msgs = _messages(_errors(root))
    assert any("f embeds" in m and "interval" in m for m in msgs), msgs


def test_a_generic_quantity_is_no_longer_free_without_variables(tmp_path):
    """Round 2, D: flight-speed in the closure must be one of the embedder's variables."""
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\nvariables: []\n"),
            "h": ({"a": "speed-a", "s": "flight-speed"}, {"w": "speed-w"}, ""),
        },
    )
    msgs = _messages(_errors(root))
    assert any("f embeds" in m and "flight-speed" in m for m in msgs), msgs


def test_embeds_needs_variables(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, ""),
        },
    )
    msgs = _messages(_errors(root))
    assert any("variables" in m for m in msgs), msgs


def test_a_variable_no_formula_in_the_closure_reads_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\nvariables: [speed-z]\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, ""),
        },
    )
    msgs = _messages(_errors(root))
    assert any("variables" in m and "speed-z" in m for m in msgs), msgs


TWO_APPS = "applications:\n  - id: one\n  - id: two\n"


def test_embedding_one_application_of_a_multi_application_formula_is_accepted(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h.one]\nvariables: []\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, TWO_APPS),
        },
    )
    assert _findings(root) == []


def test_embedding_a_multi_application_formula_bare_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h]\nvariables: []\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, TWO_APPS),
        },
    )
    msgs = _messages(_errors(root))
    assert any("embeds" in m and "'h'" in m and "application" in m for m in msgs), msgs


def test_embedding_an_unknown_application_is_reported(tmp_path):
    root = _embed_canon(
        tmp_path,
        {
            "f": ({"a": "speed-a"}, {"v": "speed-v"}, "embeds: [h.three]\nvariables: []\n"),
            "h": ({"a": "speed-a"}, {"w": "speed-w"}, TWO_APPS),
        },
    )
    msgs = _messages(_errors(root))
    assert any("embeds" in m and "h.three" in m for m in msgs), msgs


def _per_app_canon(tmp_path, item):
    """h has two applications binding b differently; f embeds one of them and reads speed-b."""
    h_front = (
        "applications:\n  - id: one\n    bind: {b: speed-b}\n  - id: two\n    bind: {b: speed-c}\n"
    )
    root = _embed_canon(
        tmp_path,
        {
            "f": (
                {"a": "speed-a", "b": "speed-b"},
                {"v": "speed-v"},
                f"embeds: [{item}]\nvariables: []\n",
            ),
            "h": ({"a": "speed-a", "b": "null"}, {"w": "speed-w"}, h_front),
        },
    )
    # the fixture builder cannot see application bindings: write h's from line and links by hand
    h = root / "formulas" / "h.md"
    h.write_text(
        h.read_text(encoding="utf-8").replace(
            "**from** [[speed-a]] · [[null]]", "**from** [[speed-a]] · [[speed-b]] · [[speed-c]]"
        ),
        encoding="utf-8",
    )
    (root / "quantities" / "null.md").unlink()
    for q, users in (("speed-b", ["f", "h"]), ("speed-c", ["h"])):
        text = _with_type({q: _quantity(q, used_by=users)})[q]
        (root / "quantities" / f"{q}.md").write_text(text, encoding="utf-8")
    return root


def test_the_input_rule_applies_to_the_embedded_application_only(tmp_path):
    """Review round 2: an item embeds that application as written, not the union of all."""
    assert _findings(_per_app_canon(tmp_path, "h.one")) == []


def test_the_input_rule_reports_what_the_embedded_application_binds(tmp_path):
    msgs = _messages(_errors(_per_app_canon(tmp_path, "h.two")))
    assert any("f embeds" in m and "speed-c" in m for m in msgs), msgs


def test_optional_naming_an_input_parameter_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "optional: [b]\n"
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_optional_naming_a_non_input_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "optional: [v, z]\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("optional" in m and "'v'" in m for m in msgs), msgs
    assert any("optional" in m and "'z'" in m for m in msgs), msgs


# --- naming ----------------------------------------------------------------------------------


def test_parameter_names_must_be_snake_case(tmp_path):
    front = "inputs: {a: speed-a, B-x: speed-b}\noutputs: {v: speed-v}\n"
    quantities = _with_type(
        {
            "speed-a": _quantity("speed-a", used_by=["f"]),
            "speed-b": _quantity("speed-b", used_by=["f"]),
            "speed-v": _quantity("speed-v", produced_by=["f"]),
        }
    )
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=quantities)))
    assert any("B-x" in m and "snake_case" in m for m in msgs), msgs


# --- preconditions, worlds, cost -------------------------------------------------------------


def test_precondition_on_an_unknown_parameter_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "preconditions:\n  - {id: check_x, parameter: x, on_violation: warning}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("preconditions" in m and "'x'" in m for m in msgs), msgs


def test_precondition_with_an_unknown_violation_mode_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "preconditions:\n  - {id: check_a, parameter: a, on_violation: abort}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("abort" in m for m in msgs), msgs


def test_a_well_formed_precondition_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "preconditions:\n  - {id: check_a, parameter: a, on_violation: error}\n"
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


SCOPED_FRONT = (
    GOOD_FRONT
    + """applications:
  - id: one
  - id: two
preconditions:
  - {id: check_a, parameter: a, on_violation: error, applications: [two]}
"""
)


def test_a_precondition_scoped_to_existing_applications_is_accepted(tmp_path, typed_quantities):
    assert _findings(_canon(tmp_path, front=SCOPED_FRONT, quantities=typed_quantities)) == []


def test_a_precondition_scoped_to_an_unknown_application_is_reported(tmp_path, typed_quantities):
    front = SCOPED_FRONT.replace("applications: [two]", "applications: [three]")
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("preconditions" in m and "'three'" in m for m in msgs), msgs


def test_a_precondition_scope_must_be_a_list(tmp_path, typed_quantities):
    front = SCOPED_FRONT.replace("applications: [two]", "applications: two")
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("preconditions" in m and "list" in m for m in msgs), msgs


def test_a_precondition_on_an_output_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "preconditions:\n  - {id: check_v, parameter: v, on_violation: error}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("preconditions" in m and "input" in m and "'v'" in m for m in msgs), msgs


def test_a_postcondition_on_an_output_is_accepted(tmp_path, typed_quantities):
    front = SCOPED_FRONT.replace("preconditions:", "postconditions:").replace(
        "parameter: a", "parameter: v"
    )
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_a_postcondition_on_an_input_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "postconditions:\n  - {id: check_a, parameter: a, on_violation: error}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("postconditions" in m and "output" in m and "'a'" in m for m in msgs), msgs


def test_a_postcondition_scoped_to_an_unknown_application_is_reported(tmp_path, typed_quantities):
    front = (
        SCOPED_FRONT.replace("preconditions:", "postconditions:")
        .replace("parameter: a", "parameter: v")
        .replace("applications: [two]", "applications: [three]")
    )
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("postconditions" in m and "'three'" in m for m in msgs), msgs


def test_a_postcondition_with_an_unknown_violation_mode_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "postconditions:\n  - {id: check_v, parameter: v, on_violation: abort}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("postconditions" in m and "abort" in m for m in msgs), msgs


def test_the_old_precondition_key_on_is_reported(tmp_path, typed_quantities):
    """`on` was renamed to `parameter`: YAML 1.1 reads a bare `on` as the boolean true."""
    front = GOOD_FRONT + "preconditions:\n  - {id: check_a, on: a, on_violation: error}\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("preconditions" in m for m in msgs), msgs


def test_interval_uncertainty_needs_worlds(tmp_path, typed_quantities):
    front = GOOD_FRONT + "uncertainty: interval\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("worlds" in m for m in msgs), msgs


def test_worlds_without_interval_uncertainty_are_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "worlds: [textbook, avl]\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("worlds" in m for m in msgs), msgs


def test_interval_with_worlds_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "uncertainty: interval\nworlds: [textbook, avl]\n"
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


def test_unknown_cost_class_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "cost: hours\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("hours" in m for m in msgs), msgs


# --- quantity fields -------------------------------------------------------------------------


def test_quantity_without_type_is_reported(tmp_path):
    msgs = _messages(_errors(_canon(tmp_path)))
    assert any("speed-a type" in m for m in msgs), msgs


def test_quantity_type_outside_the_set_is_reported(tmp_path, typed_quantities):
    typed_quantities["speed-a"] = typed_quantities["speed-a"].replace(
        "type: scalar", "type: tensor"
    )
    msgs = _messages(_errors(_canon(tmp_path, quantities=typed_quantities)))
    assert any("tensor" in m for m in msgs), msgs


def test_quantity_default_needs_a_source(tmp_path, typed_quantities):
    typed_quantities["speed-a"] = typed_quantities["speed-a"].replace(
        "type: scalar", "type: scalar\ndefault: {value: 1.225}"
    )
    msgs = _messages(_errors(_canon(tmp_path, quantities=typed_quantities)))
    assert any("speed-a default" in m for m in msgs), msgs


def test_quantity_default_with_a_source_is_accepted(tmp_path, typed_quantities):
    typed_quantities["speed-a"] = typed_quantities["speed-a"].replace(
        "type: scalar", 'type: scalar\ndefault: {value: 1.225, source: "ISA"}'
    )
    assert _findings(_canon(tmp_path, quantities=typed_quantities)) == []


# --- command line ----------------------------------------------------------------------------


# --- review round 1: robustness --------------------------------------------------------------


def test_a_yaml_1_1_boolean_in_an_entry_is_a_structural_error(tmp_path, typed_quantities, capsys):
    typed_quantities["speed-a"] = typed_quantities["speed-a"].replace(
        "symbol: speed_a", "symbol: y"
    )
    root = _canon(tmp_path, quantities=typed_quantities)
    assert check_canon.cli([str(root)]) == 1
    out = capsys.readouterr().out
    assert "speed-a" in out and "'y'" in out, out


def test_a_when_that_is_not_a_term_is_reported_not_a_crash(tmp_path, typed_quantities):
    front = GOOD_FRONT + "applications:\n  - id: one\n    when: [has_flap]\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("when" in m for m in msgs), msgs


def test_an_unknown_uncertainty_value_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "uncertainty: fuzzy\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("uncertainty" in m and "fuzzy" in m for m in msgs), msgs


def test_an_unknown_uncertainty_value_on_a_quantity_is_reported(tmp_path, typed_quantities):
    typed_quantities["speed-v"] = typed_quantities["speed-v"].replace(
        "type: scalar", "type: scalar\nuncertainty: fuzzy"
    )
    msgs = _messages(_errors(_canon(tmp_path, quantities=typed_quantities)))
    assert any("speed-v uncertainty" in m for m in msgs), msgs


def test_an_escalation_without_a_reason_is_reported(tmp_path, typed_quantities):
    front = GOOD_FRONT + "# ESCALATED:\n"
    msgs = _messages(_errors(_canon(tmp_path, front=front, quantities=typed_quantities)))
    assert any("ESCALATED" in m and "reason" in m for m in msgs), msgs


def test_an_escalation_with_a_reason_is_accepted(tmp_path, typed_quantities):
    front = GOOD_FRONT + "# ESCALATED: b has no decided binding\n"
    assert _findings(_canon(tmp_path, front=front, quantities=typed_quantities)) == []


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


def test_an_escalation_only_opens_the_gaps_it_names(tmp_path, typed_quantities):
    front = """
inputs: {a: speed-a, b: null}
outputs: {v: speed-v}
applications:
  # ESCALATED: c has no decided binding
  - id: one
    bind: {a: speed-a}
"""
    root = _canon(tmp_path, front=front, quantities=typed_quantities, inputs_line=("speed-a",))
    _fix_used_by(root, "speed-b", [])
    errors = _errors(root)
    assert any("'b'" in f.message for f in errors), _messages(errors)


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


def test_cli_exits_non_zero_on_a_structural_error(tmp_path, capsys):
    assert check_canon.cli([str(_canon(tmp_path))]) == 1
    assert "speed-a" in capsys.readouterr().out


def test_cli_exits_zero_on_a_consistent_canon(tmp_path, typed_quantities):
    assert check_canon.cli([str(_canon(tmp_path, quantities=typed_quantities))]) == 0


# --- the real canon --------------------------------------------------------------------------


def test_the_real_canon_has_no_structural_errors():
    errors = [f for f in _findings(REAL_CANON) if not f.open]
    assert errors == [], "\n".join(_messages(errors))


def test_the_real_canon_has_no_yaml_1_1_boolean_keys():
    """Keys and values avoid on/off/yes/no/y/n, which a YAML 1.1 reader turns into booleans."""
    canon = check_canon.load_canon(REAL_CANON)
    for entry in [*canon.formulas.values(), *canon.quantities.values()]:
        assert check_canon.yaml11_booleans(entry.raw_front) == [], entry.slug


def test_yaml_1_1_booleans_are_found_in_keys_and_values():
    raw = "a: {id: x, on: e}\nb: yes\nc: [n, avl]\nd: none\n"
    assert check_canon.yaml11_booleans(raw) == ["on", "yes", "n"]


def test_every_real_entry_carries_the_fields():
    canon = check_canon.load_canon(REAL_CANON)
    assert len(canon.formulas) == 57
    assert len(canon.quantities) == 138
    assert all("inputs" in f.front and "outputs" in f.front for f in canon.formulas.values())
    assert all("type" in q.front for q in canon.quantities.values())


def _fix_used_by(root, slug, used_by):
    """Rewrite a fixture quantity's Used-by line (a quantity no formula reads any more)."""
    path = root / "quantities" / f"{slug}.md"
    head = path.read_text(encoding="utf-8").split("**Used by.**")[0]
    if used_by:
        head += "**Used by.** " + " · ".join(f"[[{u}]]" for u in used_by) + "\n"
    path.write_text(head, encoding="utf-8")
