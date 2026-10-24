"""Importer stage 2 (normalise): one test per finding class, and the normalised shape."""

import re
from pathlib import Path
from typing import get_args

import pytest
from aero_kernel.canon.model import Tool
from aero_kernel.importer.normalise import DERIVED_COST
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, write_canon

GRAVITY = "quantities/gravity.md"
WEIGHT = "quantities/weight.md"
WEIGHING = "formulas/weighing.md"
TWICE = "formulas/weigh-twice.md"
FROM_MASS = "formulas/weight-from-mass.md"


def run(tmp_path: Path, overrides: dict[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, overrides))


def mutate(name: str, old: str, new: str) -> dict[str, str | None]:
    """Return an override that replaces ``old`` by ``new`` in one mini-canon file."""
    assert old in MINI_CANON[name], f"{old!r} not in {name}"
    return {name: MINI_CANON[name].replace(old, new, 1)}


STAGE_2_CASES = {
    "unit is a boolean": (
        mutate(GRAVITY, "unit: m/s^2", "unit: !!bool true"),
        GRAVITY,
        "unit",
        "got True",
    ),
    "constant with an empty source": (
        mutate(WEIGHING, "source: test source", "source: ''"),
        WEIGHING,
        "applications[1].bind.g.source",
        "at least 1 character",
    ),
    "constant with an extra key": (
        mutate(WEIGHING, "source: test source}", "source: test source, unit: kg}"),
        WEIGHING,
        "applications[1].bind.g.unit",
        "Extra inputs",
    ),
    "bind is no mapping": (
        mutate(WEIGHING, "bind: {g: {const: 9.81, source: test source}}", "bind: [g]"),
        WEIGHING,
        "applications[1].bind",
        "valid dictionary",
    ),
    "application is no mapping": (
        mutate(WEIGHING, "applications:\n", "applications:\n  - plain\n"),
        WEIGHING,
        "applications[0]",
        "must be a mapping",
    ),
    "application id is no identifier": (
        mutate(WEIGHING, "id: flapped", "id: Flapped"),
        WEIGHING,
        "applications[1].id",
        "should match pattern",
    ),
    "empty given": (
        mutate(WEIGHING, "given: [aircraft-mass]", "given: []"),
        WEIGHING,
        "applications[1].given",
        "must not be empty",
    ),
    "check is no mapping": (
        mutate(FROM_MASS, "preconditions:\n  - {", "preconditions:\n  - plain\n  - {"),
        FROM_MASS,
        "preconditions[0]",
        "valid dictionary",
    ),
    "check id is no identifier": (
        mutate(FROM_MASS, "{id: m_checked,", "{id: M-Checked,"),
        FROM_MASS,
        "preconditions[0].id",
        "should match pattern",
    ),
    "check applications empty": (
        mutate(WEIGHING, "applications: [clean]}", "applications: []}"),
        WEIGHING,
        "postconditions[0].applications",
        "must not be empty",
    ),
    "check applications not ids": (
        mutate(WEIGHING, "applications: [clean]}", "applications: [Clean]}"),
        WEIGHING,
        "postconditions[0].applications[0]",
        "should match pattern",
    ),
    "optional is no parameter name": (
        mutate(TWICE, "variables:", "optional: [Mass]\nvariables:"),
        TWICE,
        "optional[0]",
        "should match pattern",
    ),
    "unknown unit": (mutate(GRAVITY, "unit: m/s^2", "unit: furlong"), GRAVITY, "unit", "furlong"),
    "unit is no string or 1": (
        mutate(GRAVITY, "unit: m/s^2", "unit: [m]"),
        GRAVITY,
        "unit",
        "(got ['m'])",
    ),
    "unknown role": (mutate(GRAVITY, "role: input", "role: boss"), GRAVITY, "role", "boss"),
    "unknown type": (mutate(GRAVITY, "type: scalar", "type: blob"), GRAVITY, "type", "blob"),
    "unknown quantity uncertainty": (
        mutate(WEIGHT, "type: scalar\n", "type: scalar\nuncertainty: fuzzy\n"),
        WEIGHT,
        "uncertainty",
        "fuzzy",
    ),
    "positive false": (
        mutate(GRAVITY, "positive: true", "positive: false"),
        GRAVITY,
        "positive",
        "Input should be True",
    ),
    "positive on a derived quantity": (
        mutate(WEIGHT, "type: scalar\n", "type: scalar\npositive: true\n"),
        WEIGHT,
        "entry",
        "input or target",
    ),
    "unknown kind": (mutate(WEIGHING, "kind: procedure", "kind: rite"), WEIGHING, "kind", "rite"),
    "unknown tool": (mutate(WEIGHING, "tool: AB", "tool: XYZ"), WEIGHING, "tool", "XYZ"),
    "unknown cost": (
        mutate(WEIGHING, "tool: AB\n", "tool: AB\ncost: slow\n"),
        WEIGHING,
        "cost",
        "slow",
    ),
    "unknown formula uncertainty": (
        mutate(WEIGHING, "tool: AB\n", "tool: AB\nuncertainty: fuzzy\n"),
        WEIGHING,
        "uncertainty",
        "fuzzy",
    ),
    "input slug is no string": (
        mutate(WEIGHING, "inputs: {m: aircraft-mass,", "inputs: {m: 5,"),
        WEIGHING,
        "inputs.m",
        "valid string",
    ),
    "parameter is no snake_case name": (
        mutate(WEIGHING, "inputs: {m: aircraft-mass,", "inputs: {Mass: aircraft-mass,"),
        WEIGHING,
        "inputs.Mass.[key]",
        "should match pattern",
    ),
    "unknown when": (
        mutate(WEIGHING, "when: has_aileron", "when: has_wings"),
        WEIGHING,
        "applications[1].when",
        "has_wings",
    ),
    "unknown on_violation": (
        mutate(FROM_MASS, "on_violation: warning", "on_violation: panic"),
        FROM_MASS,
        "preconditions[0].on_violation",
        "panic",
    ),
    "check without id": (
        mutate(FROM_MASS, "{id: m_checked, parameter: m,", "{parameter: m,"),
        FROM_MASS,
        "preconditions[0].id",
        "Field required",
    ),
    "unknown check field": (
        mutate(FROM_MASS, "{id: m_checked, parameter: m,", "{id: m_checked, parameter: m, x: 1,"),
        FROM_MASS,
        "preconditions[0].x",
        "Extra inputs",
    ),
    "bind of an unknown parameter": (
        mutate(WEIGHING, "bind: {g: {const", "bind: {zz: {const"),
        WEIGHING,
        "entry",
        "application `flapped`: parameter `zz` is not an input of the formula",
    ),
    "produce of an unknown parameter": (
        mutate(WEIGHING, "produce: {w: weight-flapped}", "produce: {zz: weight-flapped}"),
        WEIGHING,
        "entry",
        "application `flapped`: parameter `zz` is not an output of the formula",
    ),
    "constant without a source": (
        mutate(WEIGHING, "{const: 9.81, source: test source}", "{const: 9.81}"),
        WEIGHING,
        "applications[1].bind.g.source",
        "Field required",
    ),
    "boolean constant": (
        mutate(WEIGHING, "const: 9.81", "const: !!bool true"),
        WEIGHING,
        "applications[1].bind.g.const",
        "valid number",
    ),
    "bind value is a number": (
        mutate(WEIGHING, "bind: {g: {const: 9.81, source: test source}}", "bind: {g: 3}"),
        WEIGHING,
        "applications[1].bind.g",
        "valid string",
    ),
    "application without an id": (
        mutate(WEIGHING, "  - id: flapped\n    bind", "  - bind"),
        WEIGHING,
        "applications[1].id",
        "missing, but required",
    ),
    "unknown application field": (
        mutate(WEIGHING, "    when: has_aileron\n", "    when: has_aileron\n    colour: red\n"),
        WEIGHING,
        "applications[1].colour",
        "Extra inputs",
    ),
    "output left unproduced": (
        mutate(WEIGHING, "  - id: clean\n    produce: {w: weight-weighed}\n", "  - id: clean\n"),
        WEIGHING,
        "entry",
        "application `clean`: output parameter `w` is not produced",
    ),
    "empty applications list": (
        {
            WEIGHING: re.sub(
                r"applications:\n(?:  .*\n)+", "applications: []\n", MINI_CANON[WEIGHING]
            )
        },
        WEIGHING,
        "applications",
        "must not be empty; omit the field for the implicit application",
    ),
    "second application omits a binding": (
        mutate(
            WEIGHING,
            "inputs: {m: aircraft-mass, g: gravity}\noutputs: {w: null}\napplications:\n  - id: clean\n",
            "inputs: {m: null, g: gravity}\noutputs: {w: null}\napplications:\n  - id: clean\n    bind: {m: aircraft-mass}\n",
        ),
        WEIGHING,
        "entry",
        "application `flapped`: input parameter `m` is not bound",
    ),
    "unbound input": (
        mutate(WEIGHING, "inputs: {m: aircraft-mass, g: gravity}", "inputs: {m: null, g: gravity}"),
        WEIGHING,
        "entry",
        "application `clean`: input parameter `m` is not bound",
    ),
    "unbound input of an implicit application": (
        mutate(
            FROM_MASS, "inputs: {m: aircraft-mass, g: gravity}", "inputs: {m: null, g: gravity}"
        ),
        FROM_MASS,
        "entry",
        "application `default`: input parameter `m` is not bound",
    ),
    "bare embed of a multi-application formula": (
        mutate(TWICE, "weighing.clean", "weighing"),
        TWICE,
        "embeds",
        "several applications",
    ),
    "embed of an unknown formula": (
        mutate(TWICE, "weighing.clean", "nowhere.clean"),
        TWICE,
        "embeds",
        "nowhere",
    ),
    "embed of an unknown application": (
        mutate(TWICE, "weighing.clean", "weighing.zzz"),
        TWICE,
        "embeds",
        "zzz",
    ),
    "embed with a malformed item": (
        mutate(TWICE, "weighing.clean", "Weighing.a.b"),
        TWICE,
        "embeds",
        "Weighing.a.b",
    ),
    "default with an unknown unit": (
        {
            "defaults.yaml": "gravity:\n  value: 9.8\n  unit: furlong\n  basis: sourced\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "gravity.unit",
        "furlong",
    ),
    "reference to an unknown quantity": (
        mutate(FROM_MASS, "outputs: {w: weight}", "outputs: {w: nothing}"),
        FROM_MASS,
        "outputs.w",
        "unknown quantity calc:nothing",
    ),
    "default of an unknown quantity": (
        {
            "defaults.yaml": "nothing:\n  value: 9.8\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n",
        },
        "defaults.yaml",
        "nothing",
        "unknown quantity",
    ),
}


@pytest.mark.parametrize(
    ("overrides", "file", "field", "text"), STAGE_2_CASES.values(), ids=STAGE_2_CASES.keys()
)
def test_stage_2_finding(
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


def test_stage_2_runs_only_when_stage_1_is_clean(tmp_path: Path) -> None:
    overrides = {
        **mutate(GRAVITY, "symbol: g\n", ""),
        **mutate(WEIGHT, 'unit: "N"', "unit: furlong"),
    }
    assert {finding.file for finding in run(tmp_path, overrides).findings} == {GRAVITY}


# --- the normalised shape ---------------------------------------------------------------------


def imported(tmp_path: Path) -> ImportResult:
    """Import the unmodified mini canon, which must succeed."""
    result = run(tmp_path)
    assert result.model is not None, [str(finding) for finding in result.findings]
    return result


def test_slugs_become_dict_keys_and_the_counts_match(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    content = model.namespaces["calc"]
    assert set(content.formulas) == {
        "weight-from-mass",
        "weighing",
        "estimate",
        "weigh-twice",
        "outer",
    }
    assert len(content.quantities) == 10


def test_references_are_qualified_and_the_implicit_application_is_written_out(
    tmp_path: Path,
) -> None:
    model = imported(tmp_path).model
    assert model is not None
    formula = model.formula("weight-from-mass")
    assert formula is not None
    assert formula.inputs == {"m": "calc:aircraft-mass", "g": "calc:gravity"}
    (application,) = formula.applications
    assert application.id == "default"
    assert application.bind == {"m": "calc:aircraft-mass", "g": "calc:gravity"}
    assert application.produce == {"w": "calc:weight"}
    assert application.when is None
    assert application.given is None
    assert formula.preconditions[0].applications is None


def test_explicit_applications_are_merged_with_the_defaults(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    formula = model.formula("weighing")
    assert formula is not None
    assert formula.outputs == {"w": None}
    clean, flapped = formula.applications
    assert clean.bind == {"m": "calc:aircraft-mass", "g": "calc:gravity"}
    assert clean.produce == {"w": "calc:weight-weighed"}
    assert flapped.bind["m"] == "calc:aircraft-mass"
    bound = flapped.bind["g"]
    assert not isinstance(bound, str)
    assert (bound.const, bound.source) == (9.81, "test source")
    assert flapped.when == "has_aileron"
    assert flapped.given == ("calc:aircraft-mass",)
    assert formula.postconditions[0].applications == ("clean",)


def test_cost_is_declared_or_derived_from_the_tool(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    costs = {slug: formula.cost for slug, formula in model.namespaces["calc"].formulas.items()}
    assert costs == {
        "weight-from-mass": "instant",  # APP
        "weighing": "seconds",  # AB
        "estimate": "seconds",  # AVL
        "weigh-twice": "instant",  # APP
        "outer": "minutes",  # declared, although OPT would derive seconds
    }


def test_embeds_are_normalised_and_the_closure_is_transitive(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    twice = model.formula("weigh-twice")
    outer = model.formula("outer")
    assert twice is not None
    assert outer is not None
    assert twice.embeds == ("calc:weight-from-mass.default", "calc:weighing.clean")
    assert twice.embeds_closure == tuple(sorted(twice.embeds))
    assert outer.embeds == ("calc:weigh-twice.default",)
    assert outer.embeds_closure == (
        "calc:weigh-twice.default",
        "calc:weighing.clean",
        "calc:weight-from-mass.default",
    )
    assert outer.variables == ("calc:aircraft-mass",)
    assert outer.optional == ("g",)


def test_worlds_and_dimensionless_units(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    estimate = model.formula("estimate")
    assert estimate is not None
    assert (estimate.uncertainty, estimate.worlds) == ("interval", ("simple", "detailed"))
    airplane = model.quantity("airplane")
    ratio = model.quantity("ratio")
    assert airplane is not None
    assert ratio is not None
    assert (airplane.unit, ratio.unit) == ("1", "1")  # "—" and 1 both fold into "1"


def test_defaults_become_the_namespace_table(tmp_path: Path) -> None:
    model = imported(tmp_path).model
    assert model is not None
    default = model.namespaces["calc"].defaults["gravity"]
    assert (default.value, default.unit) == (9.80665, "m/s^2")
    assert (default.source, default.regime) == ("standard gravity", "regime-independent")


def test_integer_numbers_become_floats(tmp_path: Path) -> None:
    overrides = {
        **mutate(WEIGHING, "const: 9.81", "const: 10"),
        "defaults.yaml": "gravity:\n  value: 10\n  unit: m/s^2\n  basis: sourced\n  source: s\n  regime: r\n",
    }
    result = run(tmp_path, overrides)
    assert result.model is not None
    assert result.model.namespaces["calc"].defaults["gravity"].value == 10.0
    assert '"const": 10.0' in (result.model_json or "")


@pytest.mark.parametrize(
    ("tool", "cost"),
    [
        ("APP", "instant"),
        ("ATM", "instant"),
        ("GEO", "instant"),
        ("KAT", "instant"),
        ("APC", "instant"),
        ("AB", "seconds"),
        ("AVL", "seconds"),
        ("OPT", "seconds"),
    ],
)
def test_cost_is_derived_from_every_tool_as_in_8_7(tmp_path: Path, tool: str, cost: str) -> None:
    result = run(tmp_path, mutate(FROM_MASS, "tool: APP", f"tool: {tool}"))
    assert result.model is not None
    formula = result.model.formula("weight-from-mass")
    assert formula is not None
    assert formula.cost == cost


def test_the_cost_table_covers_exactly_the_tools_of_the_model() -> None:
    assert set(DERIVED_COST) == set(get_args(Tool))


def test_a_declared_cost_wins_over_the_derived_one(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(FROM_MASS, "tool: APP\n", "tool: APP\ncost: seconds\n"))
    assert result.model is not None
    formula = result.model.formula("weight-from-mass")
    assert formula is not None
    assert formula.cost == "seconds"


def test_an_embed_listed_twice_is_a_finding(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(TWICE, "weight-from-mass,", "weight-from-mass, weight-from-mass,")
    )
    assert any(
        f.file == TWICE and f.field == "embeds" and "listed twice" in f.message
        for f in result.findings
    )


def test_a_bare_embed_of_a_single_explicit_application_names_that_application(
    tmp_path: Path,
) -> None:
    """T4: the only application's id, whatever it is called."""
    only = MINI_CANON[FROM_MASS].replace(
        "preconditions:",
        "applications:\n  - id: only\npreconditions:",
    )
    result = run(tmp_path, {FROM_MASS: only})
    assert result.model is not None
    twice = result.model.formula("weigh-twice")
    assert twice is not None
    assert "calc:weight-from-mass.only" in twice.embeds


def test_a_bare_embed_of_a_single_application_formula_names_its_application(
    tmp_path: Path,
) -> None:
    result = run(tmp_path, mutate(TWICE, "weight-from-mass,", "weight-from-mass.default,"))
    assert result.model is not None
    assert result.model.formula("weigh-twice") is not None


def test_an_embedder_of_a_formula_with_no_applications_adds_no_cascade(tmp_path: Path) -> None:
    empty = re.sub(r"applications:\n(?:  .*\n)+", "applications: []\n", MINI_CANON[WEIGHING])
    result = run(tmp_path, {WEIGHING: empty})
    assert [(f.file, f.field) for f in result.findings] == [(WEIGHING, "applications")]


def test_an_embedder_of_a_formula_with_an_unreadable_application_adds_no_cascade(
    tmp_path: Path,
) -> None:
    broken = mutate(WEIGHING, "  - id: clean\n    produce", "  - produce")
    result = run(tmp_path, broken)
    assert [(f.file, f.field) for f in result.findings] == [(WEIGHING, "applications[0].id")]


def test_an_embedder_of_a_formula_with_another_fault_adds_no_cascade(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(WEIGHING, "kind: procedure", "kind: rite"))
    assert [(f.file, f.field) for f in result.findings] == [(WEIGHING, "kind")]
