"""The canon model: identity, hash and the structural integrity of its references."""

import json
from pathlib import Path
from typing import Any

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.tests.canon_builders import base_model, base_namespaces, with_hash
from pydantic import ValidationError


def build(namespaces: dict[str, Any]) -> CanonModel:
    """Build a model around ``namespaces`` with a matching hash."""
    return CanonModel.model_validate(with_hash(namespaces))


def test_minimal_model_is_valid() -> None:
    model = CanonModel.model_validate(base_model())
    assert model.schema_version == 1
    assert model.namespaces["calc"].formulas["weight-from-mass"].tool == "APP"


def test_lookup_resolves_bare_and_qualified_slugs() -> None:
    model = CanonModel.model_validate(base_model())
    assert model.quantity("aircraft-mass") is model.namespaces["calc"].quantities["aircraft-mass"]
    assert model.quantity("calc:aircraft-mass") is model.quantity("aircraft-mass")
    assert model.quantity("nope") is None
    assert model.quantity("other:aircraft-mass") is None


@pytest.mark.parametrize("version", [0, 2, "1"])
def test_only_schema_version_one(version: object) -> None:
    raw = base_model()
    raw["schema_version"] = version
    with pytest.raises(ValidationError):
        CanonModel.model_validate(raw)


def test_hash_must_match_the_namespaces() -> None:
    raw = base_model()
    raw["namespaces"]["calc"]["quantities"]["gravity"]["default"]["value"] = 9.81
    with pytest.raises(ValidationError, match="content_hash"):
        CanonModel.model_validate(raw)


def test_hash_ignores_provenance() -> None:
    first = base_model()
    second = base_model()
    second["source_commit"] = "f" * 40
    second["importer_version"] = "9.9.9"
    assert first["content_hash"] == second["content_hash"]
    CanonModel.model_validate(second)


def test_hash_format_and_provenance_formats() -> None:
    for field, bad in (
        ("content_hash", "abc"),
        ("source_commit", "xyz"),
        ("importer_version", ""),
    ):
        raw = base_model()
        raw[field] = bad
        with pytest.raises(ValidationError):
            CanonModel.model_validate(raw)


def test_namespace_and_slug_keys_are_validated() -> None:
    namespaces = base_namespaces()
    namespaces["Bad Name"] = namespaces["calc"]
    with pytest.raises(ValidationError):
        build(namespaces)
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["Bad_Slug"] = namespaces["calc"]["quantities"]["weight"]
    with pytest.raises(ValidationError):
        build(namespaces)


def test_model_needs_a_namespace() -> None:
    with pytest.raises(ValidationError):
        build({})


@pytest.mark.parametrize(
    "path",
    [
        ("inputs", "m"),
        ("outputs", "w"),
        ("applications", 0, "bind", "m"),
        ("applications", 0, "produce", "w"),
    ],
)
def test_unknown_quantity_reference_is_rejected(path: tuple[str | int, ...]) -> None:
    namespaces = base_namespaces()
    node: Any = namespaces["calc"]["formulas"]["weight-from-mass"]
    for step in path[:-1]:
        node = node[step]
    node[path[-1]] = "calc:ghost"
    with pytest.raises(ValidationError, match="calc:ghost"):
        build(namespaces)


def test_unknown_namespace_reference_is_rejected() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["formulas"]["weight-from-mass"]["outputs"]["w"] = "sizing:weight"
    namespaces["calc"]["formulas"]["weight-from-mass"]["applications"][0]["produce"]["w"] = (
        "sizing:weight"
    )
    with pytest.raises(ValidationError, match="sizing:weight"):
        build(namespaces)


def test_cross_namespace_reference_is_allowed_when_it_resolves() -> None:
    namespaces = base_namespaces()
    namespaces["sizing"] = {
        "quantities": {"mtow": namespaces["calc"]["quantities"]["aircraft-mass"]},
        "formulas": {},
    }
    formula = namespaces["calc"]["formulas"]["weight-from-mass"]
    formula["inputs"]["m"] = "sizing:mtow"
    formula["applications"][0]["bind"]["m"] = "sizing:mtow"
    model = build(namespaces)
    assert model.quantity("sizing:mtow") is not None


def test_const_binding_needs_no_quantity() -> None:
    namespaces = base_namespaces()
    formula = namespaces["calc"]["formulas"]["weight-from-mass"]
    formula["inputs"]["g"] = None
    formula["applications"][0]["bind"]["g"] = {"const": 9.81, "source": "test"}
    build(namespaces)


def with_given(namespaces: dict[str, Any], **quantity: Any) -> dict[str, Any]:
    """Add a quantity ``extra`` bound as a ``given`` of the formula's application."""
    ns = namespaces["calc"]
    ns["quantities"]["extra"] = {
        "symbol": "x",
        "unit": "1",
        "role": "target",
        "type": "scalar",
        **quantity,
    }
    formula = ns["formulas"]["weight-from-mass"]
    formula["inputs"]["x"] = "calc:extra"
    formula["applications"][0]["bind"]["x"] = "calc:extra"
    formula["applications"][0]["given"] = ["calc:extra"]
    return namespaces


def test_given_may_be_a_target_without_default() -> None:
    build(with_given(base_namespaces()))


@pytest.mark.parametrize(
    "quantity",
    [
        {"role": "derived"},
        {"role": "output"},
        {"default": {"value": 1.0, "source": "s"}},
    ],
)
def test_given_must_be_supplied_input_or_target_without_default(quantity: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="given"):
        build(with_given(base_namespaces(), **quantity))


def embedding_namespaces() -> dict[str, Any]:
    """Return a model whose second formula embeds the first one's ``default`` application."""
    namespaces = base_namespaces()
    ns = namespaces["calc"]
    ns["quantities"]["mass-limit"] = {
        "symbol": "m_max",
        "unit": "kg",
        "role": "output",
        "type": "scalar",
    }
    ns["formulas"]["limit"] = {
        "kind": "optimization",
        "tool": "OPT",
        "cost": "minutes",
        "inputs": {"g": "calc:gravity"},
        "outputs": {"m_max": "calc:mass-limit"},
        "applications": [
            {
                "id": "default",
                "bind": {"g": "calc:gravity"},
                "produce": {"m_max": "calc:mass-limit"},
            }
        ],
        "embeds": ["calc:weight-from-mass.default"],
        "variables": ["calc:aircraft-mass"],
        "embeds_closure": ["calc:weight-from-mass.default"],
    }
    return namespaces


def test_embeds_that_resolve_are_valid() -> None:
    build(embedding_namespaces())


@pytest.mark.parametrize(
    "item", ["calc:ghost.default", "calc:weight-from-mass.nope", "sizing:x.default"]
)
def test_embeds_items_must_resolve(item: str) -> None:
    namespaces = embedding_namespaces()
    formula = namespaces["calc"]["formulas"]["limit"]
    formula["embeds"] = [item]
    formula["embeds_closure"] = [item]
    with pytest.raises(ValidationError, match=item):
        build(namespaces)


@pytest.mark.parametrize(
    "item", ["calc:ghost.default", "calc:weight-from-mass.nope", "sizing:x.default"]
)
def test_closure_items_must_resolve(item: str) -> None:
    namespaces = embedding_namespaces()
    formula = namespaces["calc"]["formulas"]["limit"]
    formula["embeds_closure"] = sorted([*formula["embeds_closure"], item])
    with pytest.raises(ValidationError, match=item):
        build(namespaces)


def test_variables_must_resolve_to_quantities() -> None:
    namespaces = embedding_namespaces()
    namespaces["calc"]["formulas"]["limit"]["variables"] = ["calc:ghost"]
    with pytest.raises(ValidationError, match="calc:ghost"):
        build(namespaces)


def test_error_message_names_formula() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["formulas"]["weight-from-mass"]["inputs"]["m"] = "calc:ghost"
    namespaces["calc"]["formulas"]["weight-from-mass"]["applications"][0]["bind"]["m"] = (
        "calc:ghost"
    )
    with pytest.raises(ValidationError, match="weight-from-mass"):
        build(namespaces)


def test_dump_round_trips() -> None:
    model = CanonModel.model_validate(base_model())
    assert CanonModel.model_validate(model.model_dump(mode="json")) == model


def test_given_must_resolve_to_a_quantity() -> None:
    namespaces = with_given(base_namespaces())
    formula = namespaces["calc"]["formulas"]["weight-from-mass"]
    formula["inputs"]["x"] = "calc:ghost"
    formula["applications"][0]["bind"]["x"] = "calc:ghost"
    formula["applications"][0]["given"] = ["calc:ghost"]
    with pytest.raises(ValidationError, match="unknown quantity calc:ghost"):
        build(namespaces)


def test_public_names_of_the_model_are_pinned() -> None:
    from aero_kernel.canon import model

    assert sorted(model.__all__) == sorted(
        [
            "DEFAULT_NAMESPACE",
            "Application",
            "Binding",
            "CanonModel",
            "Check",
            "ConstBinding",
            "CostClass",
            "Default",
            "Formula",
            "FormulaKind",
            "Namespace",
            "OnViolation",
            "Quantity",
            "QuantityRole",
            "QuantityType",
            "Tool",
            "Unit",
            "WhenTerm",
            "compute_content_hash",
        ]
    )
    for name in model.__all__:
        assert hasattr(model, name)


def test_model_holds_no_second_definition_of_the_slug_and_world_patterns() -> None:
    from aero_kernel import errors
    from aero_kernel.canon import model

    source = Path(model.__file__).read_text(encoding="utf-8")
    for regex in (errors.SLUG_REGEX, errors.WORLD_NAME_REGEX):
        assert regex not in source


def test_schema_states_the_shared_patterns() -> None:
    from aero_kernel import errors
    from aero_kernel.canon.schema_file import schema_text

    text = schema_text()
    for regex in (errors.SLUG_REGEX, errors.WORLD_NAME_REGEX):
        assert json.dumps(f"^{regex}$") in text
