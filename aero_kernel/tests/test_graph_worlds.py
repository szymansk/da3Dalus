"""Method-world expansion over the graph (ARCHITECTURE ch. 8.13, A11)."""

from typing import Any

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import format_world_assignment
from aero_kernel.graph import CanonGraph, GraphModelError, NodeId
from aero_kernel.tests.canon_builders import with_hash
from aero_kernel.tests.graph_builders import formula, model_of, quantity


def node_id(slug: str, application: str = "default") -> NodeId:
    return NodeId(formula=f"calc:{slug}", application=application)


def uncertain(reads: dict[str, str], writes: dict[str, str], worlds: list[str]) -> dict[str, Any]:
    return formula(reads, writes, uncertainty="interval", worlds=worlds)


def two_worlds_model() -> CanonModel:
    """Two uncertain formulas u1 (a, b) and u2 (x, y, z), a certain head and three consumers."""
    return model_of(
        {
            s: quantity("input" if s == "i" else "derived")
            for s in ("i", "h", "p", "q", "both", "only1", "tail")
        },
        {
            "head": formula({"v": "i"}, {"o": "h"}),
            "u1": uncertain({"v": "h"}, {"o": "p"}, ["a", "b"]),
            "u2": uncertain({"v": "h"}, {"o": "q"}, ["x", "y", "z"]),
            "both": formula({"v": "p", "w": "q"}, {"o": "both"}),
            "only1": formula({"v": "p"}, {"o": "only1"}),
            "tail": formula({"v": "both"}, {"o": "tail"}),
        },
    )


def test_a_certain_quantity_has_one_empty_assignment(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed"])
    assert subtree.uncertain_formulas("stall-speed") == ()
    assert subtree.world_assignments("stall-speed") == ({},)


def test_an_uncertain_quantity_has_one_assignment_per_world(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["neutral-point"])
    assert subtree.uncertain_formulas("neutral-point") == ("neutral-point",)
    assignments = subtree.world_assignments("neutral-point")
    assert [format_world_assignment(a) for a in assignments] == [
        "neutral-point=textbook",
        "neutral-point=pappas",
        "neutral-point=avl",
    ]


def test_two_uncertain_formulas_give_the_cartesian_product() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["both"])
    assert subtree.uncertain_formulas("both") == ("u1", "u2")
    assignments = [format_world_assignment(a) for a in subtree.world_assignments("both")]
    assert assignments == [
        "u1=a,u2=x",
        "u1=a,u2=y",
        "u1=a,u2=z",
        "u1=b,u2=x",
        "u1=b,u2=y",
        "u1=b,u2=z",
    ]


def test_worlds_reach_every_quantity_that_reads_an_uncertain_one() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["only1", "tail"])
    assert subtree.uncertain_formulas("only1") == ("u1",)
    assert len(subtree.world_assignments("only1")) == 2
    assert subtree.uncertain_formulas("tail") == ("u1", "u2")
    assert len(subtree.world_assignments("tail")) == 6


def test_the_nodes_of_a_quantity_are_its_own_subtree_in_order() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["only1", "tail"])
    assert subtree.nodes_for("only1") == (node_id("head"), node_id("u1"), node_id("only1"))
    assert subtree.nodes_for("calc:tail") == (
        node_id("head"),
        node_id("u1"),
        node_id("u2"),
        node_id("both"),
        node_id("tail"),
    )


def test_nodes_outside_an_uncertain_subtree_share_one_key() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["tail"])
    assignment = {"u1": "b", "u2": "y"}
    assert subtree.assignment_key(node_id("head"), assignment) is None
    assert subtree.assignment_key(node_id("u1"), assignment) == "u1=b"
    assert subtree.assignment_key(node_id("u2"), assignment) == "u2=y"
    assert subtree.assignment_key(node_id("both"), assignment) == "u1=b,u2=y"
    assert subtree.assignment_key(node_id("tail"), assignment) == "u1=b,u2=y"


def test_a_node_reading_one_world_is_keyed_by_that_world_only() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["only1", "tail"])
    assignment = {"u1": "a", "u2": "z"}
    assert subtree.assignment_key(node_id("only1"), assignment) == "u1=a"


def test_embeds_do_not_carry_worlds() -> None:
    namespaces: dict[str, Any] = {
        "calc": {
            "quantities": {
                "i": quantity("input"),
                "p": quantity("derived"),
                "e": quantity("derived"),
                "var": quantity("input"),
            },
            "formulas": {
                "u": uncertain({"v": "i"}, {"o": "p"}, ["a", "b"]),
                "emb": formula(
                    {"v": "i"},
                    {"o": "e"},
                    embeds=["calc:u.default"],
                    embeds_closure=["calc:u.default"],
                    variables=["calc:var"],
                ),
            },
        }
    }
    model = CanonModel.model_validate(with_hash(namespaces))
    subtree = CanonGraph(model).subtree(["e"])
    assert subtree.uncertain_formulas("e") == ()
    assert subtree.world_assignments("e") == ({},)


def test_an_unrequested_quantity_has_no_worlds() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["tail"])
    for call in (subtree.uncertain_formulas, subtree.world_assignments, subtree.nodes_for):
        with pytest.raises(KeyError):
            call("only1")


def test_two_uncertain_formulas_with_one_bare_slug_are_a_model_error() -> None:
    namespaces: dict[str, Any] = {
        name: {
            "quantities": {"i": quantity("input"), "o": quantity("derived")},
            "formulas": {
                "np": formula({"v": "i"}, {"o": "o"}, uncertainty="interval", worlds=["a", "b"])
            },
        }
        for name in ("calc", "other")
    }
    # the helper qualifies with ``calc:``; the second namespace must refer to its own quantities
    for formula_doc in (namespaces["other"]["formulas"]["np"],):
        for key in ("inputs", "outputs"):
            formula_doc[key] = {
                k: v.replace("calc:", "other:") for k, v in formula_doc[key].items()
            }
        for application in formula_doc["applications"]:
            for key in ("bind", "produce"):
                application[key] = {
                    k: v.replace("calc:", "other:") for k, v in application[key].items()
                }
    model = CanonModel.model_validate(with_hash(namespaces))
    with pytest.raises(GraphModelError, match=r"calc:np.*other:np"):
        CanonGraph(model)


def test_a_malformed_world_in_an_assignment_is_rejected() -> None:
    subtree = CanonGraph(two_worlds_model()).subtree(["only1"])
    with pytest.raises(ValueError, match="malformed"):
        subtree.assignment_key(node_id("u1"), {"u1": "Not A World"})
