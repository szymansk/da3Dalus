"""Tests of the formula ``Context`` (ARCHITECTURE ch. 8.12)."""

import pytest
from aero_kernel.context import Context, Solvers
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers.atmosphere import AtmosphereAdapter

SOLVERS = Solvers(atmosphere=AtmosphereAdapter(SolverRuntime()))


def test_warn_builds_the_catalogue_warning_with_the_origin() -> None:
    context = Context(origin="stall-speed", solvers=SOLVERS)
    context.warn("precondition_unchecked", "Not checked.", {"parameter": "rho"})
    (warning,) = context.warnings
    assert warning.severity is WarningSeverity.PRACTICE
    assert (warning.origin, warning.world, warning.detail) == (
        "stall-speed",
        None,
        {"parameter": "rho"},
    )


def test_the_context_carries_the_solvers_and_the_warnings_only() -> None:
    context = Context(origin="x", solvers=SOLVERS)
    assert context.solvers is SOLVERS
    assert context.solvers.atmosphere is SOLVERS.atmosphere
    assert not hasattr(context, "world")
    assert not hasattr(context, "request")


def test_an_uncatalogued_code_raises() -> None:
    with pytest.raises(ValueError, match="catalogue"):
        Context(origin="x", solvers=SOLVERS).warn("not_a_code", "x")


def test_warnings_come_back_in_order_with_their_exact_text() -> None:
    context = Context(origin="x", solvers=SOLVERS)
    context.warn("precondition_unchecked", "first")
    context.warn("postcondition_unchecked", "second", {"k": 1})
    assert [(w.code, w.message, w.detail) for w in context.warnings] == [
        ("precondition_unchecked", "first", {}),
        ("postcondition_unchecked", "second", {"k": 1}),
    ]


def test_the_returned_warnings_are_a_snapshot() -> None:
    context = Context(origin="x", solvers=SOLVERS)
    context.warn("precondition_unchecked", "first")
    snapshot = context.warnings
    context.warn("precondition_unchecked", "second")
    assert len(snapshot) == 1
    assert len(context.warnings) == 2
