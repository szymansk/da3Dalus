"""Importer stage 3 (assemble): model errors become findings with file and field."""

import pytest
from aero_kernel.importer.assemble import assemble, findings_of
from aero_kernel.tests.importer_builders import SOURCE_COMMIT
from pydantic import BaseModel, ValidationError, model_validator


def namespace(**formula_overrides: object) -> dict[str, object]:
    """A minimal valid namespace whose single formula takes ``formula_overrides``."""
    formula: dict[str, object] = {
        "kind": "law",
        "tool": "APP",
        "cost": "instant",
        "inputs": {"m": "calc:mass"},
        "outputs": {"w": "calc:weight"},
        "applications": [
            {
                "id": "default",
                "bind": {"m": "calc:mass"},
                "produce": {"w": "calc:weight"},
                "when": None,
                "given": None,
            }
        ],
        **formula_overrides,
    }
    return {
        "quantities": {
            "mass": {"symbol": "m", "unit": "kg", "role": "input", "type": "scalar"},
            "weight": {"symbol": "W", "unit": "N", "role": "derived", "type": "scalar"},
        },
        "formulas": {"weigh": formula},
        "defaults": {},
    }


def test_a_valid_namespace_assembles() -> None:
    model, findings = assemble(namespace(), SOURCE_COMMIT)
    assert findings == []
    assert model is not None


def test_a_list_index_in_the_location_is_rendered_in_brackets() -> None:
    bad = namespace(
        applications=[
            {
                "id": "default",
                "bind": {"m": "not a slug"},
                "produce": {"w": "calc:weight"},
                "when": None,
                "given": None,
            }
        ]
    )
    model, findings = assemble(bad, SOURCE_COMMIT)
    assert model is None
    assert any(
        f.file == "formulas/weigh.md" and f.field.startswith("applications[0].bind.m")
        for f in findings
    )


def test_a_field_of_the_model_itself_is_named_by_its_own_name() -> None:
    model, findings = assemble(namespace(), "not-a-commit")
    assert model is None
    assert [(f.file, f.field) for f in findings] == [("canon model", "source_commit")]


def test_a_whole_model_rule_the_mapping_does_not_know_still_becomes_a_finding() -> None:
    """A rule added to the model later must not vanish: it is reported against the model."""

    class Odd(BaseModel):
        @model_validator(mode="after")
        def _always(self) -> "Odd":
            msg = "something new"
            raise ValueError(msg)

    with pytest.raises(ValidationError) as raised:
        Odd()
    findings = findings_of(raised.value)
    assert [(f.file, f.field, f.message) for f in findings] == [
        ("canon model", "model", "something new")
    ]


def test_a_one_element_location_names_the_section_of_the_model() -> None:
    bad: dict[str, object] = {"quantities": {}, "formulas": 5, "defaults": {}}
    model, findings = assemble(bad, SOURCE_COMMIT)
    assert model is None
    assert [(f.file, f.field, f.message) for f in findings] == [
        ("canon model", "formulas", "Input should be a valid dictionary (got 5)")
    ]
