"""Run times per quantity: the result models and the chain arithmetic (ARCHITECTURE ch. 8.3)."""

import math

import pytest
from aero_kernel.schema import (
    QuantityResult,
    QuantityStatus,
    Reason,
    ReasonCode,
    TimeBounds,
    Timing,
)
from aero_kernel.timing import chain_timing, run_bounds
from pydantic import ValidationError


def close(actual: float | tuple[float, ...], expected: float | tuple[float, ...]) -> bool:
    """Whether two times or tuples of times agree up to rounding."""
    a = actual if isinstance(actual, tuple) else (actual,)
    e = expected if isinstance(expected, tuple) else (expected,)
    return len(a) == len(e) and all(
        math.isclose(x, y, abs_tol=1e-12) for x, y in zip(a, e, strict=True)
    )


def exact(seconds: float) -> TimeBounds:
    return TimeBounds(lower=seconds, upper=seconds)


# --- TimeBounds ---------------------------------------------------------------------------------


def test_bounds_may_be_equal() -> None:
    bounds = exact(0.25)
    assert close((bounds.lower, bounds.upper), (0.25, 0.25))


def test_a_lower_bound_above_the_upper_one_is_rejected() -> None:
    with pytest.raises(ValidationError, match="lower bound must not exceed the upper bound"):
        TimeBounds(lower=2.0, upper=1.0)


@pytest.mark.parametrize("bad", [-0.001, math.nan, math.inf])
def test_a_negative_or_non_finite_time_is_rejected(bad: float) -> None:
    with pytest.raises(ValidationError):
        TimeBounds(lower=0.0, upper=bad)


def test_bounds_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TimeBounds.model_validate({"lower": 0.0, "upper": 1.0, "unit": "s"})


# --- Timing -------------------------------------------------------------------------------------


def test_the_total_is_before_plus_own() -> None:
    timing = Timing(
        own_s=TimeBounds(lower=1.0, upper=3.0),
        before_s=TimeBounds(lower=4.0, upper=6.0),
        total_s=TimeBounds(lower=5.0, upper=9.0),
    )
    assert close(timing.total_s.upper, 9.0)


def test_a_total_that_is_not_before_plus_own_is_rejected() -> None:
    one, three = exact(1.0), exact(3.0)
    with pytest.raises(ValidationError, match="total_s must be before_s plus own_s"):
        Timing(own_s=one, before_s=one, total_s=three)


def test_of_builds_the_total() -> None:
    timing = Timing.of(
        own=TimeBounds(lower=1.0, upper=3.0), before=TimeBounds(lower=4.0, upper=6.0)
    )
    assert close((timing.total_s.lower, timing.total_s.upper), (5.0, 9.0))


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (QuantityStatus.NOT_APPLICABLE, ReasonCode.CONDITION_NOT_MET),
        (QuantityStatus.SKIPPED, ReasonCode.LONG_RUN_NOT_INCLUDED),
    ],
)
def test_a_quantity_whose_formula_did_not_run_carries_no_timing(
    status: QuantityStatus, code: ReasonCode
) -> None:
    timing = Timing.of(own=exact(0.0), before=exact(0.0))
    reason = Reason(code=code, message="did not run")
    with pytest.raises(ValidationError, match="must not carry a timing"):
        QuantityResult(slug="q", status=status, reason=reason, timing=timing)


def test_an_ok_quantity_carries_its_timing_through_json() -> None:
    timing = Timing.of(own=exact(0.5), before=TimeBounds(lower=1.0, upper=2.0))
    result = QuantityResult(
        slug="q",
        unit="m",
        status=QuantityStatus.OK,
        value=1.0,
        tool="T",
        application="a",
        timing=timing,
    )
    assert QuantityResult.model_validate_json(result.model_dump_json()).timing == timing


# --- run_bounds ---------------------------------------------------------------------------------


def test_one_run_gives_equal_bounds() -> None:
    bounds = run_bounds([0.5])
    assert close((bounds.lower, bounds.upper), (0.5, 0.5))


def test_several_world_runs_give_the_longest_run_and_the_sum() -> None:
    bounds = run_bounds([0.5, 2.0, 1.0])
    assert close((bounds.lower, bounds.upper), (2.0, 3.5))


def test_no_run_has_no_bounds() -> None:
    with pytest.raises(ValueError, match="at least one run"):
        run_bounds([])


# --- chain_timing -------------------------------------------------------------------------------

# a diamond: a -> b, a -> c, b -> d, c -> d
DIAMOND = {"a": (), "b": ("a",), "c": ("a",), "d": ("b", "c")}
OWN = {"a": exact(1.0), "b": exact(2.0), "c": exact(3.0), "d": exact(0.5)}


def test_a_node_without_predecessors_has_nothing_before_it() -> None:
    timing = chain_timing("a", OWN, DIAMOND)
    assert close((timing.before_s.lower, timing.before_s.upper), (0.0, 0.0))
    assert close((timing.total_s.lower, timing.total_s.upper), (1.0, 1.0))


def test_a_shared_upstream_node_is_counted_once_in_the_sum() -> None:
    timing = chain_timing("d", OWN, DIAMOND)
    assert close(timing.before_s.upper, 6.0)  # a + b + c, a once


def test_the_lower_bound_is_the_longest_path_through_the_ancestors() -> None:
    timing = chain_timing("d", OWN, DIAMOND)
    assert close(timing.before_s.lower, 4.0)  # a then c
    assert close((timing.total_s.lower, timing.total_s.upper), (4.5, 6.5))
    assert close((timing.own_s.lower, timing.own_s.upper), (0.5, 0.5))


def test_world_runs_enter_the_path_by_their_lower_and_the_sum_by_their_upper_bound() -> None:
    own = {**OWN, "c": TimeBounds(lower=1.5, upper=4.5)}
    timing = chain_timing("d", own, DIAMOND)
    assert close(timing.before_s.lower, 3.0)  # a then b (2.0) beats a then c (1.5)
    assert close(timing.before_s.upper, 7.5)


def test_nodes_outside_the_ancestors_do_not_count() -> None:
    timing = chain_timing("b", OWN, DIAMOND)
    assert close((timing.before_s.lower, timing.before_s.upper), (1.0, 1.0))
