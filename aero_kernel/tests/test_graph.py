"""Graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13)."""

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.graph import CanonGraph, GraphModelError, NodeId
from aero_kernel.tests.graph_builders import formula, model_of, quantity


def test_every_application_of_the_fixture_is_a_node(flight_canon: CanonModel) -> None:
    graph = CanonGraph(flight_canon)
    stall = {
        NodeId(formula="calc:stall-speed", application=a) for a in ("clean", "landing", "inverted")
    }
    assert stall <= set(graph.node_ids)
    assert len(graph.node_ids) == 9


def test_two_producers_of_one_quantity_are_a_model_error() -> None:
    model = model_of(
        {"a": quantity("input"), "b": quantity("output")},
        {"f1": formula({"x": "a"}, {"y": "b"}), "f2": formula({"x": "a"}, {"y": "b"})},
    )
    with pytest.raises(GraphModelError, match=r"calc:b.*calc:f1.*calc:f2"):
        CanonGraph(model)


def test_a_read_quantity_nobody_produces_is_a_model_error() -> None:
    model = model_of(
        {"a": quantity("derived"), "b": quantity("output")},
        {"f": formula({"x": "a"}, {"y": "b"})},
    )
    with pytest.raises(GraphModelError, match=r"calc:a.*no producer"):
        CanonGraph(model)
