"""Pre- and postconditions in the engine (ARCHITECTURE ch. 8.5, 8.1, Q25)."""

from collections.abc import Callable, Mapping
from typing import Any

import pytest
from aero_kernel.build import Build
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.graph import CanonGraph
from aero_kernel.registry import CheckResult, Registry
from aero_kernel.schema import (
    AircraftInput,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
    WarningSeverity,
)
from aero_kernel.tests.engine_builders import NO_SOLVERS, request
from aero_kernel.tests.graph_builders import model_of, quantity
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

ON_VIOLATION_WARNING = "warning"
ON_VIOLATION_ERROR = "error"


def check(check_id: str, parameter: str, on_violation: str, *applications: str) -> dict[str, Any]:
    """A check entry of the fixture formula."""
    entry: dict[str, Any] = {"id": check_id, "parameter": parameter, "on_violation": on_violation}
    if applications:
        entry["applications"] = list(applications)
    return entry


def fixture_model() -> Any:  # the validated canon model
    """One formula `chk` with two applications and four checks."""
    bind = {"m": "calc:aircraft-mass"}
    chk = {
        "kind": "law",
        "tool": "APP",
        "cost": "instant",
        "inputs": dict(bind),
        "outputs": {"a": None, "b": None},
        "applications": [
            {
                "id": "default",
                "bind": dict(bind),
                "produce": {"a": "calc:out-a", "b": "calc:out-b"},
            },
            {"id": "strict", "bind": dict(bind), "produce": {"a": "calc:strict-a", "b": None}},
        ],
        "preconditions": [
            check("pre_warn", "m", ON_VIOLATION_WARNING),
            check("pre_err", "m", ON_VIOLATION_ERROR, "strict"),
        ],
        "postconditions": [
            check("post_warn", "a", ON_VIOLATION_WARNING),
            check("post_err", "b", ON_VIOLATION_ERROR, "default"),
        ],
    }
    return model_of(
        {
            "aircraft-mass": quantity("input", unit="kg", positive=True),
            "out-a": quantity("output"),
            "out-b": quantity("output"),
            "strict-a": quantity("output"),
        },
        {"chk": chk},
    )


class Probe:
    """The checks and the implementation, with what they were called with and what they answer."""

    def __init__(self) -> None:
        self.states: dict[str, CheckResult] = {}
        self.calls: list[str] = []
        self.post_args: list[tuple[Mapping[str, object], Mapping[str, object]]] = []
        self.implementation_calls = 0

    def answer(self, check_id: str) -> CheckResult:
        self.calls.append(check_id)
        return self.states.get(check_id, CheckResult(state="held", message=f"{check_id} held"))

    def _pre(self, check_id: str) -> Callable[[Mapping[str, object]], CheckResult]:
        def pre(x: Mapping[str, object]) -> CheckResult:
            return self.answer(check_id)

        return pre

    def _post(
        self, check_id: str
    ) -> Callable[[Mapping[str, object], Mapping[str, object]], CheckResult]:
        def post(x: Mapping[str, object], y: Mapping[str, object]) -> CheckResult:
            self.post_args.append((dict(x), dict(y)))
            return self.answer(check_id)

        return post

    def registry(self, *, skip: tuple[str, ...] = ()) -> Registry:
        registry = Registry()

        async def chk(x: Inputs, ctx: Context) -> Mapping[str, object]:
            self.implementation_calls += 1
            return {"a": 1.0, "b": 2.0}

        registry.formula("chk")(chk)
        for check_id in ("pre_warn", "pre_err"):
            if check_id not in skip:
                registry.precondition("chk", check_id)(self._pre(check_id))
        for check_id in ("post_warn", "post_err"):
            if check_id not in skip:
                registry.postcondition("chk", check_id)(self._post(check_id))
        return registry


async def run(probe: Probe, *slugs: str, skip: tuple[str, ...] = ()) -> ComputeResult:
    model = fixture_model()
    registry = probe.registry(skip=skip)
    build = Build(
        model=model,
        graph=CanonGraph(model),
        digest="sha256:" + "ab" * 32,
        registry=registry,
        report=registry.check_traceability(model),
    )
    only_mass = AircraftInput.model_validate(
        {"airplane": airplane_document(), "values": {"aircraft-mass": 2.0}}
    )
    return await evaluate(build, only_mass, request(*slugs), solvers=NO_SOLVERS)


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


async def test_held_checks_give_the_value_and_no_warning() -> None:
    probe = Probe()
    result = await run(probe, "out-a", "out-b")
    for quantity_ in result.quantities:
        assert quantity_.status is QuantityStatus.OK
        assert quantity_.warnings == ()
    assert probe.calls == ["pre_warn", "post_warn", "post_err"]  # pre_err is scoped to strict


async def test_a_violated_precondition_with_on_violation_warning_returns_the_value() -> None:
    probe = Probe()
    probe.states["pre_warn"] = CheckResult(state="violated", message="m is odd")
    result = await run(probe, "out-a")
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    (warning,) = only.warnings
    assert (warning.code, warning.severity) == ("precondition_violated", WarningSeverity.DEFECT)
    assert warning.detail == {"precondition": "pre_warn"}
    assert "m is odd" in warning.message
    assert probe.implementation_calls == 1


async def test_a_violated_precondition_with_on_violation_error_withholds_the_call() -> None:
    probe = Probe()
    probe.states["pre_err"] = CheckResult(state="violated", message="m is out")
    result = await run(probe, "strict-a")
    (only,) = result.quantities
    assert only.status is QuantityStatus.ERROR
    assert only.error is not None
    assert (only.error.category, only.error.code) == (
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "precondition_violated",
    )
    assert only.error.detail == {"precondition": "pre_err"}
    assert (only.error.quantity, only.error.formula, only.error.application) == (
        "strict-a",
        "chk",
        "strict",
    )
    assert probe.implementation_calls == 0


async def test_an_unchecked_precondition_warns_and_the_value_stays() -> None:
    probe = Probe()
    probe.states["pre_warn"] = CheckResult(state="unchecked", message="no altitude given")
    result = await run(probe, "out-a")
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    (warning,) = only.warnings
    assert (warning.code, warning.severity) == ("precondition_unchecked", WarningSeverity.PRACTICE)
    assert warning.detail == {"precondition": "pre_warn"}


async def test_a_violated_postcondition_with_on_violation_warning_returns_the_value() -> None:
    probe = Probe()
    probe.states["post_warn"] = CheckResult(state="violated", message="a drifted")
    result = await run(probe, "out-a")
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    assert only.value == 1.0
    (warning,) = only.warnings
    assert (warning.code, warning.severity) == ("postcondition_violated", WarningSeverity.DEFECT)
    assert warning.detail == {"postcondition": "post_warn"}


async def test_a_violated_postcondition_with_on_violation_error_discards_all_outputs() -> None:
    """The outputs come from one evaluation: a failed check on one invalidates the others."""
    probe = Probe()
    probe.states["post_err"] = CheckResult(state="violated", message="b is wrong")
    result = await run(probe, "out-a", "out-b")
    for quantity_ in result.quantities:
        assert quantity_.status is QuantityStatus.ERROR
        assert quantity_.value is None
        assert quantity_.error is not None
        assert (quantity_.error.category, quantity_.error.code) == (
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "postcondition_violated",
        )
        assert quantity_.error.detail == {"postcondition": "post_err"}
    assert probe.implementation_calls == 1


async def test_an_unchecked_postcondition_warns_and_the_value_stays() -> None:
    probe = Probe()
    probe.states["post_err"] = CheckResult(state="unchecked", message="not decidable")
    result = await run(probe, "out-b")
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    (warning,) = only.warnings
    assert (warning.code, warning.severity) == ("postcondition_unchecked", WarningSeverity.PRACTICE)
    assert warning.detail == {"postcondition": "post_err"}


async def test_a_check_scoped_to_another_application_is_neither_run_nor_reported() -> None:
    probe = Probe()
    probe.states["post_err"] = CheckResult(state="violated", message="would fail")
    result = await run(probe, "strict-a")  # post_err is scoped to `default`
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    assert only.warnings == ()
    assert "post_err" not in probe.calls


async def test_a_postcondition_sees_the_inputs_and_all_outputs_also_the_unexposed() -> None:
    probe = Probe()
    await run(probe, "strict-a")  # the strict application does not expose `b`
    ((x, y),) = probe.post_args
    assert x == {"m": 2.0}
    assert y == {"a": 1.0, "b": 2.0}


async def test_a_declared_check_without_a_function_is_reported_unchecked() -> None:
    result = await run(Probe(), "out-a", skip=("pre_warn", "post_warn", "post_err"))
    (only,) = result.quantities
    assert only.status is QuantityStatus.OK
    assert sorted(w.code for w in only.warnings) == [
        "postcondition_unchecked",
        "postcondition_unchecked",
        "precondition_unchecked",
    ]
