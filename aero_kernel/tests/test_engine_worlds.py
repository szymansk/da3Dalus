"""Method worlds in the engine (ARCHITECTURE ch. 8.13, A11, ADR 0027), on a fixture canon model."""

from collections.abc import Mapping
from typing import Any

import pytest
from aero_kernel.build import Build
from aero_kernel.cache import cache_key
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.graph import CanonGraph, NodeId
from aero_kernel.registry import CheckResult, Registry
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
)
from aero_kernel.tests.engine_builders import NO_SOLVERS
from aero_kernel.tests.graph_builders import formula, model_of, quantity
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

WORLDS = ["alpha", "beta", "gamma"]
VALUE = {"alpha": 10.0, "beta": 20.0, "gamma": 30.0}


def fixture_model() -> Any:
    """head (certain) -> unc (3 worlds) -> down -> join <- side (certain)."""
    return model_of(
        {
            "aircraft-mass": quantity("input", unit="kg", positive=True),
            "head-q": quantity("derived"),
            "np-q": quantity("derived"),
            "down-q": quantity("derived"),
            "side-q": quantity("derived"),
            "join-q": quantity("derived"),
        },
        {
            "head": formula({"m": "aircraft-mass"}, {"o": "head-q"}),
            "unc": formula(
                {"v": "head-q"},
                {"o": "np-q"},
                uncertainty="interval",
                worlds=WORLDS,
                preconditions=[{"id": "pre", "parameter": "v", "on_violation": "warning"}],
            ),
            "down": formula({"v": "np-q"}, {"o": "down-q"}),
            "side": formula({"m": "aircraft-mass"}, {"o": "side-q"}),
            "join": formula({"a": "down-q", "b": "side-q"}, {"o": "join-q"}),
        },
    )


class Probe:
    """The fixture formulas, their calls, and what each world does."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.fail: dict[str, FormulaError] = {}
        self.warn: set[str] = set()
        self.pre_calls: list[object] = []

    def registry(self) -> Registry:
        registry = Registry()

        async def head(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.calls.append(("head", ctx.world))
            return {"o": 1.0}

        async def unc(x: Inputs, ctx: Context) -> Mapping[str, object]:
            world = ctx.world
            assert world is not None
            self.calls.append(("unc", world))
            if world in self.warn:
                ctx.warn("precondition_unchecked", f"warned in {world}")
            if world in self.fail:
                raise self.fail[world]
            return {"o": VALUE[world]}

        async def down(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.calls.append(("down", ctx.world))
            value = x["v"]
            assert isinstance(value, float)
            return {"o": value + 1.0}

        async def side(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.calls.append(("side", ctx.world))
            return {"o": 7.0}

        async def join(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.calls.append(("join", ctx.world))
            a, b = x["a"], x["b"]
            assert isinstance(a, float)
            assert isinstance(b, float)
            return {"o": a + b}

        def pre(x: Mapping[str, object]) -> CheckResult:
            self.pre_calls.append(x["v"])
            return CheckResult(state="held", message="ok")

        for name, function in (
            ("head", head),
            ("unc", unc),
            ("down", down),
            ("side", side),
            ("join", join),
        ):
            registry.formula(name)(function)
        registry.precondition("unc", "pre")(pre)
        return registry


async def run(probe: Probe, *slugs: str, mass: bool = True) -> ComputeResult:
    model = fixture_model()
    registry = probe.registry()
    build = Build(
        model=model,
        graph=CanonGraph(model),
        digest="sha256:" + "ab" * 32,
        registry=registry,
        report=registry.check_traceability(model),
    )
    values = {"aircraft-mass": 2.0} if mass else {}
    aircraft = AircraftInput.model_validate({"airplane": airplane_document(), "values": values})
    return await evaluate(build, aircraft, ComputeRequest(quantities=slugs), solvers=NO_SOLVERS)


def only(result: ComputeResult) -> QuantityResult:
    (quantity_,) = result.quantities
    return quantity_


def count(probe: Probe, name: str) -> int:
    return sum(1 for called, _ in probe.calls if called == name)


async def test_uncertain_node_runs_once_per_world() -> None:
    probe = Probe()
    await run(probe, "np-q")
    assert sorted(str(w) for n, w in probe.calls if n == "unc") == WORLDS
    assert len(probe.pre_calls) == 3  # the precondition runs per world


async def test_a_node_outside_the_uncertain_subtree_runs_once_and_is_shared() -> None:
    probe = Probe()
    await run(probe, "join-q")
    assert (count(probe, "head"), count(probe, "side")) == (1, 1)
    assert (count(probe, "unc"), count(probe, "down"), count(probe, "join")) == (3, 3, 3)
    assert {w for n, w in probe.calls if n in ("head", "side")} == {None}


async def test_the_context_world_is_set_on_the_uncertain_formula_only() -> None:
    probe = Probe()
    await run(probe, "join-q")
    assert {w for n, w in probe.calls if n == "down"} == {None}
    assert {w for n, w in probe.calls if n == "join"} == {None}


async def test_the_interval_is_min_max_over_the_worlds() -> None:
    result = await run(Probe(), "np-q")
    quantity_ = only(result)
    assert quantity_.status is QuantityStatus.OK
    assert quantity_.value is None
    assert quantity_.interval is not None
    assert (quantity_.interval.min, quantity_.interval.max) == (10.0, 30.0)
    assert quantity_.interval.worlds == {
        "unc=alpha": 10.0,
        "unc=beta": 20.0,
        "unc=gamma": 30.0,
    }
    assert (quantity_.tool, quantity_.application, quantity_.unit) == ("APP", "default", "1")


async def test_a_downstream_quantity_carries_the_interval_per_assignment() -> None:
    interval = only(await run(Probe(), "join-q")).interval
    assert interval is not None
    assert interval.worlds == {"unc=alpha": 18.0, "unc=beta": 28.0, "unc=gamma": 38.0}


async def test_a_certain_quantity_is_a_plain_value() -> None:
    quantity_ = only(await run(Probe(), "side-q"))
    assert (quantity_.value, quantity_.interval) == (7.0, None)


def failing(code: str, category: ErrorCategory) -> FormulaError:
    return FormulaError(category, code, f"{code} message", "a hint")


async def test_a_failed_world_makes_the_quantity_an_error_never_a_narrower_interval() -> None:
    probe = Probe()
    probe.fail["beta"] = failing("not_converged", ErrorCategory.NOT_CONVERGED)
    quantity_ = only(await run(probe, "np-q"))
    assert quantity_.status is QuantityStatus.ERROR
    assert quantity_.interval is None
    assert quantity_.error is not None
    assert (quantity_.error.code, quantity_.error.world) == ("not_converged", "unc=beta")
    assert quantity_.error.detail["worlds_ok"] == {"unc=alpha": 10.0, "unc=gamma": 30.0}


async def test_a_downstream_node_of_a_failed_assignment_is_upstream_failed_there_only() -> None:
    probe = Probe()
    probe.fail["beta"] = failing("not_converged", ErrorCategory.NOT_CONVERGED)
    quantity_ = only(await run(probe, "join-q"))
    assert quantity_.error is not None
    assert quantity_.error.code == "upstream_failed"
    assert quantity_.error.world == "unc=beta"
    assert quantity_.error.detail["worlds_ok"] == {"unc=alpha": 18.0, "unc=gamma": 38.0}
    assert count(probe, "join") == 2  # not run in the failed assignment


async def test_the_reported_failure_is_ranked_by_the_row_of_the_run_not_by_its_code() -> None:
    """A missing_input a formula raises while computing is a computed failure (row 8), not the
    engine's row 5: with alpha not converged, gamma raising missing_input, both are row 8 and the
    first key (alpha) is reported."""
    probe = Probe()
    probe.fail["alpha"] = failing("not_converged", ErrorCategory.NOT_CONVERGED)
    probe.fail["gamma"] = failing("missing_input", ErrorCategory.INVALID_INPUT)
    error = only(await run(probe, "np-q")).error
    assert error is not None
    assert (error.code, error.world) == ("not_converged", "unc=alpha")
    tie = Probe()
    tie.fail["beta"] = failing("not_converged", ErrorCategory.NOT_CONVERGED)
    tie.fail["gamma"] = failing("invalid_input", ErrorCategory.INVALID_INPUT)
    error = only(await run(tie, "np-q")).error
    assert error is not None
    assert (error.code, error.world) == ("not_converged", "unc=beta")


async def test_a_shared_input_that_fails_fails_every_world_and_names_no_world() -> None:
    """No per-world inputs: head has no mass (row 5), so every unc assignment is upstream_failed
    (row 4). The cause is in no world: the error carries no world label and no world computed."""
    probe = Probe()
    error = only(await run(probe, "np-q", mass=False)).error
    assert error is not None
    assert (error.code, error.world) == ("upstream_failed", None)
    assert error.detail["worlds_ok"] == {}
    assert count(probe, "unc") == 0


async def test_a_failure_raised_alike_in_every_world_names_no_world() -> None:
    """The layout refusal of the neutral point is raised in each world with the same text: the cause
    is the airplane, not a method."""
    probe = Probe()
    for world in WORLDS:
        probe.fail[world] = failing("invalid_input", ErrorCategory.INVALID_INPUT)
    error = only(await run(probe, "np-q")).error
    assert error is not None
    assert (error.code, error.world) == ("invalid_input", None)
    assert error.detail["worlds_ok"] == {}


async def test_a_warning_carries_the_world_it_arose_in() -> None:
    probe = Probe()
    probe.warn.add("beta")
    quantity_ = only(await run(probe, "np-q"))
    (warning,) = quantity_.warnings
    assert (warning.code, warning.world, warning.origin) == (
        "precondition_unchecked",
        "unc=beta",
        "np-q",
    )


async def test_the_cache_key_is_per_assignment() -> None:
    subtree = CanonGraph(fixture_model()).subtree(["join-q"])
    unc = NodeId(formula="calc:unc", application="default")
    head = NodeId(formula="calc:head", application="default")
    keys = [key for key, _ in subtree.node_assignments(unc)]
    assert keys == ["unc=alpha", "unc=beta", "unc=gamma"]
    assert [key for key, _ in subtree.node_assignments(head)] == [None]
    digests = {
        cache_key(
            formula="calc:unc",
            application="default",
            world=key,
            inputs={"v": 1.0},
            build_digest="sha256:aa",
            tool_versions={},
        )
        for key in keys
    }
    assert len(digests) == 3


async def test_two_worlds_failing_alike_and_one_differently_keep_a_world_label() -> None:
    """Only a failure that is the same in every assignment has its cause in no world."""
    probe = Probe()
    probe.fail["alpha"] = failing("invalid_input", ErrorCategory.INVALID_INPUT)
    probe.fail["beta"] = failing("invalid_input", ErrorCategory.INVALID_INPUT)
    probe.fail["gamma"] = failing("not_converged", ErrorCategory.NOT_CONVERGED)
    error = only(await run(probe, "np-q")).error
    assert error is not None
    assert error.world is not None
