"""Status precedence and cost class over the graph (ARCHITECTURE ch. 8.13, 8.7, test Q26)."""

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.errors import ErrorCategory, KernelError, aggregate_upstream
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


def test_a_nested_upstream_failure_reports_the_root_cause_only() -> None:
    model = model_of(
        {"i": quantity("input"), "b": quantity("derived"), "d": quantity("derived")},
        {"f-b": formula({"x": "i"}, {"y": "b"}), "f-d": formula({"p": "b"}, {"y": "d"})},
    )
    root = KernelError(
        code="tool_unavailable",
        category=ErrorCategory.TOOL_UNAVAILABLE,
        quantity="a",
        message="m",
        hint="h",
    )
    upstream = NodeOutcome(
        status=QuantityStatus.ERROR, error=aggregate_upstream([root], quantity="b")
    )
    propagated = (
        CanonGraph(model)
        .subtree(["d"])
        .propagate(node_id("f-d"), {node_id("f-b"): upstream}, quantity="d")
    )
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.detail["causes"] == [{"quantity": "a", "code": "tool_unavailable"}]
    assert propagated.error.escalate is True


def test_an_error_propagates_through_an_optional_read() -> None:
    model = model_of(
        {"a": quantity("input"), "b": quantity("derived"), "c": quantity("derived")},
        {
            "f-b": formula({"x": "a"}, {"y": "b"}),
            "f-c": formula({"p": "b"}, {"y": "c"}, optional=["p"]),
        },
    )
    propagated = (
        CanonGraph(model)
        .subtree(["c"])
        .propagate(node_id("f-c"), {node_id("f-b"): failed("b")}, quantity="c")
    )
    assert propagated is not None
    assert propagated.status is QuantityStatus.ERROR
    assert propagated.error is not None
    assert propagated.error.category is ErrorCategory.UPSTREAM_FAILED


def other_chain() -> Subtree:
    """The diamond of the status tests, in the namespace ``other``."""
    model = model_of(
        {s: quantity("input" if s == "a" else "derived") for s in "abcd"},
        {
            "f-b": formula({"x": "a"}, {"y": "b"}, namespace="other"),
            "f-c": formula({"x": "a"}, {"y": "c"}, namespace="other"),
            "f-d": formula({"p": "b", "q": "c"}, {"y": "d"}, namespace="other"),
        },
        namespace="other",
    )
    return CanonGraph(model).subtree(["other:d"])


def other_id(slug: str) -> NodeId:
    return NodeId(formula=f"other:{slug}", application="default")


def test_a_slug_of_another_namespace_is_written_qualified_in_messages_and_errors() -> None:
    subtree = other_chain()
    skipped = subtree.propagate(
        other_id("f-d"), {other_id("f-b"): SKIPPED, other_id("f-c"): OK}, quantity="other:d"
    )
    assert skipped is not None
    assert skipped.reason is not None
    assert "`other:b`" in skipped.reason.message
    errored = subtree.propagate(
        other_id("f-d"),
        {other_id("f-b"): failed("other:b"), other_id("f-c"): OK},
        quantity="other:d",
    )
    assert errored is not None
    assert errored.error is not None
    assert errored.error.formula == "other:f-d"


def test_a_calc_slug_is_written_bare_in_messages_and_errors() -> None:
    propagated = run(failed("b"), OK)
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.formula == "f-d"


def two_outputs() -> Subtree:
    model = model_of(
        {s: quantity("input" if s == "a" else "derived") for s in ("a", "p", "q", "d")},
        {
            "f-two": formula({"x": "a"}, {"y": "p", "z": "q"}),
            "f-d": formula({"u": "p", "v": "q"}, {"y": "d"}),
        },
    )
    return CanonGraph(model).subtree(["d"])


def test_the_causes_name_the_quantities_the_node_reads_not_the_node_error_quantity() -> None:
    outcomes = {node_id("f-two"): failed("p")}
    propagated = two_outputs().propagate(node_id("f-d"), outcomes, quantity="d")
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.detail["causes"] == [
        {"quantity": "p", "code": "not_converged"},
        {"quantity": "q", "code": "not_converged"},
    ]


def test_a_dependent_of_one_output_is_told_that_output() -> None:
    model = model_of(
        {s: quantity("input" if s == "a" else "derived") for s in ("a", "p", "q", "d")},
        {
            "f-two": formula({"x": "a"}, {"y": "p", "z": "q"}),
            "f-d": formula({"v": "q"}, {"y": "d"}),
        },
    )
    subtree = CanonGraph(model).subtree(["d"])
    propagated = subtree.propagate(node_id("f-d"), {node_id("f-two"): failed("p")}, quantity="d")
    assert propagated is not None
    assert propagated.error is not None
    assert propagated.error.detail["causes"] == [{"quantity": "q", "code": "not_converged"}]


def test_an_own_long_run_skip_is_skipped_with_its_reason() -> None:
    propagated = diamond().propagate(
        node_id("f-d"), {node_id("f-b"): OK, node_id("f-c"): OK}, quantity="d", skip_long_run=True
    )
    assert propagated is not None
    assert propagated.status is QuantityStatus.SKIPPED
    assert propagated.reason is not None
    assert propagated.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED


def test_precedence_is_error_then_own_skip_then_skipped_then_not_applicable() -> None:
    subtree = diamond()

    def status(b: NodeOutcome, c: NodeOutcome, *, skip: bool) -> Propagated | None:
        outcomes = {node_id("f-b"): b, node_id("f-c"): c}
        return subtree.propagate(node_id("f-d"), outcomes, quantity="d", skip_long_run=skip)

    errored = status(failed("b"), OK, skip=True)
    assert errored is not None
    assert errored.status is QuantityStatus.ERROR
    own = status(NOT_APPLICABLE, OK, skip=True)
    assert own is not None
    assert own.reason is not None
    assert own.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
    inherited = status(SKIPPED, NOT_APPLICABLE, skip=False)
    assert inherited is not None
    assert inherited.reason is not None
    assert inherited.reason.code is ReasonCode.DEPENDS_ON_SKIPPED


@pytest.mark.parametrize(
    ("b", "skip"),
    [
        (failed("b"), False),
        (SKIPPED, False),
        (NOT_APPLICABLE, False),
        (OK, True),
    ],
    ids=["error", "skipped", "not-applicable", "long-run"],
)
def test_a_propagation_can_be_addressed_to_another_quantity(b: NodeOutcome, skip: bool) -> None:
    outcomes = {node_id("f-b"): b, node_id("f-c"): OK}
    propagated = diamond().propagate(node_id("f-d"), outcomes, quantity="d", skip_long_run=skip)
    assert propagated is not None
    other = propagated.addressed_to("sibling")
    texts = [
        other.error.message if other.error else "",
        other.reason.message if other.reason else "",
    ]
    assert any("`sibling`" in text for text in texts)
    assert not any("`d`" in text for text in texts)
    assert other.status is propagated.status
    first = [
        propagated.error.message if propagated.error else "",
        propagated.reason.message if propagated.reason else "",
    ]
    assert any("`d`" in text for text in first)
    if other.error is not None:
        assert other.error.quantity == "sibling"
        assert other.error.detail == propagated.error.detail  # type: ignore[union-attr]  # same causes
