"""The rules of the canon model: validation rules with overridable parameters (gh-1260)."""

import copy
from typing import Any

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.tests.canon_builders import base_namespaces, with_hash
from pydantic import ValidationError

PARAMETER: dict[str, Any] = {
    "value": 45.0,
    "unit": "deg",
    "basis": "convention",
    "status": "adopted",
    "source": "adopted by the maintainer on 2026-10-25",
    "regime": "regime-independent",
}
RULE: dict[str, Any] = {
    "applies_to": {"quantity": "aircraft-mass"},
    "kind": "input",
    "on_violation": "error",
    "criterion": "the value is plausible",
    "parameters": {"limit": PARAMETER},
}


def build(rule: dict[str, Any] | None = None, **changes: Any) -> CanonModel:
    namespaces = base_namespaces()
    namespaces["calc"]["rules"] = {"a-rule": copy.deepcopy({**(rule or RULE), **changes})}
    return CanonModel.model_validate(with_hash(namespaces))


def test_a_rule_lives_in_the_namespace_with_its_parameter() -> None:
    rule = build().namespaces["calc"].rules["a-rule"]
    assert rule.parameters["limit"].value == 45.0
    assert (rule.kind, rule.on_violation) == ("input", "error")
    assert rule.parameters["limit"].status == "adopted"


def test_a_namespace_without_rules_has_an_empty_table() -> None:
    assert CanonModel.model_validate(with_hash(base_namespaces())).namespaces["calc"].rules == {}


def test_a_rule_may_belong_to_a_formula() -> None:
    assert build(applies_to={"formula": "weight-from-mass"}).namespaces["calc"].rules["a-rule"]


@pytest.mark.parametrize(
    "target",
    [
        {"quantity": "ghost"},
        {"formula": "ghost"},
        {},
        {"quantity": "gravity", "formula": "weight-from-mass"},
    ],
)
def test_a_rule_names_exactly_one_existing_target(target: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        build(applies_to=target)


def test_a_pending_parameter_is_allowed_but_stays_pending() -> None:
    pending = {**PARAMETER, "status": "pending"}
    rule = build(parameters={"limit": pending}).namespaces["calc"].rules["a-rule"]
    assert rule.parameters["limit"].status == "pending"


@pytest.mark.parametrize(
    "change", [{"unit": "furlong"}, {"basis": "guess"}, {"status": "maybe"}, {"source": " "}]
)
def test_a_parameter_with_a_bad_field_is_rejected(change: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        build(parameters={"limit": {**PARAMETER, **change}})
