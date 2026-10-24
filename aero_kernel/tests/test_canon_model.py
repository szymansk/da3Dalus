"""The canon model: identity, hash and the structural integrity of its references."""

import copy
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
    raw["namespaces"]["calc"]["defaults"]["gravity"]["value"] = 9.81
    with pytest.raises(ValidationError, match="content_hash"):
        CanonModel.model_validate(raw)


def test_hash_ignores_provenance() -> None:
    first = base_model()
    second = base_model()
    second["importer_version"] = "9.9.9"
    assert first["content_hash"] == second["content_hash"]
    CanonModel.model_validate(second)


def test_hash_format_and_provenance_formats() -> None:
    for field, bad in (
        ("content_hash", "abc"),
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
    ],
)
def test_given_must_be_supplied_input_or_target_without_default(quantity: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="given"):
        build(with_given(base_namespaces(), **quantity))


GRAVITY_DEFAULT: dict[str, Any] = {
    "value": 9.80665,
    "unit": "m/s^2",
    "basis": "standard",
    "source": "ISO 80000-3",
    "regime": "RC and UAV, sea level",
}


def with_defaults(namespaces: dict[str, Any], **defaults: Any) -> dict[str, Any]:
    """Put ``defaults`` (slug to entry) into the ``calc`` namespace."""
    namespaces["calc"]["defaults"] = defaults
    return namespaces


def test_a_default_lives_in_the_namespace_and_resolves_to_its_quantity() -> None:
    model = build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT))
    default = model.namespaces["calc"].defaults["gravity"]
    assert (default.value, default.unit, default.regime) == (
        9.80665,
        "m/s^2",
        "RC and UAV, sea level",
    )


def test_a_namespace_without_defaults_has_an_empty_table() -> None:
    namespaces = base_namespaces()
    del namespaces["calc"]["defaults"]
    assert build(namespaces).namespaces["calc"].defaults == {}


def test_a_default_of_an_unknown_quantity_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ghost"):
        build(with_defaults(base_namespaces(), ghost=GRAVITY_DEFAULT))


@pytest.mark.parametrize("role", ["derived", "output"])
def test_a_default_on_a_computed_quantity_is_rejected(role: str) -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["computed"] = {
        "symbol": "c",
        "unit": "N",
        "role": role,
        "type": "scalar",
    }
    with pytest.raises(ValidationError, match="role"):
        build(with_defaults(namespaces, computed=GRAVITY_DEFAULT | {"unit": "N"}))


def test_a_negative_default_is_accepted_on_a_quantity_that_is_not_positive() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["offset"] = {
        "symbol": "dx",
        "unit": "m",
        "role": "input",
        "type": "scalar",
    }
    model = build(
        with_defaults(
            namespaces,
            gravity=GRAVITY_DEFAULT,
            offset=GRAVITY_DEFAULT | {"unit": "m", "value": -1.0},
        )
    )
    assert model.namespaces["calc"].defaults["offset"].value == -1.0


def test_defaults_are_checked_in_every_namespace() -> None:
    namespaces = with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT)
    namespaces["other"] = copy.deepcopy(namespaces["calc"])
    namespaces["other"]["defaults"]["gravity"]["unit"] = "N"
    with pytest.raises(ValidationError, match="other:gravity"):
        build(namespaces)


def test_a_default_on_a_non_scalar_quantity_is_rejected() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["shape"] = {
        "symbol": "S",
        "unit": "1",
        "role": "input",
        "type": "curve",
    }
    with pytest.raises(ValidationError, match="scalar"):
        build(with_defaults(namespaces, shape=GRAVITY_DEFAULT | {"unit": "1"}))


def test_a_default_unit_must_equal_the_quantity_unit() -> None:
    with pytest.raises(ValidationError, match="unit"):
        build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {"unit": "N"}))


@pytest.mark.parametrize("value", [0.0, -1.0])
def test_the_default_of_a_positive_quantity_must_be_positive(value: float) -> None:
    with pytest.raises(ValidationError, match="positive"):
        build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {"value": value}))


def test_the_default_of_a_bounded_quantity_must_not_exceed_its_maximum() -> None:
    namespaces = base_namespaces()
    namespaces["calc"]["quantities"]["gravity"]["at_most"] = 10.0
    with pytest.raises(ValidationError, match="at_most"):
        build(with_defaults(namespaces, gravity=GRAVITY_DEFAULT | {"value": 10.5}))


@pytest.mark.parametrize("field", ["source", "regime"])
def test_a_default_needs_a_source_and_a_regime(field: str) -> None:
    with pytest.raises(ValidationError):
        build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {field: ""}))


@pytest.mark.parametrize("basis", ["", "assumed", "Convention", None])
def test_a_default_basis_is_one_of_the_four_terms(basis: str | None) -> None:
    namespaces = with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {"basis": basis})
    with pytest.raises(ValidationError):
        build(namespaces)


def test_a_default_without_a_basis_is_rejected() -> None:
    default = {key: value for key, value in GRAVITY_DEFAULT.items() if key != "basis"}
    namespaces = with_defaults(base_namespaces(), gravity=default)
    with pytest.raises(ValidationError, match="basis"):
        build(namespaces)


@pytest.mark.parametrize("basis", ["definition", "standard", "sourced", "convention"])
def test_every_basis_term_is_accepted(basis: str) -> None:
    model = build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {"basis": basis}))
    assert model.namespaces["calc"].defaults["gravity"].basis == basis


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_default_value_must_be_finite(bad: float) -> None:
    with pytest.raises(ValidationError, match="finite"):
        build(with_defaults(base_namespaces(), gravity=GRAVITY_DEFAULT | {"value": bad}))


def test_a_given_quantity_must_not_have_a_default() -> None:
    namespaces = with_given(base_namespaces(), role="input")
    with pytest.raises(ValidationError, match="given"):
        build(with_defaults(namespaces, extra=GRAVITY_DEFAULT | {"unit": "1"}))


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


def problems_of(error: ValidationError) -> list[dict[str, Any]]:
    """Return the structured problems a whole-model rule carries in its error context."""
    (entry,) = error.errors(include_url=False, include_input=False)
    assert entry["type"] == "canon_problems"
    return list(entry["ctx"]["problems"])  # type: ignore[index,no-any-return]  # pydantic types ctx loosely


def test_unresolved_references_are_structured_problems_with_the_precise_field() -> None:
    namespaces = with_given(base_namespaces())
    formula = namespaces["calc"]["formulas"]["weight-from-mass"]
    formula["inputs"]["x"] = "calc:ghost"
    formula["applications"][0]["bind"]["x"] = "calc:ghost"
    formula["applications"][0]["given"] = ["calc:ghost"]
    with pytest.raises(ValidationError) as raised:
        build(namespaces)
    assert problems_of(raised.value) == [
        {
            "namespace": "calc",
            "section": "formulas",
            "slug": "weight-from-mass",
            "field": field,
            "side": side,
            "application": application,
            "parameter": parameter,
            "text": "unknown quantity calc:ghost",
        }
        for field, side, application, parameter in (
            ("inputs.x", "inputs", None, "x"),
            ("applications[0].bind.x", "bind", 0, "x"),
            ("applications[0].given[0]", None, None, None),
        )
    ]


def test_a_bad_default_is_a_structured_problem_of_the_defaults_section() -> None:
    namespaces = with_defaults(base_namespaces(), ghost=GRAVITY_DEFAULT)
    with pytest.raises(ValidationError) as raised:
        build(namespaces)
    assert problems_of(raised.value) == [
        {
            "namespace": "calc",
            "section": "defaults",
            "slug": "ghost",
            "field": "",
            "side": None,
            "application": None,
            "parameter": None,
            "text": "default of unknown quantity calc:ghost",
        }
    ]


def test_a_binding_error_location_uses_our_own_tags() -> None:
    """The union of a slug and a constant names its branch ``slug`` or ``const``, nothing else."""
    from aero_kernel.canon.model import BINDING_TAGS, Application

    with pytest.raises(ValidationError) as slug:
        Application.model_validate({"id": "default", "bind": {"m": "Not A Slug"}, "produce": {}})
    with pytest.raises(ValidationError) as const:
        Application.model_validate({"id": "default", "bind": {"m": {"const": 1.0}}, "produce": {}})
    assert [e["loc"] for e in slug.value.errors()] == [("bind", "m", "slug")]
    assert [e["loc"] for e in const.value.errors()] == [("bind", "m", "const", "source")]
    assert BINDING_TAGS == ("slug", "const")


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
            "BINDING_TAGS",
            "DEFAULT_NAMESPACE",
            "Application",
            "Binding",
            "CanonModel",
            "CanonProblem",
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


def test_canon_model_is_frozen() -> None:
    model = CanonModel.model_validate(base_model())
    with pytest.raises(ValidationError, match="frozen"):
        model.importer_version = "9"  # type: ignore[misc]  # the assignment is the thing under test


def test_hash_covers_every_namespace() -> None:
    namespaces = base_namespaces()
    namespaces["other"] = copy.deepcopy(namespaces["calc"])
    first = with_hash(namespaces)["content_hash"]
    namespaces["other"]["defaults"]["gravity"]["value"] = 9.81
    assert with_hash(namespaces)["content_hash"] != first


def test_an_unknown_embed_is_a_problem_of_the_embeds_field() -> None:
    namespaces = embedding_namespaces()
    formula = namespaces["calc"]["formulas"]["limit"]
    formula["embeds"] = ["calc:ghost.default"]
    formula["embeds_closure"] = ["calc:ghost.default"]
    with pytest.raises(ValidationError) as raised:
        build(namespaces)
    fields = [problem["field"] for problem in problems_of(raised.value)]
    assert fields == ["embeds[0]", "embeds_closure[0]"]


def test_a_python_built_constant_binding_validates_without_warnings() -> None:
    import warnings

    from aero_kernel.canon.model import Application, ConstBinding

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        application = Application(
            id="default",
            bind={"m": ConstBinding(const=1.0, source="s")},
            produce={},
        )
    assert application.bind["m"] == ConstBinding(const=1.0, source="s")


def test_given_names_the_unbound_slug_only() -> None:
    namespaces = with_given(base_namespaces())
    formula = namespaces["calc"]["formulas"]["weight-from-mass"]
    formula["applications"][0]["given"] = ["calc:aircraft-mass", "calc:gravity-ghost"]
    namespaces["calc"]["quantities"]["gravity-ghost"] = dict(
        namespaces["calc"]["quantities"]["gravity"]
    )
    with pytest.raises(ValidationError) as raised:
        build(namespaces)
    message = str(raised.value)
    assert "given calc:gravity-ghost is not bound by the application" in message
    assert "given calc:aircraft-mass is not bound" not in message
