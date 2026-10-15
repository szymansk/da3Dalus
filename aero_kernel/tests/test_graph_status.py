"""Status precedence and cost class over the graph (ARCHITECTURE ch. 8.13, 8.7, test Q26)."""

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import CanonGraph, NodeId, NodeOutcome, Propagated, Subtree
from aero_kernel.schema import QuantityStatus, ReasonCode
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from pydantic import ValidationError

OK = NodeOutcome(status=QuantityStatus.OK)
SKIPPED = NodeOutcome(status=QuantityStatus.SKIPPED)
NOT_APPLICABLE = NodeOutcome(status=QuantityStatus.NOT_APPLICABLE)


def failed(quantity_slug: str, code: str = "not_converged") -> NodeOutcome:
    category = ErrorCategory(code)
    error = KernelError(
        code=code, category=category, quantity=quantity_slug, message="failed", hint="retry"
    )
    return NodeOutcome(status=QuantityStatus.ERROR, error=error)


def node_id(slug: str) -> NodeId:
    return NodeId(formula=f"calc:{slug}", application="default")


def diamond() -> Subtree:
    model = model_of(
        {s: quantity("input" if s == "a" else "derived") for s in "abcd"},
        {
            "f-b": formula({"x": "a"}, {"y": "b"}),
            "f-c": formula({"x": "a"}, {"y": "c"}),
            "f-d": formula({"p": "b", "q": "c"}, {"y": "d"}),
        },
    )
    return CanonGraph(model).subtree(["d"])


def run(b: NodeOutcome, c: NodeOutcome, world: str | None = None) -> Propagated | None:
    outcomes = {node_id("f-b"): b, node_id("f-c"): c}
    return diamond().propagate(node_id("f-d"), outcomes, quantity="d", world=world)


def test_an_outcome_carries_an_error_exactly_with_status_error() -> None:
    with pytest.raises(ValidationError, match="error"):
        NodeOutcome(status=QuantityStatus.ERROR)
    error = failed("b").error
    with pytest.raises(ValidationError, match="error"):
        NodeOutcome(status=QuantityStatus.OK, error=error)


def test_all_predecessors_ok_means_no_propagation() -> None:
    assert run(OK, OK) is None


def test_a_node_without_predecessors_never_propagates() -> None:
    assert diamond().propagate(node_id("f-b"), {}, quantity="b") is None


def test_an_error_gives_upstream_failed_with_the_cause() -> None:
    propagated = run(failed("b"), OK, world="u1=a")
    assert propagated is not None
    assert propagated.status is QuantityStatus.ERROR
    assert propagated.reason is None
    error = propagated.error
    assert error is not None
    assert error.category is ErrorCategory.UPSTREAM_FAILED
    assert (error.quantity, error.formula, error.application, error.world) == (
        "d",
        "f-d",
        "default",
        "u1=a",
    )
    assert error.detail["causes"] == [{"quantity": "b", "code": "not_converged"}]
    assert error.retryable is True


def test_two_failed_predecessors_list_both_causes() -> None:
    propagated = run(failed("b"), failed("c", "tool_unavailable"))
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.detail["causes"] == [
        {"quantity": "b", "code": "not_converged"},
        {"quantity": "c", "code": "tool_unavailable"},
    ]
    assert propagated.error.retryable is False


@pytest.mark.parametrize("other", [OK, SKIPPED, NOT_APPLICABLE])
def test_an_error_dominates_every_other_status(other: NodeOutcome) -> None:
    propagated = run(other, failed("c"))
    assert propagated is not None
    assert propagated.status is QuantityStatus.ERROR


@pytest.mark.parametrize("other", [OK, SKIPPED, NOT_APPLICABLE])
def test_skipped_dominates_not_applicable_and_ok(other: NodeOutcome) -> None:
    propagated = run(SKIPPED, other)
    assert propagated is not None
    assert propagated.status is QuantityStatus.SKIPPED
    assert propagated.reason is not None
    assert propagated.reason.code is ReasonCode.DEPENDS_ON_SKIPPED
    assert propagated.error is None
    assert "`b`" in propagated.reason.message


def test_not_applicable_propagates_when_nothing_stronger_is_there() -> None:
    propagated = run(OK, NOT_APPLICABLE)
    assert propagated is not None
    assert propagated.status is QuantityStatus.NOT_APPLICABLE
    assert propagated.reason is not None
    assert propagated.reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE
    assert "`c`" in propagated.reason.message


def test_a_predecessor_the_node_does_not_read_does_not_propagate() -> None:
    outcomes = {node_id("f-b"): OK, node_id("f-c"): OK, node_id("f-x"): failed("x")}
    assert diamond().propagate(node_id("f-d"), outcomes, quantity="d") is None


def test_a_missing_outcome_of_a_read_predecessor_is_a_key_error() -> None:
    with pytest.raises(KeyError):
        diamond().propagate(node_id("f-d"), {node_id("f-b"): OK}, quantity="d")


def test_an_optional_read_of_a_computed_quantity_propagates_like_any_other() -> None:
    model = model_of(
        {"a": quantity("input"), "b": quantity("derived"), "c": quantity("derived")},
        {
            "f-b": formula({"x": "a"}, {"y": "b"}),
            "f-c": formula({"p": "b"}, {"y": "c"}, optional=["p"]),
        },
    )
    subtree = CanonGraph(model).subtree(["c"])
    propagated = subtree.propagate(node_id("f-c"), {node_id("f-b"): NOT_APPLICABLE}, quantity="c")
    assert propagated is not None
    assert propagated.status is QuantityStatus.NOT_APPLICABLE


def test_the_fixture_chain_propagates_from_the_landing_stall(flight_canon: CanonModel) -> None:
    subtree = CanonGraph(flight_canon).subtree(["approach-speed"])
    landing = NodeId(formula="calc:stall-speed", application="landing")
    approach = NodeId(formula="calc:speed-from-stall-margin", application="approach")
    propagated = subtree.propagate(
        approach, {landing: failed("stall-speed-landing")}, quantity="approach-speed"
    )
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.formula == "speed-from-stall-margin"
    assert propagated.error.application == "approach"


def test_long_runs_are_the_nodes_of_cost_class_minutes(flight_canon: CanonModel) -> None:
    graph = CanonGraph(flight_canon)
    mass = NodeId(formula="calc:max-mass-level-flight", application="default")
    assert graph.subtree(["max-mass-level-flight", "stall-speed"]).long_run_nodes() == (mass,)
    assert graph.subtree(["stall-speed"]).long_run_nodes() == ()
