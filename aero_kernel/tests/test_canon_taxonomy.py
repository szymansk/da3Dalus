"""The taxonomy types: shape, uniqueness, references between values."""

import pytest
from aero_kernel.canon.taxonomy import Taxonomy
from pydantic import ValidationError


def value(identifier: str, **extra: object) -> dict[str, object]:
    return {
        "id": identifier,
        "label": identifier.title(),
        "explanation": f"About {identifier}.",
        **extra,
    }


def test_an_empty_taxonomy_is_valid_and_has_no_default_direction() -> None:
    taxonomy = Taxonomy()
    assert taxonomy.modules == ()


def test_the_list_order_is_the_display_order() -> None:
    taxonomy = Taxonomy.model_validate({"stages": [value("b"), value("a")]})
    assert [stage.id for stage in taxonomy.stages] == ["b", "a"]


def test_properties_are_carried() -> None:
    taxonomy = Taxonomy.model_validate(
        {
            "modules": [value("m", cross_cutting=True, holds_targets=False)],
            "disciplines": [value("d", stability=True)],
            "groups": [value("p"), value("p-child", parent="p")],
        }
    )
    assert taxonomy.modules[0].cross_cutting
    assert taxonomy.disciplines[0].stability
    assert taxonomy.groups[1].parent == "p"


def test_a_duplicate_id_is_rejected() -> None:
    with pytest.raises(ValidationError, match="duplicate id"):
        Taxonomy.model_validate({"points": [value("a"), value("a")]})


@pytest.mark.parametrize(
    ("document", "text"),
    [
        ({"groups": [value("g", parent="missing")]}, "parent 'missing'"),
        ({"groups": [value("g", stage="missing")]}, "stage 'missing'"),
        ({"groups": [value("g", module="missing")]}, "module 'missing'"),
        ({"groups": [value("g", parent="g")]}, "parent is the group itself"),
        (
            {"groups": [value("a"), value("b", parent="a"), value("c", parent="b")]},
            "itself a part of a group",
        ),
        ({"worlds": [{"id": "w", "tool": "APP"}]}, "not in tools"),
    ],
)
def test_a_reference_to_a_missing_value_is_rejected(document: dict[str, object], text: str) -> None:
    with pytest.raises(ValidationError, match=text):
        Taxonomy.model_validate(document)


def test_exactly_one_direction_is_the_default() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        Taxonomy.model_validate({"directions": [value("a"), value("b")]})
    with pytest.raises(ValidationError, match="exactly one"):
        Taxonomy.model_validate(
            {"directions": [value("a", default=True), value("b", default=True)]}
        )
    taxonomy = Taxonomy.model_validate({"directions": [value("a", default=True), value("b")]})
    assert [d.id for d in taxonomy.directions if d.default] == ["a"]


def test_an_unknown_field_and_a_blank_text_are_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        Taxonomy.model_validate({"points": [value("a", colour="red")]})
    with pytest.raises(ValidationError, match="at least 1 character"):
        Taxonomy.model_validate({"points": [{**value("a"), "label": ""}]})
