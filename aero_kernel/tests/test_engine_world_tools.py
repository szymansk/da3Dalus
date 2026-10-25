"""Provenance names the tools of the worlds that ran, not the tool of the formula (#1221)."""

from collections.abc import Mapping
from typing import Any

import pytest
from aero_kernel.build import Build
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.graph import CanonGraph
from aero_kernel.registry import Registry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput, ComputeRequest, ComputeResult
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.tests.formula_builders import StubAtmosphere, solvers_with
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from aero_kernel.tests.wing_builders import airplane_document
from pydantic import JsonValue

pytestmark = pytest.mark.asyncio


class StubAvl(AvlAdapter):
    """An AVL adapter that reports a version and settings and is never run."""

    def __init__(self) -> None:
        super().__init__(SolverRuntime())

    def tool_versions(self) -> dict[str, str]:
        return {"avl-binary": "9.9"}

    def settings(self) -> dict[str, JsonValue]:
        return {"avl_nspan": 7}


def taxonomy(alpha: str, beta: str) -> dict[str, Any]:
    tools = sorted({alpha, beta, "AVL"})
    return {
        "tools": [{"id": tool, "name": tool} for tool in tools],
        "worlds": [{"id": "alpha", "tool": alpha}, {"id": "beta", "tool": beta}],
    }


async def provenance_of(alpha: str, beta: str) -> ComputeResult:
    """Run an AVL-tool formula whose worlds use ``alpha`` and ``beta`` tools."""
    model = model_of(
        {"aircraft-mass": quantity("input", unit="kg"), "np-q": quantity("derived")},
        {
            "np": formula(
                {"m": "aircraft-mass"},
                {"o": "np-q"},
                tool="AVL",
                uncertainty="interval",
                worlds=["alpha", "beta"],
            )
        },
        taxonomy=taxonomy(alpha, beta),
    )
    registry = Registry()

    async def np(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"o": 1.0}

    registry.formula("np")(np)
    build = Build(
        model=model,
        graph=CanonGraph(model),
        digest="sha256:" + "ab" * 32,
        registry=registry,
        report=registry.check_traceability(model),
    )
    aircraft = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({}, {"aerosandbox": "1.2.3"}), avl=StubAvl())
    return await evaluate(build, aircraft, ComputeRequest(quantities=("np-q",)), solvers=solvers)


async def test_a_world_that_used_avl_lists_the_avl_version_and_settings() -> None:
    provenance = (await provenance_of("AVL", "AVL")).provenance
    assert provenance.tool_versions == {"avl-binary": "9.9"}
    assert provenance.solver_settings == {"avl_nspan": 7}


async def test_the_tool_of_the_formula_is_not_listed_when_no_world_used_it() -> None:
    provenance = (await provenance_of("ATM", "APP")).provenance
    assert provenance.tool_versions == {"aerosandbox": "1.2.3"}
    assert provenance.solver_settings == {}


async def test_every_world_that_ran_contributes_its_tool() -> None:
    provenance = (await provenance_of("ATM", "AVL")).provenance
    assert provenance.tool_versions == {"aerosandbox": "1.2.3", "avl-binary": "9.9"}


async def test_worlds_of_pure_tools_leave_the_provenance_empty() -> None:
    provenance = (await provenance_of("APP", "APP")).provenance
    assert (provenance.tool_versions, provenance.solver_settings) == ({}, {})
