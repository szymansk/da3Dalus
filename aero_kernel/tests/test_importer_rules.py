"""Importer stage 3, cross-formula rules (ARCHITECTURE ch. 8.6): one mutated mini canon per rule."""

from collections.abc import Mapping
from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, SOURCE_COMMIT, write_canon

GRAVITY = "quantities/gravity.md"
WEIGHT = "quantities/weight.md"
ESTIMATE = "formulas/estimate.md"
WEIGHING = "formulas/weighing.md"
TWICE = "formulas/weigh-twice.md"
OUTER = "formulas/outer.md"
FROM_MASS = "formulas/weight-from-mass.md"


def run(tmp_path: Path, overrides: Mapping[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, dict(overrides or {})), SOURCE_COMMIT)


def mutate(name: str, old: str, new: str) -> dict[str, str | None]:
    """Return an override that replaces ``old`` by ``new`` in one mini-canon file."""
    assert old in MINI_CANON[name], f"{old!r} not in {name}"
    return {name: MINI_CANON[name].replace(old, new, 1)}


def shown(result: ImportResult) -> list[str]:
    """Render the findings of a result."""
    return [str(finding) for finding in result.findings]


def quantity(slug: str, symbol: str, unit: str, role: str) -> str:
    """The text of a scalar quantity entry."""
    shown_unit = f'"{unit}"' if unit == "N" else unit
    return (
        f"---\ncanon: {slug}\nkind: quantity\nsymbol: {symbol}\nunit: {shown_unit}\nrole: {role}\n"
        "status: draft\ntags: []\ntype: scalar\n---\n"
    )


def formula(slug: str, body: str) -> str:
    """The text of a formula entry."""
    return (
        f"---\ncanon: {slug}\nentry: formula\nstatus: draft\nshape: law\noutput: x\n"
        f"source_status: SOURCED\ndimensional_check: OK\ntags: []\ntex: x\n{body}---\n"
    )


def test_the_mini_canon_obeys_every_rule(tmp_path: Path) -> None:
    assert shown(run(tmp_path)) == []


# --- A7: one producer per quantity; every derived or output quantity has one -------------------------


def test_two_formulas_producing_one_quantity(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(ESTIMATE, "outputs: {w: weight-estimate}", "outputs: {w: weight}")
    )
    assert shown(result) == [
        "formulas/weight-from-mass.md: applications[0].produce.w: quantity calc:weight is "
        "already produced by calc:estimate.default (A7)",
        "quantities/weight-estimate.md: role: quantity calc:weight-estimate has role derived "
        "but no formula produces it",
    ]


def test_two_applications_of_one_formula_producing_one_quantity(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(WEIGHING, "produce: {w: weight-flapped}", "produce: {w: weight-weighed}")
    )
    assert shown(result) == [
        "formulas/weighing.md: applications[1].produce.w: quantity calc:weight-weighed is "
        "already produced by calc:weighing.clean (A7)",
        "quantities/weight-flapped.md: role: quantity calc:weight-flapped has role derived "
        "but no formula produces it",
    ]


def test_a_derived_quantity_nobody_produces(tmp_path: Path) -> None:
    result = run(tmp_path, {ESTIMATE: None})
    assert shown(result) == [
        "quantities/weight-estimate.md: role: quantity calc:weight-estimate has role derived "
        "but no formula produces it"
    ]


def test_an_output_quantity_nobody_produces(tmp_path: Path) -> None:
    extra = quantity("lonely", "L", "kg", "output")
    assert shown(run(tmp_path, {"quantities/lonely.md": extra})) == [
        "quantities/lonely.md: role: quantity calc:lonely has role output but no formula produces it"
    ]


# --- A9: roles and names --------------------------------------------------------------------------------


def test_an_input_that_a_formula_produces(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(ESTIMATE, "outputs: {w: weight-estimate}", "outputs: {w: ratio}"))
    assert shown(result) == [
        "formulas/estimate.md: applications[0].produce.w: calc:ratio has role input: the caller "
        "supplies it, no formula may produce it (A9)",
        "quantities/weight-estimate.md: role: quantity calc:weight-estimate has role derived "
        "but no formula produces it",
    ]


def test_a_target_that_a_formula_produces(tmp_path: Path) -> None:
    extra = quantity("speed-target", "V_t", "kg", "target")
    files = {
        "quantities/speed-target.md": extra,
        **mutate(ESTIMATE, "outputs: {w: weight-estimate}", "outputs: {w: speed-target}"),
    }
    assert shown(run(tmp_path, files)) == [
        "formulas/estimate.md: applications[0].produce.w: calc:speed-target has role target: the "
        "caller supplies it, no formula may produce it (A9)",
        "quantities/weight-estimate.md: role: quantity calc:weight-estimate has role derived "
        "but no formula produces it",
    ]


def test_a_target_needs_a_target_segment_in_its_name(tmp_path: Path) -> None:
    extra = quantity("wing-loading", "q", "kg", "target")
    assert shown(run(tmp_path, {"quantities/wing-loading.md": extra})) == [
        "quantities/wing-loading.md: canon: a quantity of role target needs a target segment in "
        "its name (A9)"
    ]


@pytest.mark.parametrize("slug", ["speed-target", "roll-rate-target-cruise", "target-speed"])
def test_a_target_segment_anywhere_in_the_name_is_enough(tmp_path: Path, slug: str) -> None:
    extra = quantity(slug, "V_t", "kg", "target")
    assert shown(run(tmp_path, {f"quantities/{slug}.md": extra})) == []


def test_the_one_named_exception_is_a_target_without_the_segment(tmp_path: Path) -> None:
    extra = quantity("limit-load-factor", "n_lim", "1", "target")
    assert shown(run(tmp_path, {"quantities/limit-load-factor.md": extra})) == []


@pytest.mark.parametrize("role", ["input", "derived"])
def test_a_target_segment_does_not_make_a_quantity_a_target(tmp_path: Path, role: str) -> None:
    """The reverse is no rule: ``range-at-cruise-target`` is an output named after its target."""
    slug = "range-at-cruise-target"
    files: dict[str, str | None] = {f"quantities/{slug}.md": quantity(slug, "R", "kg", role)}
    if role == "derived":
        body = "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {r: range-at-cruise-target}\n"
        files["formulas/range.md"] = formula("range", body)
    assert shown(run(tmp_path, files)) == []


@pytest.mark.parametrize("word", ["requirement", "goal", "req"])
@pytest.mark.parametrize("role", ["input", "target"])
def test_requirements_language_in_an_input_name(tmp_path: Path, word: str, role: str) -> None:
    slug = f"mass-{word}" + ("-target" if role == "target" else "")
    extra = quantity(slug, "Q", "kg", role)
    assert shown(run(tmp_path, {f"quantities/{slug}.md": extra})) == [
        f"quantities/{slug}.md: canon: the name of an input or target must not contain "
        f"['{word}'] (A9)"
    ]


def test_a_longer_word_is_not_a_requirement_segment(tmp_path: Path) -> None:
    extra = quantity("required-mass", "Q", "kg", "input")
    assert shown(run(tmp_path, {"quantities/required-mass.md": extra})) == []


def test_a_derived_quantity_may_be_called_requirement(tmp_path: Path) -> None:
    """Only inputs and targets are the user's; a computed need is called req (A9)."""
    extra = quantity("power-req", "P_req", "kg", "derived")
    body = "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {p: power-req}\n"
    files: dict[str, str | None] = {
        "quantities/power-req.md": extra,
        "formulas/power-need.md": formula("power-need", body),
    }
    assert shown(run(tmp_path, files)) == []


# --- A8: unique symbols ----------------------------------------------------------------------------------


def test_a_symbol_names_one_quantity(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(WEIGHT, "symbol: W\n", "symbol: g\n"))
    assert shown(result) == [
        "quantities/weight.md: symbol: symbol 'g' is already used by calc:gravity (A8)"
    ]


# --- A4: one unit per parameter across applications --------------------------------------------------------


def test_an_output_parameter_with_two_units(tmp_path: Path) -> None:
    flapped = MINI_CANON["quantities/weight-flapped.md"].replace('unit: "N"', "unit: kg")
    assert shown(run(tmp_path, {"quantities/weight-flapped.md": flapped})) == [
        "formulas/weighing.md: applications[1].produce.w: parameter w is calc:weight-flapped (kg) "
        "here but calc:weight-weighed (N) in application clean (A4)"
    ]


def test_an_input_parameter_with_two_units(tmp_path: Path) -> None:
    area = quantity("wing-area", "S", "m^2", "input")
    text = (
        MINI_CANON[WEIGHING]
        .replace("    given: [aircraft-mass]\n", "")
        .replace(
            "bind: {g: {const: 9.81, source: test source}}",
            "bind: {g: {const: 9.81, source: test source}, m: wing-area}",
        )
    )
    assert shown(run(tmp_path, {"quantities/wing-area.md": area, WEIGHING: text})) == [
        "formulas/weighing.md: applications[1].bind.m: parameter m is calc:wing-area (m^2) here "
        "but calc:aircraft-mass (kg) in application clean (A4)"
    ]


def test_a_constant_has_no_unit_to_compare(tmp_path: Path) -> None:
    assert (
        shown(run(tmp_path)) == []
    )  # weighing binds g to a quantity in one application, a constant in the other


# --- the embeds closure --------------------------------------------------------------------------------------


def test_a_formula_that_embeds_itself(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(OUTER, "embeds: [weigh-twice]", "embeds: [outer]"))
    assert shown(result) == [
        "formulas/outer.md: embeds: calc:outer.default is in its own embeds closure (a cycle)"
    ]


def test_every_member_of_a_cycle_is_reported_once(tmp_path: Path) -> None:
    two = MINI_CANON[TWICE].replace("embeds: [weight-from-mass, weighing.clean]", "embeds: [outer]")
    assert shown(run(tmp_path, {TWICE: two})) == [
        "formulas/outer.md: embeds: calc:outer.default is in its own embeds closure (a cycle)",
        "formulas/weigh-twice.md: embeds: calc:weigh-twice.default is in its own embeds closure (a cycle)",
    ]


def test_a_variable_that_nothing_in_the_closure_reads(tmp_path: Path) -> None:
    result = run(tmp_path, mutate(TWICE, "variables: [aircraft-mass]", "variables: [airplane]"))
    assert shown(result) == [
        "formulas/weigh-twice.md: variables[0]: calc:airplane is read by no formula in the embeds closure"
    ]


def test_a_formula_with_worlds_may_not_be_embedded(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(OUTER, "embeds: [weigh-twice]", "embeds: [weigh-twice, estimate]")
    )
    assert shown(result) == [
        "formulas/outer.md: embeds: calc:estimate has uncertainty: interval and may not be embedded"
    ]


def test_an_embedded_input_nobody_supplies(tmp_path: Path) -> None:
    area = quantity("wing-area", "S", "m^2", "input")
    out = quantity("area-result", "A", "m^2", "derived")
    user = formula(
        "area-user",
        "kind: law\ntool: APP\ninputs: {s: wing-area}\noutputs: {a: area-result}\n",
    )
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]",
        "embeds: [weight-from-mass, weighing.clean, area-user]",
    )
    files = {
        "quantities/wing-area.md": area,
        "quantities/area-result.md": out,
        "formulas/area-user.md": user,
        TWICE: twice,
    }
    assert shown(run(tmp_path, files)) == [
        "formulas/outer.md: embeds: input calc:wing-area of embedded calc:area-user.default is neither "
        "a variable of calc:outer, an input of it, nor produced inside the closure",
        "formulas/weigh-twice.md: embeds: input calc:wing-area of embedded calc:area-user.default is "
        "neither a variable of calc:weigh-twice, an input of it, nor produced inside the closure",
    ]


def test_an_embedded_input_that_the_embedder_lists_as_variable_is_supplied(tmp_path: Path) -> None:
    area = quantity("wing-area", "S", "m^2", "input")
    out = quantity("area-result", "A", "m^2", "derived")
    user = formula(
        "area-user",
        "kind: law\ntool: APP\ninputs: {s: wing-area}\noutputs: {a: area-result}\n",
    )
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]\nvariables: [aircraft-mass]",
        "embeds: [weight-from-mass, weighing.clean, area-user]\nvariables: [aircraft-mass, wing-area]",
    )
    outer = MINI_CANON[OUTER].replace(
        "variables: [aircraft-mass]", "variables: [aircraft-mass, wing-area]"
    )
    files = {
        "quantities/wing-area.md": area,
        "quantities/area-result.md": out,
        "formulas/area-user.md": user,
        TWICE: twice,
        OUTER: outer,
    }
    assert shown(run(tmp_path, files)) == []


# --- the defaults rules (enforced by the model types, pinned here through the whole import) -----------------


def defaults(slug: str, value: str, unit: str, *, source: str = "s", regime: str = "r") -> str:
    """A defaults.yaml with one entry."""
    return (
        f"{slug}:\n  value: {value}\n  unit: '{unit}'\n  source: '{source}'\n  regime: '{regime}'\n"
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            defaults("wing-area", "1.0", "m^2"),
            "defaults.yaml: wing-area: default of unknown quantity calc:wing-area",
        ),
        (
            defaults("weight", "1.0", "N"),
            "defaults.yaml: weight: default of calc:weight: role must be input or target, not derived",
        ),
        (
            defaults("airplane", "1.0", "1"),
            "defaults.yaml: airplane: default of calc:airplane: quantity must be a scalar, not airplane",
        ),
        (
            defaults("gravity", "9.8", "kg"),
            "defaults.yaml: gravity: default of calc:gravity: unit kg differs from the quantity's m/s^2",
        ),
        (
            defaults("gravity", "-1", "m/s^2"),
            "defaults.yaml: gravity: default of positive quantity calc:gravity must be > 0",
        ),
    ],
)
def test_every_defaults_rule_through_the_import(tmp_path: Path, text: str, expected: str) -> None:
    assert shown(run(tmp_path, {"defaults.yaml": text})) == [expected]


def test_a_given_quantity_may_not_have_a_default(tmp_path: Path) -> None:
    text = MINI_CANON["defaults.yaml"] + defaults("aircraft-mass", "5", "kg")
    assert shown(run(tmp_path, {"defaults.yaml": text})) == [
        "formulas/weighing.md: applications[1].given[0]: given calc:aircraft-mass must be an input "
        "or target without default"
    ]


@pytest.mark.parametrize("field", ["source", "regime"])
def test_a_default_states_its_source_and_regime(tmp_path: Path, field: str) -> None:
    kwargs = {field: " "}
    text = defaults("gravity", "9.8", "m/s^2", **kwargs)
    result = run(tmp_path, {"defaults.yaml": text})
    assert [(f.file, f.field) for f in result.findings] == [("defaults.yaml", f"gravity.{field}")]


# --- S3 (b) amendment 2: cycles ---------------------------------------------------------------------------------


def two_application_cycle() -> dict[str, str | None]:
    """``weighing`` (two applications) and ``weigh-twice`` embed each other's applications."""
    weighing = MINI_CANON[WEIGHING].replace(
        "postconditions:", "embeds: [weigh-twice]\nvariables: [aircraft-mass]\npostconditions:"
    )
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]",
        "embeds: [weight-from-mass, weighing.clean, weighing.flapped]",
    )
    return {WEIGHING: weighing, TWICE: twice}


def test_a_cycle_is_reported_once_per_member_formula_not_once_per_application(
    tmp_path: Path,
) -> None:
    findings = shown(run(tmp_path, two_application_cycle()))
    assert findings == [
        "formulas/weigh-twice.md: embeds: calc:weigh-twice.default is in its own embeds closure (a cycle)",
        "formulas/weighing.md: embeds: calc:weighing.clean is in its own embeds closure (a cycle)",
    ]


def test_one_cycle_does_not_hide_the_embeds_faults_of_unrelated_formulas(tmp_path: Path) -> None:
    other = formula(
        "other",
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {w: weight-other}\n"
        "embeds: [weight-from-mass]\nvariables: [airplane]\n",
    )
    files = {
        **two_application_cycle(),
        "formulas/other.md": other,
        "quantities/weight-other.md": quantity("weight-other", "W_x", "N", "derived"),
    }
    assert (
        "formulas/other.md: variables[0]: calc:airplane is read by no formula in the embeds closure"
        in shown(run(tmp_path, files))
    )


def test_a_formula_embedding_a_cycle_gets_no_derived_embeds_findings(tmp_path: Path) -> None:
    """``outer`` embeds the cycle: its own closure is not defined, only the cycle is reported."""
    outer = MINI_CANON[OUTER].replace("variables: [aircraft-mass]", "variables: [airplane]")
    findings = shown(run(tmp_path, {**two_application_cycle(), OUTER: outer}))
    assert not any(line.startswith("formulas/outer.md") for line in findings), findings
