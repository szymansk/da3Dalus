"""Tests of the formula ``Context`` (ARCHITECTURE ch. 8.12)."""

import pytest
from aero_kernel.context import Context
from aero_kernel.schema import WarningSeverity


def test_warn_builds_the_catalogue_warning_with_the_origin() -> None:
    context = Context(origin="stall-speed")
    context.warn("precondition_unchecked", "Not checked.", {"parameter": "rho"})
    (warning,) = context.warnings
    assert warning.severity is WarningSeverity.PRACTICE
    assert (warning.origin, warning.world, warning.detail) == (
        "stall-speed",
        None,
        {"parameter": "rho"},
    )


def test_the_context_carries_nothing_but_warn() -> None:
    context = Context(origin="x")
    assert not hasattr(context, "world")
    assert not hasattr(context, "solvers")


def test_an_uncatalogued_code_raises() -> None:
    with pytest.raises(ValueError, match="catalogue"):
        Context(origin="x").warn("not_a_code", "x")
