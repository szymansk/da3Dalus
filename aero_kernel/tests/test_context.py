"""Tests of the formula ``Context`` (ARCHITECTURE ch. 8.12)."""

import pytest
from aero_kernel.context import Context
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import WarningSeverity
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.tests.formula_builders import StubAtmosphere, solvers_with

SOLVERS = solvers_with()


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


def test_tool_versions_of_an_adapter_tool_are_the_adapters() -> None:
    solvers = solvers_with(atmosphere=StubAtmosphere({}, {"aerosandbox": "1.2.3"}))
    assert solvers.tool_versions_of("ATM") == {"aerosandbox": "1.2.3"}


@pytest.mark.parametrize("tool", ["APP", "KAT", "APC"])
def test_a_pure_tool_has_no_version(tool: str) -> None:
    assert SOLVERS.tool_versions_of(tool) == {}


@pytest.mark.parametrize("tool", ["AB", "AVL", "OPT"])
def test_a_tool_without_an_adapter_is_a_defect_not_an_empty_version(tool: str) -> None:
    with pytest.raises(ValueError, match=tool):
        SOLVERS.tool_versions_of(tool)


def test_the_geometry_tool_reports_the_versions_of_its_adapter() -> None:
    """GEO has an adapter (ch. 8.8), so it is no pure tool: it reports aerosandbox like ATM."""

    class Versioned(GeometryAdapter):
        def tool_versions(self) -> dict[str, str]:
            return {"aerosandbox": "3.2.1"}

    solvers = solvers_with(geometry=Versioned(SolverRuntime()))
    assert solvers.tool_versions_of("GEO") == {"aerosandbox": "3.2.1"}
    assert solvers.geometry.tool == "GEO"
