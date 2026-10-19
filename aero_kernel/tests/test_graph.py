"""Graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13)."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from aero_kernel import graph
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


@pytest.mark.parametrize("role", ["derived", "output"])
def test_a_computed_quantity_nobody_produces_is_a_model_error_at_construction(role: str) -> None:
    with pytest.raises(GraphModelError, match=r"calc:a.*no producer"):
        CanonGraph(model_of({"a": quantity(role)}, {}))


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
        CanonGraph(model)


def test_a_node_reading_its_own_output_is_a_cycle() -> None:
    model = model_of({"a": quantity("derived")}, {"f": formula({"x": "a"}, {"y": "a"})})
    with pytest.raises(GraphModelError, match=r"cycle: calc:f.default -> calc:f.default"):
        CanonGraph(model)


def test_producer_of_an_unrequested_quantity_is_a_key_error(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall-speed", "polar-stall"])
    for slug in ("approach-speed", "polar-stall"):
        with pytest.raises(KeyError):
            subtree.producer_of(slug)


def test_a_parameter_declared_optional_is_an_optional_read(flight_canon: CanonModel) -> None:
    node = CanonGraph(flight_canon).node(
        NodeId(formula="calc:airplane-configuration", application="default")
    )
    assert {read.parameter: read.optional for read in node.reads} == {
        "airplane": False,
        "flap_deflection": True,
    }


_LAYERS_SCRIPT = """
import sys
from pathlib import Path
from aero_kernel.canon.load import load_canon_model
from aero_kernel.graph import CanonGraph

model = load_canon_model(Path(sys.argv[1]) / "tests" / "fixtures" / "flight_canon.json")
request = ["stall-speed", "neutral-point", "max-mass-level-flight", "roll-rate-cruise",
           "approach-speed", "stall-speed-landing"]
for layer in CanonGraph(model).subtree(request).layers:
    print([(n.formula, n.application) for n in layer])
"""


def test_the_layer_order_does_not_depend_on_the_hash_seed(package_root: Path) -> None:
    outputs = {
        subprocess.run(
            [sys.executable, "-c", _LAYERS_SCRIPT, str(package_root)],
            capture_output=True,
            check=True,
            cwd=package_root.parent,
            env={**os.environ, "PYTHONHASHSEED": str(seed)},
            text=True,
        ).stdout
        for seed in range(8)
    }
    assert len(outputs) == 1
    first_layer = next(iter(outputs)).splitlines()[0]
    assert first_layer.index("airplane-configuration") < first_layer.index("max-mass-level-flight")


def test_public_names_of_graph_are_pinned() -> None:
    assert sorted(graph.__all__) == [
        "CanonGraph",
        "Edge",
        "GraphModelError",
        "Node",
        "NodeId",
        "NodeOutcome",
        "PENDING_WHEN_TERMS",
        "Produce",
        "Propagated",
        "Read",
        "Resolved",
        "Subtree",
        "WhenFacts",
        "facts_from_geometry",
        "unmet_condition",
    ]


@pytest.mark.parametrize("request_slug", ["stall-speed", "calc:stall-speed"])
def test_the_resolved_quantity_keeps_the_spelling_of_the_request(
    flight_canon: CanonModel, request_slug: str
) -> None:
    resolved = CanonGraph(flight_canon).resolve(request_slug)
    assert isinstance(resolved, Resolved)
    assert resolved.requested == request_slug
    subtree = CanonGraph(flight_canon).subtree([request_slug])
    assert subtree.requested[0].requested == request_slug


def test_a_malformed_slug_is_an_unknown_quantity_with_the_raw_spelling(
    flight_canon: CanonModel,
) -> None:
    error = CanonGraph(flight_canon).resolve("Not A Slug")
    assert isinstance(error, KernelError)
    assert (error.code, error.quantity) == ("unknown_quantity", "Not A Slug")


def test_a_malformed_slug_is_reported_per_quantity_while_the_rest_resolves(
    flight_canon: CanonModel,
) -> None:
    subtree = CanonGraph(flight_canon).subtree(["stall_speed", "stall-speed"])
    assert [(e.code, e.quantity) for e in subtree.errors] == [("unknown_quantity", "stall_speed")]
    assert [r.requested for r in subtree.requested] == ["stall-speed"]


def test_a_rejected_request_echoes_the_raw_spelling_with_its_namespace(
    flight_canon: CanonModel,
) -> None:
    error = CanonGraph(flight_canon).resolve("calc:no-such-thing")
    assert isinstance(error, KernelError)
    assert error.quantity == "calc:no-such-thing"


@pytest.mark.parametrize(
    "pair", [("stall_speed", "calc:stall_speed"), ("Stall Speed", "calc:Stall Speed")]
)
def test_two_malformed_spellings_are_two_unknown_quantities(
    flight_canon: CanonModel, pair: tuple[str, str]
) -> None:
    subtree = CanonGraph(flight_canon).subtree(pair)
    assert [(e.code, e.quantity) for e in subtree.errors] == [
        ("unknown_quantity", pair[0]),
        ("unknown_quantity", pair[1]),
    ]
    assert subtree.requested == ()


# --- per_control_surface: one quantity, several applications of one formula ---------------------------------------


def multi_application_formula(quantity_slug: str = "b") -> dict[str, Any]:
    """A formula whose two applications both produce ``quantity_slug``."""
    base = formula({"x": "a"}, {"y": quantity_slug})
    application = base["applications"][0]
    base["applications"] = [
        {**application, "id": "first"},
        {**application, "id": "second"},
    ]
    return base


def per_surface_quantities(type_: str) -> dict[str, dict[str, Any]]:
    return {"a": quantity("input"), "b": quantity("output", type=type_)}


def test_two_applications_of_one_formula_may_produce_a_per_control_surface_quantity() -> None:
    model = model_of(
        per_surface_quantities("per_control_surface"), {"f": multi_application_formula()}
    )
    graph = CanonGraph(model)
    assert set(graph.node_ids) == {
        NodeId(formula="calc:f", application="first"),
        NodeId(formula="calc:f", application="second"),
    }


def test_two_applications_of_one_formula_producing_a_scalar_are_a_model_error() -> None:
    model = model_of(per_surface_quantities("scalar"), {"f": multi_application_formula()})
    with pytest.raises(GraphModelError, match=r"calc:b.*calc:f\.first.*calc:f\.second"):
        CanonGraph(model)


def test_two_formulas_producing_a_per_control_surface_quantity_are_a_model_error() -> None:
    model = model_of(
        per_surface_quantities("per_control_surface"),
        {"f1": formula({"x": "a"}, {"y": "b"}), "f2": formula({"x": "a"}, {"y": "b"})},
    )
    with pytest.raises(GraphModelError, match=r"calc:b.*calc:f1.*calc:f2"):
        CanonGraph(model)


def test_reading_a_quantity_with_several_producers_is_a_model_error() -> None:
    """Never pick one of them (ADR 0020): the importer forbids it, the graph refuses it as well."""
    model = model_of(
        {**per_surface_quantities("per_control_surface"), "c": quantity("output")},
        {"f": multi_application_formula(), "reader": formula({"v": "b"}, {"w": "c"})},
    )
    with pytest.raises(GraphModelError, match=r"calc:b.*several producers.*calc:reader"):
        CanonGraph(model)
