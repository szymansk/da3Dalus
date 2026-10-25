"""The tool of a method world (ARCHITECTURE ch. 8.4, 8.9; #1221)."""

from typing import Any

import pytest
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from pydantic import ValidationError

TAXONOMY: dict[str, Any] = {
    "tools": [
        {"id": "AVL", "name": "AVL"},
        {"id": "APP", "name": "App"},
        {"id": "OPT", "name": "O"},
    ],
    "worlds": [{"id": "avl", "tool": "AVL"}, {"id": "textbook", "tool": "APP"}],
}


def build(worlds: list[str], taxonomy: dict[str, Any] | None = None) -> Any:
    return model_of(
        {"aircraft-mass": quantity("input", unit="kg"), "np-q": quantity("derived")},
        {
            "np": formula(
                {"m": "aircraft-mass"},
                {"o": "np-q"},
                tool="OPT",
                uncertainty="interval",
                worlds=worlds,
            ),
            "plain": formula({"m": "aircraft-mass"}, {"o": "np-q"}, tool="AVL"),
        },
        taxonomy=TAXONOMY if taxonomy is None else taxonomy,
    )


def test_a_world_the_taxonomy_lacks_makes_the_model_invalid() -> None:
    with pytest.raises(ValidationError, match=r"world 'pappas'.*no tool"):
        build(["avl", "pappas"])


def test_a_formula_with_worlds_needs_a_taxonomy_that_names_them() -> None:
    with pytest.raises(ValidationError, match="world 'avl'"):
        build(["avl", "textbook"], taxonomy={})


def test_the_tool_of_a_world_is_the_taxonomys_not_the_formulas() -> None:
    model = build(["avl", "textbook"])
    assert model.tool_of("calc:np", "avl") == "AVL"
    assert model.tool_of("calc:np", "textbook") == "APP"


def test_a_formula_without_worlds_has_its_own_tool() -> None:
    assert build(["avl", "textbook"]).tool_of("calc:plain", None) == "AVL"


def test_a_world_the_model_does_not_know_is_refused() -> None:
    model = build(["avl", "textbook"])
    with pytest.raises(ValueError, match="no world 'ghost'"):
        model.tool_of("calc:np", "ghost")
    with pytest.raises(ValueError, match="no formula"):
        model.tool_of("calc:ghost", None)
