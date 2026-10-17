"""Importer stage 3 (assemble): model errors become findings with file and field."""

from aero_kernel.importer.assemble import assemble
from aero_kernel.tests.importer_builders import SOURCE_COMMIT


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


def test_an_error_outside_the_namespaces_names_the_canon_model() -> None:
    model, findings = assemble(namespace(), "not-a-commit")
    assert model is None
    assert [(f.file, f.field) for f in findings] == [("canon model", "model")]
