"""Import of ``rules.yaml``: the validation rules with their overridable parameters (gh-1260)."""

from pathlib import Path

from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import write_canon

RULES = """\
mass-plausible:
  applies_to: {quantity: gravity}
  kind: input
  on_violation: error
  criterion: "The value is below max_value."
  codes: [value_above_maximum]
  parameters:
    max_value:
      value: 20
      unit: "m/s^2"
      basis: convention
      status: adopted
      source: "a test value"
      regime: "regime-independent"
"""


def run(tmp_path: Path, rules: str | None) -> ImportResult:
    return import_canon(write_canon(tmp_path, {} if rules is None else {"rules.yaml": rules}))


def test_a_canon_without_rules_yaml_imports_with_no_rules(tmp_path: Path) -> None:
    result = run(tmp_path, None)
    assert result.findings == ()
    assert result.model is not None
    assert result.model.namespaces["calc"].rules == {}


def test_a_rule_is_carried_into_the_model_with_its_parameter(tmp_path: Path) -> None:
    result = run(tmp_path, RULES)
    assert result.findings == ()
    assert result.model is not None
    rule = result.model.namespaces["calc"].rules["mass-plausible"]
    assert rule.parameters["max_value"].value == 20
    assert rule.codes == ["value_above_maximum"]


def test_a_rule_of_an_unknown_quantity_is_a_finding_in_rules_yaml(tmp_path: Path) -> None:
    result = run(tmp_path, RULES.replace("quantity: gravity", "quantity: ghost"))
    assert result.model is None
    assert [(f.file, f.field) for f in result.findings] == [("rules.yaml", "mass-plausible")]


def test_a_rule_that_is_not_a_mapping_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, "mass-plausible: 3\n")
    assert [f.file for f in result.findings] == ["rules.yaml"]


def test_a_bad_parameter_field_is_a_finding_that_names_the_parameter(tmp_path: Path) -> None:
    result = run(tmp_path, RULES.replace("status: adopted", "status: maybe"))
    assert result.model is None
    (finding,) = result.findings
    assert finding.file == "rules.yaml"
    assert "max_value" in finding.field
