"""The taxonomy in the import: reading ``taxonomy.yaml``, validating the tags, carrying both."""

from pathlib import Path

from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import MINI_CANON, MINI_TAXONOMY, write_canon

WEIGHT = "quantities/weight.md"
MASS = "quantities/aircraft-mass.md"
RATIO = "quantities/ratio.md"
ESTIMATE = "formulas/estimate.md"

FAMILIES = """\
modules:
  - {id: body, label: Body, explanation: The airplane.}
  - {id: goals, label: Goals, explanation: What is asked., holds_targets: true}
points:
  - {id: cruise, label: Cruise, explanation: Cruise.}
  - {id: none, label: None, explanation: No point.}
stages:
  - {id: early, label: Early, explanation: First.}
  - {id: refs, label: Refs, explanation: Derived values., reference: true}
groups:
  - {id: air, label: Air, explanation: The air., stage: early, module: goals}
disciplines:
  - {id: forces, label: Forces, explanation: Forces., stability: true}
directions:
  - {id: analysis, label: Analysis, explanation: What an airplane does., default: true}
  - {id: design, label: Design, explanation: Target to quantity.}
"""

FINALS = (
    "weight",
    "weight-estimate",
    "weight-twice",
    "weight-outer",
    "weight-weighed",
    "weight-flapped",
)
SUPPLIED = ("aircraft-mass", "gravity", "airplane", "ratio")


def tag(text: str, *tags: str, extra: str = "", drop: str = "") -> str:
    """Add ``tags`` (and ``extra`` front matter) to a mini entry; ``drop`` removes one tag line."""
    lines = "".join(f"  - {value}\n" for value in tags)
    text = text.replace("tags:\n", f"tags:\n{lines}", 1)
    if drop:
        text = text.replace(f"  - {drop}\n", "", 1)
    return text.replace("---\n\n#", f"{extra}---\n\n#", 1) if extra else text


def complete() -> dict[str, str | None]:
    """The mini canon files, tagged so that they satisfy the families."""
    files: dict[str, str | None] = {"taxonomy.yaml": MINI_TAXONOMY + FAMILIES}
    for slug in SUPPLIED:
        files[f"quantities/{slug}.md"] = tag(MINI_CANON[f"quantities/{slug}.md"], "module/body")
    for slug in FINALS:
        files[f"quantities/{slug}.md"] = tag(
            MINI_CANON[f"quantities/{slug}.md"], "point/cruise", "discipline/forces"
        )
    return files


def run(tmp_path: Path, changes: dict[str, str | None] | None = None) -> ImportResult:
    """Import the complete mini canon with ``changes`` (file name to text) applied."""
    return import_canon(write_canon(tmp_path, {**complete(), **(changes or {})}))


def retag(name: str, *tags: str, extra: str = "", drop: str = "") -> dict[str, str | None]:
    """Return the change that adds ``tags`` to a file of :func:`complete` and drops one tag."""
    text = complete().get(name) or MINI_CANON[name]
    return {name: tag(text, *tags, extra=extra, drop=drop)}


def findings(result: ImportResult) -> list[str]:
    return [str(finding) for finding in result.findings]


def test_the_taxonomy_is_part_of_the_model(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert findings(result) == []
    assert result.model is not None
    taxonomy = result.model.namespaces["calc"].taxonomy
    assert [module.id for module in taxonomy.modules] == ["body", "goals"]
    assert taxonomy.groups[0].module == "goals"
    assert result.model_json is not None
    assert '"holds_targets"' in result.model_json


def test_the_tags_become_fields_of_the_quantity(tmp_path: Path) -> None:
    result = run(tmp_path)
    assert result.model is not None
    quantities = result.model.namespaces["calc"].quantities
    assert quantities["aircraft-mass"].module == "body"
    assert quantities["weight"].point == "cruise"
    assert quantities["weight"].discipline == "forces"
    assert quantities["weight"].stage is None


def test_a_formula_without_a_direction_tag_has_the_default_direction(tmp_path: Path) -> None:
    result = run(tmp_path, retag(ESTIMATE, "direction/design"))
    assert result.model is not None
    formulas = result.model.namespaces["calc"].formulas
    assert formulas["estimate"].direction == "design"
    assert formulas["weighing"].direction == "analysis"


def test_a_canon_without_directions_gives_none(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path))
    assert result.model is not None
    assert result.model.namespaces["calc"].formulas["weighing"].direction is None


def test_a_missing_taxonomy_is_a_finding(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": None}))
    assert [(f.file, f.field) for f in result.findings] == [("taxonomy.yaml", "document")]
    assert result.findings[0].message.startswith("missing")


def test_a_taxonomy_that_is_no_mapping_is_a_finding(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": "- a\n"}))
    assert findings(result) == ["taxonomy.yaml: document: must be a mapping family: [values]"]


def test_invalid_yaml_in_the_taxonomy_is_a_finding(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": "tools: [\n"}))
    assert [(f.file, f.field) for f in result.findings] == [("taxonomy.yaml", "document")]


def test_a_duplicate_key_in_the_taxonomy_is_a_finding(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": "tools: []\ntools: []\n"}))
    assert [(f.file, f.field) for f in result.findings] == [("taxonomy.yaml", "tools")]


def test_an_unknown_family_in_the_taxonomy_is_a_finding(tmp_path: Path) -> None:
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": MINI_TAXONOMY + "colours: []\n"}))
    assert [(f.file, f.field) for f in result.findings] == [("taxonomy.yaml", "colours")]


def test_a_taxonomy_value_without_an_explanation_is_a_finding(tmp_path: Path) -> None:
    broken = MINI_TAXONOMY + "points:\n  - {id: a, label: A}\n"
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": broken}))
    assert findings(result) == ["taxonomy.yaml: points[0].explanation: Field required"]


def test_an_unknown_tag_value_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(MASS, "module/ghost", drop="module/body"))
    assert findings(result) == [
        "quantities/aircraft-mass.md: module: 'ghost' is not in the taxonomy (modules: body, goals)"
    ]


def test_two_tags_of_one_family_are_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(MASS, "module/goals"))
    assert findings(result) == [
        "quantities/aircraft-mass.md: module: more than one module tag (goals, body): "
        "exactly one is allowed"
    ]


def test_a_family_the_taxonomy_leaves_empty_accepts_no_tag(tmp_path: Path) -> None:
    changes: dict[str, str | None] = {
        "taxonomy.yaml": MINI_TAXONOMY,
        MASS: tag(MINI_CANON[MASS], "module/body"),
    }
    result = import_canon(write_canon(tmp_path, changes))
    assert findings(result) == [
        "quantities/aircraft-mass.md: module: 'body' is not in the taxonomy "
        "(modules: none declared)"
    ]


def test_a_supplied_quantity_without_a_module_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(MASS, drop="module/body"))
    assert findings(result) == [
        "quantities/aircraft-mass.md: module: missing: an input or target needs a module tag"
    ]


def test_a_final_result_without_a_point_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, drop="point/cruise"))
    assert findings(result) == [
        "quantities/weight.md: point: missing: a final result needs a point tag"
    ]


def test_a_derived_quantity_without_a_discipline_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, drop="discipline/forces"))
    assert findings(result) == [
        "quantities/weight.md: discipline: missing: a derived quantity needs a discipline tag"
    ]


def test_a_reference_needs_a_module_and_a_group_and_no_discipline(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, "stage/refs", drop="discipline/forces"))
    assert findings(result) == [
        "quantities/weight.md: group: missing: a reference needs a group tag",
        "quantities/weight.md: module: missing: a reference needs a module tag",
    ]


def test_a_probe_names_the_quantity_it_checks(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, extra="checks: weight-estimate\n"))
    assert findings(result) == []
    assert result.model is not None
    assert result.model.namespaces["calc"].quantities["weight"].checks == "weight-estimate"


def test_a_probe_that_checks_nothing_known_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, extra="checks: ghost\n"))
    assert findings(result) == ["quantities/weight.md: checks: no quantity 'ghost'"]


def test_a_probe_cannot_check_itself(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, extra="checks: weight\n"))
    assert findings(result) == ["quantities/weight.md: checks: a quantity cannot check itself"]


def test_an_unknown_direction_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, retag(ESTIMATE, "direction/sideways"))
    assert findings(result) == [
        "formulas/estimate.md: direction: 'sideways' is not in the taxonomy "
        "(directions: analysis, design)"
    ]


def test_a_tool_the_taxonomy_lacks_is_a_finding(tmp_path: Path) -> None:
    thin = MINI_TAXONOMY.replace("  - {id: OPT, name: Optimisation}\n", "")
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": thin}))
    assert findings(result) == [
        "formulas/outer.md: tool: 'OPT' is not in the taxonomy (tools: APP, AB, AVL, ATM, GEO, KAT, APC)"
    ]


def test_a_world_the_taxonomy_lacks_is_a_finding(tmp_path: Path) -> None:
    thin = MINI_TAXONOMY.replace("  - {id: detailed, tool: AVL}\n", "")
    result = import_canon(write_canon(tmp_path, {"taxonomy.yaml": thin}))
    assert findings(result) == [
        "formulas/estimate.md: worlds[1]: world 'detailed' has no tool in the taxonomy"
    ]


def test_a_target_outside_a_target_module_is_a_finding(tmp_path: Path) -> None:
    text = tag(MINI_CANON[RATIO].replace("role: input", "role: target"), "module/body")
    result = run(tmp_path, {RATIO: text})
    assert (
        "quantities/ratio.md: module: a target stands in a module that holds targets, not 'body'"
    ) in findings(result)


def test_a_supplied_quantity_in_a_target_module_is_a_finding(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        retag(MASS, drop="module/body", extra="") | {MASS: tag(MINI_CANON[MASS], "module/goals")},
    )
    assert findings(result) == [
        "quantities/aircraft-mass.md: module: module 'goals' holds only targets; "
        "this quantity is input"
    ]


def test_a_group_must_agree_with_its_stage_and_module(tmp_path: Path) -> None:
    result = run(tmp_path, retag(WEIGHT, "group/air", "stage/early", "module/body"))
    assert findings(result) == [
        "quantities/weight.md: group: group 'air' belongs to module 'goals'; this quantity "
        "has module 'body'"
    ]
