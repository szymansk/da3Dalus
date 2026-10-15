"""Graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13)."""

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import CanonGraph, Edge, GraphModelError, NodeId, Resolved, Subtree
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


STALL_CLEAN = NodeId(formula="calc:stall-speed", application="clean")


@pytest.mark.parametrize("request_slug", ["stall-speed", "calc:stall-speed"])
def test_a_derived_scalar_resolves_to_its_producing_node(
    flight_canon: CanonModel, request_slug: str
) -> None:
    resolved = CanonGraph(flight_canon).resolve(request_slug)
    assert isinstance(resolved, Resolved)
    assert resolved.slug == "calc:stall-speed"
    assert resolved.producer == STALL_CLEAN
    assert resolved.quantity.unit == "m/s"


def test_an_unknown_slug_is_unknown_quantity(flight_canon: CanonModel) -> None:
    error = CanonGraph(flight_canon).resolve("no-such-thing")
    assert isinstance(error, KernelError)
    assert (error.code, error.category) == ("unknown_quantity", ErrorCategory.INVALID_INPUT)
    assert error.quantity == "no-such-thing"


@pytest.mark.parametrize("slug", ["aircraft-mass", "cruise-speed-target", "airplane"])
def test_an_input_or_target_is_not_requestable(flight_canon: CanonModel, slug: str) -> None:
    error = CanonGraph(flight_canon).resolve(slug)
    assert isinstance(error, KernelError)
    assert (error.code, error.category) == ("not_requestable", ErrorCategory.INVALID_INPUT)
    assert error.quantity == slug


@pytest.mark.parametrize("slug", ["polar-stall", "airplane-landing", "butterfly-speed-range"])
def test_a_non_scalar_quantity_is_non_scalar_result(flight_canon: CanonModel, slug: str) -> None:
    error = CanonGraph(flight_canon).resolve(slug)
    assert isinstance(error, KernelError)
    assert (error.code, error.category) == ("non_scalar_result", ErrorCategory.NOT_IMPLEMENTED)
    assert error.quantity == slug


def test_a_requestable_quantity_nobody_produces_is_a_model_error() -> None:
    graph = CanonGraph(model_of({"a": quantity("derived")}, {}))
    with pytest.raises(GraphModelError, match=r"calc:a.*no producer"):
        graph.resolve("a")


def ids(subtree: Subtree) -> list[str]:
    return [f"{n.id.formula.removeprefix('calc:')}.{n.id.application}" for n in subtree.nodes]


def test_the_subtree_holds_the_requested_chain_back_to_the_leaves(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["approach-speed"])
    assert ids(subtree) == [
        "airplane-configuration.default",
        "stall-speed.landing",
        "speed-from-stall-margin.approach",
    ]
    assert subtree.leaf_inputs == (
        "calc:air-density",
        "calc:aircraft-mass",
        "calc:airplane",
        "calc:approach-speed-margin-target",
        "calc:flap-deflection-landing",
        "calc:gravity",
    )
    assert subtree.errors == ()


def test_only_the_requested_quantities_and_their_subtree_are_included(
    flight_canon: CanonModel,
) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed"])
    assert ids(subtree) == ["stall-speed.clean"]


def test_edges_name_the_predecessor_quantity_and_parameter(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["approach-speed"])
    approach = NodeId(formula="calc:speed-from-stall-margin", application="approach")
    landing = NodeId(formula="calc:stall-speed", application="landing")
    assert subtree.edges[approach] == (
        Edge(predecessor=landing, quantity="calc:stall-speed-landing", parameter="v_s_cfg"),
    )
    assert subtree.edges[NodeId(formula="calc:airplane-configuration", application="default")] == ()


def test_layers_group_the_nodes_that_are_independent(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed", "stall-speed-landing"])
    layers = [[n.application for n in layer] for layer in subtree.layers]
    assert layers == [["default", "clean"], ["landing"]]
    assert [n for layer in subtree.layers for n in layer] == [n.id for n in subtree.nodes]


def test_the_order_does_not_depend_on_the_request_order(flight_canon: CanonModel) -> None:
    graph = CanonGraph(flight_canon)
    a = graph.subtree(["stall-speed-landing", "stall-speed"])
    b = graph.subtree(["stall-speed", "stall-speed-landing"])
    assert a.nodes == b.nodes
    assert a.layers == b.layers


def test_rejected_quantities_are_reported_in_request_order_and_the_rest_goes_on(
    flight_canon: CanonModel,
) -> None:
    subtree = CanonGraph(flight_canon).subtree(
        ["nope", "polar-stall", "stall-speed", "aircraft-mass"]
    )
    assert [e.code for e in subtree.errors] == [
        "unknown_quantity",
        "non_scalar_result",
        "not_requestable",
    ]
    assert [r.slug for r in subtree.requested] == ["calc:stall-speed"]
    assert ids(subtree) == ["stall-speed.clean"]


def test_a_non_scalar_request_alone_leaves_the_subtree_empty(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["polar-stall"])
    assert subtree.nodes == ()
    assert subtree.layers == ()
    assert subtree.leaf_inputs == ()


def test_a_quantity_requested_twice_in_two_spellings_counts_once(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed", "calc:stall-speed"])
    assert [r.slug for r in subtree.requested] == ["calc:stall-speed"]


def test_the_producer_of_a_requested_quantity(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed"])
    assert subtree.producer_of("stall-speed") == STALL_CLEAN
    assert subtree.producer_of("calc:stall-speed") == STALL_CLEAN


def test_a_diamond_runs_its_arms_in_one_layer() -> None:
    model = model_of(
        {s: quantity("input" if s == "a" else "derived") for s in "abcd"},
        {
            "f-b": formula({"x": "a"}, {"y": "b"}),
            "f-c": formula({"x": "a"}, {"y": "c"}),
            "f-d": formula({"p": "b", "q": "c"}, {"y": "d"}),
        },
    )
    subtree = CanonGraph(model).subtree(["d"])
    assert [[n.formula for n in layer] for layer in subtree.layers] == [
        ["calc:f-b", "calc:f-c"],
        ["calc:f-d"],
    ]


def test_a_cycle_is_a_model_error_naming_its_path() -> None:
    model = model_of(
        {"a": quantity("derived"), "b": quantity("derived"), "c": quantity("derived")},
        {
            "f-a": formula({"x": "c"}, {"y": "a"}),
            "f-b": formula({"x": "a"}, {"y": "b"}),
            "f-c": formula({"x": "b"}, {"y": "c"}),
        },
    )
    with pytest.raises(
        GraphModelError,
        match=r"cycle: calc:f-a.default -> calc:f-b.default -> calc:f-c.default -> calc:f-a.default",
    ):
        CanonGraph(model).subtree(["a"])


def test_a_node_reading_its_own_output_is_a_cycle() -> None:
    model = model_of({"a": quantity("derived")}, {"f": formula({"x": "a"}, {"y": "a"})})
    with pytest.raises(GraphModelError, match=r"cycle: calc:f.default -> calc:f.default"):
        CanonGraph(model).subtree(["a"])
