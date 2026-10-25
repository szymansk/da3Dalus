"""Importer stage 3, cross-formula rules (ARCHITECTURE ch. 8.6): one mutated mini canon per rule."""

from collections.abc import Mapping
from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, write_canon

GRAVITY = "quantities/gravity.md"
WEIGHT = "quantities/weight.md"
ESTIMATE = "formulas/estimate.md"
WEIGHING = "formulas/weighing.md"
TWICE = "formulas/weigh-twice.md"
OUTER = "formulas/outer.md"
FROM_MASS = "formulas/weight-from-mass.md"


def run(tmp_path: Path, overrides: Mapping[str, str | None] | None = None) -> ImportResult:
    """Import the mini canon with ``overrides`` applied."""
    return import_canon(write_canon(tmp_path, dict(overrides or {})))


def mutate(name: str, old: str, new: str) -> dict[str, str | None]:
    """Return an override that replaces ``old`` by ``new`` in one mini-canon file."""
    assert old in MINI_CANON[name], f"{old!r} not in {name}"
    return {name: MINI_CANON[name].replace(old, new, 1)}


def shown(result: ImportResult) -> list[str]:
    """Render the findings of a result."""
    return [str(finding) for finding in result.findings]


def quantity(slug: str, symbol: str, unit: str, role: str, type_: str = "scalar") -> str:
    """The text of a quantity entry (a scalar unless ``type_`` says otherwise)."""
    shown_unit = f'"{unit}"' if unit == "N" else unit
    return (
        f"---\ncanon: {slug}\nkind: quantity\nsymbol: {symbol}\nunit: {shown_unit}\nrole: {role}\n"
        f"tags: []\ntype: {type_}\n---\n"
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
        "already produced by calc:estimate.default (A7): only a per_control_surface quantity may be produced by several applications, and only of one formula, so that the merged value has one tool and one unit (ADR 0022)",
        "quantities/weight-estimate.md: role: quantity calc:weight-estimate has role derived "
        "but no formula produces it",
    ]


def test_two_applications_of_one_formula_producing_one_quantity(tmp_path: Path) -> None:
    result = run(
        tmp_path, mutate(WEIGHING, "produce: {w: weight-flapped}", "produce: {w: weight-weighed}")
    )
    assert shown(result) == [
        "formulas/weighing.md: applications[1].produce.w: quantity calc:weight-weighed is "
        "already produced by calc:weighing.clean (A7): only a per_control_surface quantity may be produced by several applications, and only of one formula, so that the merged value has one tool and one unit (ADR 0022)",
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
    return f"{slug}:\n  value: {value}\n  unit: '{unit}'\n  basis: sourced\n  source: '{source}'\n  regime: '{regime}'\n"


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


def test_a_default_states_its_basis(tmp_path: Path) -> None:
    text = defaults("gravity", "9.8", "m/s^2").replace("basis: sourced", "basis: guessed")
    result = run(tmp_path, {"defaults.yaml": text})
    assert [(f.file, f.field) for f in result.findings] == [("defaults.yaml", "gravity.basis")]


def test_a_default_without_a_basis_is_a_finding(tmp_path: Path) -> None:
    text = defaults("gravity", "9.8", "m/s^2").replace("  basis: sourced\n", "")
    result = run(tmp_path, {"defaults.yaml": text})
    assert [(f.file, f.field) for f in result.findings] == [("defaults.yaml", "gravity.basis")]


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


# --- S3 (b) amendment 3: boundaries the mutation run found ------------------------------------------------------


@pytest.mark.parametrize("slug", ["targeting-speed", "retarget-x", "targets-mass"])
def test_a_substring_is_not_a_target_segment(tmp_path: Path, slug: str) -> None:
    extra = quantity(slug, "V_t", "kg", "target")
    assert shown(run(tmp_path, {f"quantities/{slug}.md": extra})) == [
        f"quantities/{slug}.md: canon: a quantity of role target needs a target segment in its "
        "name (A9)"
    ]


def test_a_cycle_through_the_second_application_is_found(tmp_path: Path) -> None:
    weighing = MINI_CANON[WEIGHING].replace(
        "postconditions:", "embeds: [weigh-twice]\nvariables: [aircraft-mass]\npostconditions:"
    )
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]", "embeds: [weight-from-mass, weighing.flapped]"
    )
    assert shown(run(tmp_path, {WEIGHING: weighing, TWICE: twice})) == [
        "formulas/weigh-twice.md: embeds: calc:weigh-twice.default is in its own embeds closure (a cycle)",
        "formulas/weighing.md: embeds: calc:weighing.flapped is in its own embeds closure (a cycle)",
    ]


def test_a_formula_on_a_cycle_gets_no_embeds_findings_of_its_own(tmp_path: Path) -> None:
    files = two_application_cycle()
    files[TWICE] = (files[TWICE] or "").replace(
        "variables: [aircraft-mass]", "variables: [airplane]"
    )
    assert shown(run(tmp_path, files)) == [
        "formulas/weigh-twice.md: embeds: calc:weigh-twice.default is in its own embeds closure (a cycle)",
        "formulas/weighing.md: embeds: calc:weighing.clean is in its own embeds closure (a cycle)",
    ]


def test_the_second_unread_variable_is_variables_1(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        mutate(TWICE, "variables: [aircraft-mass]", "variables: [aircraft-mass, airplane]"),
    )
    assert shown(result) == [
        "formulas/weigh-twice.md: variables[1]: calc:airplane is read by no formula in the embeds closure"
    ]


def test_an_interval_formula_embedded_transitively_is_found(tmp_path: Path) -> None:
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]",
        "embeds: [weight-from-mass, weighing.clean, estimate]",
    )
    message = "embeds: calc:estimate has uncertainty: interval and may not be embedded"
    assert shown(run(tmp_path, {TWICE: twice})) == [
        f"formulas/outer.md: {message}",
        f"formulas/weigh-twice.md: {message}",
    ]


def with_area_user(
    extra_inputs: str, extra_quantities: dict[str, str | None]
) -> dict[str, str | None]:
    """A formula ``area-user`` reading ``wing-area`` (and what ``extra_inputs`` adds), embedded by weigh-twice."""
    user = formula(
        "area-user",
        f"kind: law\ntool: APP\ninputs: {{s: wing-area{extra_inputs}}}\noutputs: {{a: area-result}}\n",
    )
    twice = MINI_CANON[TWICE].replace(
        "embeds: [weight-from-mass, weighing.clean]",
        "embeds: [weight-from-mass, weighing.clean, area-user]",
    )
    return {
        "quantities/wing-area.md": quantity("wing-area", "S", "m^2", "input"),
        "quantities/area-result.md": quantity("area-result", "A", "m^2", "derived"),
        "formulas/area-user.md": user,
        TWICE: twice,
        **extra_quantities,
    }


def test_several_missing_embedded_inputs_are_all_reported_in_order(tmp_path: Path) -> None:
    files = with_area_user(
        ", t: wing-span", {"quantities/wing-span.md": quantity("wing-span", "b", "m", "input")}
    )
    sentence = "of embedded calc:area-user.default is neither a variable of calc:{who}, an input of it, nor produced inside the closure"
    assert shown(run(tmp_path, files)) == [
        f"formulas/outer.md: embeds: input calc:wing-area {sentence.format(who='outer')}",
        f"formulas/outer.md: embeds: input calc:wing-span {sentence.format(who='outer')}",
        f"formulas/weigh-twice.md: embeds: input calc:wing-area {sentence.format(who='weigh-twice')}",
        f"formulas/weigh-twice.md: embeds: input calc:wing-span {sentence.format(who='weigh-twice')}",
    ]


def test_the_second_application_of_the_embedder_may_bind_the_embedded_input(tmp_path: Path) -> None:
    host = formula(
        "host",
        "kind: law\ntool: APP\ninputs: {s: null, t: wing-span}\noutputs: {a: null}\n"
        "applications:\n  - id: first\n    bind: {s: ref-area}\n    produce: {a: host-result}\n"
        "  - id: second\n    bind: {s: wing-area}\n    produce: {a: host-result-b}\n"
        "embeds: [area-user]\nvariables: [wing-span]\n",
    )
    files = with_area_user(
        ", t: wing-span",
        {
            "quantities/wing-span.md": quantity("wing-span", "b", "m", "input"),
            "quantities/ref-area.md": quantity("ref-area", "S_r", "m^2", "input"),
            "quantities/host-result.md": quantity("host-result", "H", "m^2", "derived"),
            "quantities/host-result-b.md": quantity("host-result-b", "H_b", "m^2", "derived"),
            "formulas/host.md": host,
        },
    )
    files[TWICE] = MINI_CANON[TWICE]  # only host embeds area-user here
    files[OUTER] = MINI_CANON[OUTER]
    assert shown(run(tmp_path, files)) == []


def test_two_applications_of_one_interval_formula_give_one_finding(tmp_path: Path) -> None:
    """The final de-duplication is reachable: both embeds produce the identical message."""
    estimate = MINI_CANON[ESTIMATE].replace(
        "outputs: {w: weight-estimate}\n",
        "outputs: {w: null}\napplications:\n  - id: a\n    produce: {w: weight-estimate}\n"
        "  - id: b\n    produce: {w: weight-estimate-b}\n",
    )
    outer = MINI_CANON[OUTER].replace(
        "embeds: [weigh-twice]", "embeds: [weigh-twice, estimate.a, estimate.b]"
    )
    files = {
        ESTIMATE: estimate,
        OUTER: outer,
        "quantities/weight-estimate-b.md": quantity("weight-estimate-b", "W_eb", "N", "derived"),
    }
    assert shown(run(tmp_path, files)) == [
        "formulas/outer.md: embeds: calc:estimate has uncertainty: interval and may not be embedded"
    ]


def test_findings_of_two_rules_in_one_file_are_ordered_by_field(tmp_path: Path) -> None:
    """A7 (produce) is found before A4 (bind), but the output is sorted by field."""
    area = quantity("wing-area", "S", "m^2", "input")
    text = (
        MINI_CANON[WEIGHING]
        .replace("    given: [aircraft-mass]\n", "")
        .replace("produce: {w: weight-flapped}", "produce: {w: weight-weighed}")
        .replace(
            "bind: {g: {const: 9.81, source: test source}}",
            "bind: {g: {const: 9.81, source: test source}, m: wing-area}",
        )
    )
    assert shown(run(tmp_path, {"quantities/wing-area.md": area, WEIGHING: text})) == [
        "formulas/weighing.md: applications[1].bind.m: parameter m is calc:wing-area (m^2) here but "
        "calc:aircraft-mass (kg) in application clean (A4)",
        "formulas/weighing.md: applications[1].produce.w: quantity calc:weight-weighed is already "
        "produced by calc:weighing.clean (A7): only a per_control_surface quantity may be produced by "
        "several applications, and only of one formula, so that the merged value has one tool and "
        "one unit (ADR 0022)",
        "quantities/weight-flapped.md: role: quantity calc:weight-flapped has role derived but no "
        "formula produces it",
    ]


# --- S3 (b) amendment 5 ------------------------------------------------------------------------------------------


def test_a_formula_that_reaches_a_cycle_only_through_a_chain_gets_no_embeds_finding(
    tmp_path: Path,
) -> None:
    """top -> mid -> (weighing <-> weigh-twice): the skip is by closure, not by direct embed."""
    mid = formula(
        "mid",
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {w: weight-mid}\n"
        "embeds: [weigh-twice]\nvariables: [aircraft-mass]\n",
    )
    top = formula(
        "top",
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {w: weight-top}\n"
        "embeds: [mid]\nvariables: [airplane]\n",
    )
    files = {
        **two_application_cycle(),
        "formulas/mid.md": mid,
        "formulas/top.md": top,
        "quantities/weight-mid.md": quantity("weight-mid", "W_m", "N", "derived"),
        "quantities/weight-top.md": quantity("weight-top", "W_t", "N", "derived"),
    }
    findings = shown(run(tmp_path, files))
    assert not any(line.startswith(("formulas/top.md", "formulas/mid.md")) for line in findings), (
        findings
    )
    assert len(findings) == 2  # only the two members of the cycle


def test_findings_in_one_file_come_out_by_field_and_then_by_message(tmp_path: Path) -> None:
    files = with_area_user(
        ", t: wing-span", {"quantities/wing-span.md": quantity("wing-span", "b", "m", "input")}
    )
    files[TWICE] = (files[TWICE] or "").replace(
        "variables: [aircraft-mass]", "variables: [airplane]"
    )
    sentence = "of embedded calc:area-user.default is neither a variable of calc:weigh-twice, an input of it, nor produced inside the closure"
    twice = [
        line for line in shown(run(tmp_path, files)) if line.startswith("formulas/weigh-twice.md")
    ]
    assert twice == [
        f"formulas/weigh-twice.md: embeds: input calc:wing-area {sentence}",
        f"formulas/weigh-twice.md: embeds: input calc:wing-span {sentence}",
        "formulas/weigh-twice.md: variables[0]: calc:airplane is read by no formula in the embeds closure",
    ]


def test_findings_with_the_same_file_and_field_are_ordered_by_message_whatever_the_rule_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The tie-break is the message. The input is a list in REVERSE message order, so the result
    cannot come out right by insertion order or by the hash seed of a set."""
    from aero_kernel.canon.model import Namespace
    from aero_kernel.importer import rules
    from aero_kernel.importer.findings import Finding

    model = import_canon(write_canon(tmp_path)).model
    assert model is not None
    reverse = [
        Finding(file="formulas/outer.md", field="embeds", message=message)
        for message in ("zeta", "mu", "alpha")
    ]

    def reversed_symbols(_: Namespace) -> list[Finding]:
        return reverse

    monkeypatch.setattr(rules, "_symbols", reversed_symbols)
    assert [finding.message for finding in rules.check_model(model)] == ["alpha", "mu", "zeta"]


# --- per_control_surface: one quantity, several applications of one formula --------------------------------------

HINGE = "quantities/hinge.md"
HINGES = "formulas/hinges.md"
PER_SURFACE_MESSAGE = (
    "(A7): only a per_control_surface quantity may be produced by several applications, and only of "
    "one formula, so that the merged value has one tool and one unit (ADR 0022)"
)


def hinge_files(*, type_: str = "per_control_surface") -> dict[str, str | None]:
    """A formula ``hinges`` with two applications that both produce the quantity ``hinge``."""
    body = (
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {h: hinge}\n"
        "applications:\n  - id: elevator\n  - id: rudder\n"
    )
    return {
        HINGE: quantity("hinge", "M_h", "N*m", "output", type_),
        HINGES: formula("hinges", body),
    }


def test_several_applications_of_one_formula_may_produce_a_per_control_surface_quantity(
    tmp_path: Path,
) -> None:
    assert shown(run(tmp_path, hinge_files())) == []


def test_several_applications_producing_a_scalar_are_still_a_finding(tmp_path: Path) -> None:
    assert shown(run(tmp_path, hinge_files(type_="scalar"))) == [
        "formulas/hinges.md: applications[1].produce.h: quantity calc:hinge is already produced by "
        f"calc:hinges.elevator {PER_SURFACE_MESSAGE}"
    ]


def test_two_formulas_producing_a_per_control_surface_quantity_are_a_finding(
    tmp_path: Path,
) -> None:
    other = formula(
        "hinges-two", "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {h: hinge}\n"
    )
    files = {**hinge_files(), "formulas/hinges-two.md": other}
    assert shown(run(tmp_path, files)) == [
        "formulas/hinges-two.md: applications[0].produce.h: quantity calc:hinge is already produced "
        f"by calc:hinges.elevator {PER_SURFACE_MESSAGE}"
    ]


def test_an_application_that_binds_a_per_control_surface_quantity_is_a_finding(
    tmp_path: Path,
) -> None:
    reader = formula(
        "reader",
        "kind: law\ntool: APP\ninputs: {h: hinge}\noutputs: {w: weight-read}\n",
    )
    files = {
        **hinge_files(),
        "formulas/reader.md": reader,
        "quantities/weight-read.md": quantity("weight-read", "W_r", "N", "derived"),
    }
    assert shown(run(tmp_path, files)) == [
        "formulas/reader.md: applications[0].bind.h: calc:hinge is a per_control_surface quantity: "
        "no application may read it (it is an output only; nothing computes from it)"
    ]


def test_an_embedded_application_that_binds_a_per_control_surface_quantity_is_a_finding(
    tmp_path: Path,
) -> None:
    reader = formula(
        "reader",
        "kind: law\ntool: APP\ninputs: {h: hinge}\noutputs: {w: weight-read}\n",
    )
    host = formula(
        "host",
        "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {w: weight-host}\n"
        "embeds: [reader]\nvariables: [hinge]\n",
    )
    files = {
        **hinge_files(),
        "formulas/reader.md": reader,
        "formulas/host.md": host,
        "quantities/weight-read.md": quantity("weight-read", "W_r", "N", "derived"),
        "quantities/weight-host.md": quantity("weight-host", "W_h", "N", "derived"),
    }
    messages = shown(run(tmp_path, files))
    assert (
        "formulas/reader.md: applications[0].bind.h: calc:hinge is a per_control_surface quantity: "
        "no application may read it (it is an output only; nothing computes from it)"
    ) in messages


@pytest.mark.parametrize("role", ["input", "target", "derived"])
def test_a_per_control_surface_quantity_must_have_role_output(tmp_path: Path, role: str) -> None:
    """README: the type is output only."""
    files = hinge_files()
    files[HINGE] = quantity("hinge", "M_h", "N*m", role, "per_control_surface")
    messages = shown(run(tmp_path, files))
    assert (
        "quantities/hinge.md: role: a per_control_surface quantity has role output only "
        f"(canon README, quantity types); this one is {role}"
    ) in messages


def test_a_per_control_surface_quantity_with_role_output_is_fine(tmp_path: Path) -> None:
    assert shown(run(tmp_path, hinge_files())) == []


def same_application_files(type_: str) -> dict[str, str | None]:
    """One application that produces ``hinge`` through two output parameters."""
    body = "kind: law\ntool: APP\ninputs: {m: aircraft-mass}\noutputs: {h: hinge, h2: hinge}\n"
    return {
        HINGE: quantity("hinge", "M_h", "N*m", "output", type_),
        HINGES: formula("hinges", body),
    }


def test_one_application_may_not_produce_a_per_control_surface_quantity_twice(
    tmp_path: Path,
) -> None:
    """Two entries under one (surface, application) key would be ambiguous."""
    assert shown(run(tmp_path, same_application_files("per_control_surface"))) == [
        "formulas/hinges.md: applications[0].produce.h2: quantity calc:hinge is already produced by "
        f"calc:hinges.default {PER_SURFACE_MESSAGE}"
    ]


def test_one_application_producing_a_scalar_twice_is_still_a_finding(tmp_path: Path) -> None:
    assert shown(run(tmp_path, same_application_files("scalar"))) == [
        "formulas/hinges.md: applications[0].produce.h2: quantity calc:hinge is already produced by "
        f"calc:hinges.default {PER_SURFACE_MESSAGE}"
    ]
