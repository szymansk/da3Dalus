"""Graph layer over the canon model (ARCHITECTURE ch. 5, 6, 8.13)."""

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import CanonGraph, GraphModelError, NodeId, Resolved
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
