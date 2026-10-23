"""Which failure of several world assignments is reported, and the world label (ch. 8.13)."""

# pyright: reportPrivateUsage=false

import pytest
from aero_kernel.engine import _labelled, _merge_worlds, _NodeRun
from aero_kernel.errors import ErrorCategory, KernelError
from aero_kernel.graph import NodeOutcome
from aero_kernel.schema import QuantityResult, QuantityStatus

# (code, category) of the failures the order of ch. 8.13 ranks.
NOT_IMPLEMENTED = ("not_implemented", ErrorCategory.NOT_IMPLEMENTED)
UPSTREAM = ("upstream_failed", ErrorCategory.UPSTREAM_FAILED)
MISSING = ("missing_input", ErrorCategory.INVALID_INPUT)
COMPUTED = ("not_converged", ErrorCategory.NOT_CONVERGED)


def failure(code_and_category: tuple[str, ErrorCategory], world: str | None = None) -> KernelError:
    code, category = code_and_category
    extra: dict[str, object] = {}
    if category is ErrorCategory.UPSTREAM_FAILED:
        extra = {
            "retryable": False,
            "escalate": False,
            "detail": {"causes": [{"quantity": "x", "code": "missing_input"}]},
        }
    return KernelError(
        code=code,
        category=category,
        message=f"{code} message",
        hint="a hint",
        world=world,
        **extra,  # type: ignore[arg-type]
    )


def failed(code_and_category: tuple[str, ErrorCategory], key: str) -> QuantityResult:
    """An error result whose message names the assignment it came from."""
    error = failure(code_and_category).model_copy(update={"message": f"from {key}"})
    return QuantityResult(slug="q", unit=None, status=QuantityStatus.ERROR, error=error)


def merged(*worlds: tuple[str, tuple[str, ErrorCategory], bool]) -> KernelError:
    """The reported error of assignments (key, failure, whether the formula raised it)."""
    result = _merge_worlds(
        "q", None, [(key, failed(f, key), computed) for key, f, computed in worlds]
    )
    assert result.error is not None
    return result.error


def test_upstream_failed_beats_a_computed_failure_even_when_the_computed_key_sorts_first() -> None:
    error = merged(("f=alpha", COMPUTED, True), ("f=gamma", UPSTREAM, False))
    assert (error.code, error.message) == ("upstream_failed", "from f=gamma")


def test_upstream_failed_beats_missing_input_and_not_implemented_beats_missing_input() -> None:
    first = merged(("f=alpha", MISSING, False), ("f=gamma", UPSTREAM, False))
    assert first.code == "upstream_failed"
    second = merged(("f=alpha", MISSING, False), ("f=gamma", NOT_IMPLEMENTED, False))
    assert second.code == "not_implemented"
    third = merged(("f=alpha", UPSTREAM, False), ("f=gamma", NOT_IMPLEMENTED, False))
    assert third.code == "not_implemented"


def test_the_engines_missing_input_beats_a_computed_failure_but_a_raised_one_does_not() -> None:
    engines = merged(("f=alpha", COMPUTED, True), ("f=gamma", MISSING, False))
    assert engines.code == "missing_input"
    raised = merged(("f=alpha", COMPUTED, True), ("f=gamma", MISSING, True))
    assert (raised.code, raised.message) == ("not_converged", "from f=alpha")  # both row 8


def test_with_equal_rows_the_first_key_is_reported() -> None:
    error = merged(("f=beta", COMPUTED, True), ("f=alpha", COMPUTED, True))
    assert (error.code, error.message) == ("not_converged", "from f=alpha")


def test_an_error_that_already_names_a_world_keeps_it() -> None:
    error = failure(COMPUTED, world="f=textbook")
    run = _NodeRun(
        outcome=NodeOutcome(status=QuantityStatus.ERROR, error=error),
        anchor="q",
        error_for=lambda _slug: error,
    )
    labelled = _labelled(run, "f=pappas")
    assert labelled.outcome.error is not None
    assert labelled.outcome.error.world == "f=textbook"
    assert labelled.error_for is not None
    assert labelled.error_for("q").world == "f=textbook"


@pytest.mark.parametrize("key", ["f=pappas"])
def test_an_error_without_a_world_gets_the_runs_world(key: str) -> None:
    error = failure(COMPUTED)
    run = _NodeRun(
        outcome=NodeOutcome(status=QuantityStatus.ERROR, error=error),
        anchor="q",
        error_for=lambda _slug: error,
    )
    labelled = _labelled(run, key)
    assert labelled.outcome.error is not None
    assert labelled.outcome.error.world == key
