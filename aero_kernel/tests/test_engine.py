"""Tests of the engine seam ``evaluate`` (ARCHITECTURE ch. 6, 8.1, 8.3, 8.13)."""

import asyncio
import logging
import math
from collections.abc import Mapping
from typing import Any

import pytest
from aero_kernel.context import Context, Inputs
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError, KernelError
from aero_kernel.graph import GraphModelError
from aero_kernel.schema import ComputeResult, QuantityResult, QuantityStatus, ReasonCode
from aero_kernel.tests.engine_builders import (
    Impl,
    aileron_wing,
    aircraft,
    fixture_model,
    make_build,
    num,
    registry_with,
    request,
)

pytestmark = pytest.mark.asyncio


async def run(
    *slugs: str,
    overrides: Mapping[str, Impl] | None = None,
    drop: tuple[str, ...] = (),
    values: Mapping[str, float] | None = None,
    long_runs: bool = False,
    wings: dict[str, Any] | None = None,
) -> ComputeResult:
    return await evaluate(
        make_build(registry_with(overrides, drop=drop)),
        aircraft(values, wings),
        request(*slugs, long_runs=long_runs),
    )


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


def failing(error: FormulaError) -> Impl:
    async def raiser(x: Inputs, ctx: Context) -> Mapping[str, object]:
        raise error

    return raiser


# --- the happy path, Q3 -------------------------------------------------------------------------


async def test_a_value_is_computed_from_the_inputs() -> None:
    result = await run("weight", "double-weight")
    quantities = by_slug(result)
    assert quantities["weight"].value == (2.0 * 9.81)
    assert quantities["double-weight"].value == (4.0 * 9.81)
    assert quantities["weight"].unit == "N"
    assert quantities["weight"].validated is False
    assert quantities["weight"].from_cache is False


async def test_q3_a_result_leads_back_to_application_tool_and_canon_state() -> None:
    build = make_build()
    result = await evaluate(build, aircraft(), request("weight"))
    quantity = result.quantities[0]
    assert (quantity.slug, quantity.application, quantity.tool) == ("weight", "default", "APP")
    assert result.provenance.canon_model_hash == build.model.content_hash
    assert result.provenance.canon_source_commit == build.model.source_commit
    assert result.provenance.build_digest == build.digest
    assert result.provenance.tool_versions == {}
    assert result.provenance.solver_settings == {}
    assert result.provenance.defaults_used == ()


async def test_results_come_in_request_order_with_the_requested_spelling() -> None:
    result = await run("independent-q", "calc:weight", "double-weight")
    assert [q.slug for q in result.quantities] == ["independent-q", "calc:weight", "double-weight"]


async def test_a_constant_binding_reaches_the_formula() -> None:
    result = await run("scaled-q")
    assert result.quantities[0].value == (6.0)


async def test_the_airplane_input_is_bound_to_the_geometry() -> None:
    seen: list[object] = []

    async def span(x: Inputs, ctx: Context) -> Mapping[str, object]:
        seen.append(x["airplane"])
        return {"s": 1.5}

    result = await run("span-q", overrides={"wing-span": span})
    assert result.quantities[0].value == 1.5
    assert seen == [aircraft().airplane]


async def test_an_absent_optional_input_arrives_as_none() -> None:
    seen: list[Inputs] = []

    async def optional(x: Inputs, ctx: Context) -> Mapping[str, object]:
        seen.append(dict(x))
        return {"r": 1.0}

    values = {"aircraft-mass": 2.0}
    registry = registry_with({"optional-g": optional})
    build = make_build(registry)
    from aero_kernel.schema import AircraftInput

    only_mass = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": values})
    result = await evaluate(build, only_mass, request("opt-q"))
    assert result.quantities[0].status is QuantityStatus.OK
    assert seen[0]["g"] is None
    assert set(seen[0]) == {"m", "g"}


async def test_a_formula_called_once_serves_its_requested_siblings() -> None:
    calls: list[str] = []

    async def twin(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("twin")
        return {"a": 1.0, "b": 2.0}

    result = await run("twin-a", "twin-b", "after-a", "after-b", overrides={"twin": twin})
    assert calls == ["twin"]
    assert [q.status for q in result.quantities] == [QuantityStatus.OK] * 4


async def test_independent_nodes_of_a_layer_run_concurrently() -> None:
    barrier = asyncio.Barrier(2)

    async def meet(x: Inputs, ctx: Context) -> Mapping[str, object]:
        async with asyncio.timeout(2):
            await barrier.wait()
        return {"r": 1.0}

    async def meet_weight(x: Inputs, ctx: Context) -> Mapping[str, object]:
        async with asyncio.timeout(2):
            await barrier.wait()
        return {"w": 1.0}

    result = await run(
        "weight", "independent-q", overrides={"independent": meet, "weight": meet_weight}
    )
    assert [q.status for q in result.quantities] == [QuantityStatus.OK] * 2


# --- errors -------------------------------------------------------------------------------------


async def test_q1_a_model_formula_without_implementation_is_not_implemented() -> None:
    result = await run("unimpl-q")
    quantity = result.quantities[0]
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.unit == "1"
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.NOT_IMPLEMENTED
    assert quantity.error.quantity == "unimpl-q"
    assert quantity.error.formula == "unimplemented"
    assert quantity.error.application == "default"


async def test_q4_a_formula_error_fails_its_quantity_and_its_dependents_only() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    result = await run(
        "weight", "double-weight", "independent-q", overrides={"weight": failing(error)}
    )
    quantities = by_slug(result)
    assert quantities["weight"].error is not None
    assert quantities["weight"].error.code == "not_converged"
    assert quantities["weight"].error.quantity == "weight"
    assert quantities["weight"].error.formula == "weight"
    downstream = quantities["double-weight"].error
    assert downstream is not None
    assert downstream.category is ErrorCategory.UPSTREAM_FAILED
    assert downstream.detail == {"causes": [{"quantity": "weight", "code": "not_converged"}]}
    assert downstream.retryable is True
    assert quantities["independent-q"].status is QuantityStatus.OK


async def test_a_dependent_is_told_the_quantity_it_read_not_a_sibling() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    result = await run("after-a", "after-b", overrides={"twin": failing(error)})
    causes = {q.slug: q.error.detail["causes"] for q in result.quantities if q.error is not None}
    assert causes == {
        "after-a": [{"quantity": "twin-a", "code": "not_converged"}],
        "after-b": [{"quantity": "twin-b", "code": "not_converged"}],
    }


async def test_q6_every_error_category_reaching_a_result_has_message_and_hint() -> None:
    raised = {
        ErrorCategory.INVALID_INPUT: "invalid_input",
        ErrorCategory.UNSUPPORTED_CONFIGURATION: "unsupported_configuration",
        ErrorCategory.NOT_CONVERGED: "not_converged",
        ErrorCategory.TOOL_UNAVAILABLE: "tool_unavailable",
    }
    errors: list[KernelError | None] = []
    for category, code in raised.items():
        error = FormulaError(category, code, "It failed.", "Do this.")
        result = await run("weight", "double-weight", overrides={"weight": failing(error)})
        errors += [q.error for q in result.quantities]
    result = await run("weight", overrides={"weight": _boom})
    errors += [q.error for q in result.quantities]
    result = await run("unimpl-q")
    errors += [q.error for q in result.quantities]
    seen: set[ErrorCategory] = set()
    for error in errors:
        assert error is not None
        again = KernelError.model_validate_json(error.model_dump_json())
        assert again.message
        assert again.hint
        seen.add(again.category)
    # timeout belongs to the time budget, which comes with the solver path
    assert seen == set(ErrorCategory) - {ErrorCategory.TIMEOUT}


async def _boom(x: Inputs, ctx: Context) -> Mapping[str, object]:
    msg = "secret internal text /tmp/file"
    raise RuntimeError(msg)


async def test_a_non_formula_exception_is_internal_logged_once_and_not_leaked(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await run("weight", "double-weight", overrides={"weight": _boom})
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(errors) == 1
    assert errors[0].exc_info is not None
    quantity = result.quantities[0]
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.INTERNAL
    assert quantity.error.escalate is True
    assert "secret" not in quantity.error.message
    assert "/tmp" not in quantity.error.message
    assert quantity.error.quantity == "weight"
    assert "`weight`" in quantity.error.message
    downstream = result.quantities[1].error
    assert downstream is not None
    assert downstream.detail == {"causes": [{"quantity": "weight", "code": "internal"}]}


async def test_two_requested_siblings_of_a_crashed_formula_log_one_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await run("twin-a", "twin-b", overrides={"twin": _boom})
    assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) == 1
    messages = [q.error.message for q in result.quantities if q.error is not None]
    assert "`twin-a`" in messages[0]
    assert "`twin-b`" in messages[1]


@pytest.mark.parametrize(
    "returned",
    [{}, {"w": 1.0, "extra": 2.0}, {"x": 1.0}],
    ids=["missing", "extra", "wrong-name"],
)
async def test_missing_or_extra_output_parameters_are_internal(
    returned: dict[str, object], caplog: pytest.LogCaptureFixture
) -> None:
    async def wrong(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return returned

    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await run("weight", overrides={"weight": wrong})
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.category is ErrorCategory.INTERNAL
    assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) == 1


@pytest.mark.parametrize("bad", [math.nan, math.inf, True, "1.0", None, 3], ids=repr)
async def test_a_scalar_output_that_is_not_a_finite_float_is_internal(bad: object) -> None:
    async def wrong(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"w": bad}

    result = await run("weight", overrides={"weight": wrong})
    assert result.quantities[0].status is QuantityStatus.ERROR
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.category is ErrorCategory.INTERNAL


async def test_a_geometry_flows_between_nodes() -> None:
    result = await run("cfg-span-q")
    assert result.quantities[0].value == 2.5


async def test_an_airplane_output_must_be_a_geometry() -> None:
    async def wrong(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"c": 1.0}

    result = await run("cfg-span-q", overrides={"configure": wrong})
    error = result.quantities[0].error
    assert error is not None
    assert error.detail == {"causes": [{"quantity": "airplane-cfg", "code": "internal"}]}


async def test_a_parameter_of_a_formula_error_becomes_the_input_path() -> None:
    error = FormulaError(
        ErrorCategory.INVALID_INPUT, "missing_input", "g is needed.", "Pass gravity.", parameter="g"
    )
    result = await run("weight", overrides={"weight": failing(error)})
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.input_path == "values.gravity"


@pytest.mark.parametrize(
    ("formula", "slug", "parameter", "expected"),
    [
        ("weight", "weight", "unknown", None),
        ("scaled", "scaled-q", "k", None),
        ("wing-span", "span-q", "airplane", "airplane"),
        ("double", "double-weight", "w", None),
        ("weight", "weight", None, None),
    ],
)
async def test_the_input_path_exists_only_for_a_supplied_input(
    formula: str, slug: str, parameter: str | None, expected: str | None
) -> None:
    error = FormulaError(
        ErrorCategory.INVALID_INPUT, "invalid_input", "m", "h", parameter=parameter
    )
    result = await run(slug, overrides={formula: failing(error)})
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.input_path == expected


# --- input validation, Q8 -----------------------------------------------------------------------


async def test_q8_a_non_positive_mass_returns_input_errors_and_computes_nothing() -> None:
    calls: list[str] = []

    async def spy(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("called")
        return {"w": 1.0}

    result = await run("weight", values={"aircraft-mass": 0.0}, overrides={"weight": spy})
    assert calls == []
    assert result.quantities == ()
    assert [e.code for e in result.input_errors] == ["non_positive_value"]
    assert result.input_errors[0].input_path == "values.aircraft-mass"
    assert result.provenance.canon_model_hash is not None


async def test_an_unknown_value_slug_is_an_input_error() -> None:
    result = await run("weight", values={"nonsense": 1.0})
    assert [e.code for e in result.input_errors] == ["unknown_quantity"]


async def test_a_non_finite_value_is_an_input_error() -> None:
    result = await run("weight", values={"gravity": math.nan})
    assert [e.code for e in result.input_errors] == ["non_finite_number"]


# --- missing input, Q24 -------------------------------------------------------------------------


async def test_q24_a_missing_value_fails_only_its_dependents() -> None:
    from aero_kernel.schema import AircraftInput

    no_gravity = AircraftInput.model_validate(
        {"airplane": {"name": "t"}, "values": {"aircraft-mass": 2.0}}
    )
    result = await evaluate(
        make_build(), no_gravity, request("weight", "double-weight", "independent-q")
    )
    quantities = by_slug(result)
    missing = quantities["weight"].error
    assert missing is not None
    assert (missing.category, missing.code) == (ErrorCategory.INVALID_INPUT, "missing_input")
    assert missing.input_path == "values.gravity"
    assert "gravity" in missing.message
    downstream = quantities["double-weight"].error
    assert downstream is not None
    assert downstream.category is ErrorCategory.UPSTREAM_FAILED
    assert downstream.detail == {"causes": [{"quantity": "weight", "code": "missing_input"}]}
    assert quantities["independent-q"].status is QuantityStatus.OK


# --- requests that do not resolve ---------------------------------------------------------------


async def test_an_unknown_slug_errors_without_a_unit_and_the_rest_is_computed() -> None:
    result = await run("nonsense", "weight")
    quantities = by_slug(result)
    assert quantities["nonsense"].unit is None
    assert quantities["nonsense"].error is not None
    assert quantities["nonsense"].error.code == "unknown_quantity"
    assert quantities["weight"].status is QuantityStatus.OK


async def test_a_malformed_slug_errors_without_a_unit() -> None:
    result = await run("Not A Slug", "weight")
    assert result.quantities[0].unit is None
    assert result.quantities[0].error is not None


async def test_an_input_slug_is_not_requestable_and_keeps_its_unit() -> None:
    result = await run("aircraft-mass")
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.code == "not_requestable"
    assert result.quantities[0].unit == "kg"


async def test_a_non_scalar_request_is_an_error_with_the_unit() -> None:
    result = await run("curve-q", "independent-q")
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.code == "non_scalar_result"
    assert result.quantities[0].unit == "1"
    assert result.quantities[1].status is QuantityStatus.OK


# --- conditions ---------------------------------------------------------------------------------


async def test_an_unmet_when_condition_is_not_applicable_and_so_are_dependents() -> None:
    result = await run("roll-q", "after-roll-q", "independent-q")
    quantities = by_slug(result)
    assert quantities["roll-q"].status is QuantityStatus.NOT_APPLICABLE
    assert quantities["roll-q"].reason is not None
    assert quantities["roll-q"].reason.code is ReasonCode.CONDITION_NOT_MET
    assert quantities["roll-q"].unit == "deg/s"
    assert quantities["after-roll-q"].reason is not None
    assert quantities["after-roll-q"].reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE
    assert quantities["independent-q"].status is QuantityStatus.OK


async def test_a_met_when_condition_computes() -> None:
    result = await run("roll-q", "after-roll-q", wings=aileron_wing())
    assert [q.value for q in result.quantities] == [10.0, 11.0]


async def test_a_pending_when_term_is_not_implemented_never_a_key_error() -> None:
    result = await run("tail-q")
    quantity = result.quantities[0]
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.NOT_IMPLEMENTED
    assert quantity.error.quantity == "tail-q"
    assert quantity.error.formula == "tail"
    assert "has_horizontal_tail" in quantity.error.message


async def test_an_unmet_given_is_not_applicable_not_given() -> None:
    result = await run("given-q")
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.code is ReasonCode.NOT_GIVEN
    supplied = await run("given-q", values={"target-t": 1.0})
    assert supplied.quantities[0].value == (3.0)


# --- status precedence, Q26 ---------------------------------------------------------------------


async def test_q26_error_beats_not_applicable_beats_nothing() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    failed = await run("mix-q", overrides={"weight": failing(error)})
    assert failed.quantities[0].error is not None
    assert failed.quantities[0].error.category is ErrorCategory.UPSTREAM_FAILED
    assert failed.quantities[0].error.detail == {
        "causes": [{"quantity": "weight", "code": "not_converged"}]
    }
    only_na = await run("mix-na-q")
    assert only_na.quantities[0].reason is not None
    assert only_na.quantities[0].reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE


async def test_q26_skipped_beats_not_applicable() -> None:
    result = await run("mix-skip-q")
    assert result.quantities[0].status is QuantityStatus.SKIPPED
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.code is ReasonCode.DEPENDS_ON_SKIPPED


# --- long runs, Q15 -----------------------------------------------------------------------------


async def test_q15_a_long_run_is_skipped_unless_requested_and_dependents_follow() -> None:
    calls: list[str] = []

    async def long_run(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("long")
        return {"r": 99.0}

    result = await run("long-q", "after-long-q", overrides={"long-run": long_run})
    assert calls == []
    first, second = result.quantities
    assert first.status is QuantityStatus.SKIPPED
    assert first.reason is not None
    assert first.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
    assert first.unit == "1"
    assert second.reason is not None
    assert second.reason.code is ReasonCode.DEPENDS_ON_SKIPPED
    included = await run("long-q", "after-long-q", long_runs=True, overrides={"long-run": long_run})
    assert calls == ["long"]
    assert [q.value for q in included.quantities] == [99.0, 100.0]


async def test_an_upstream_error_beats_a_long_run_skip() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    model = fixture_model()
    assert model.formula("long-run") is not None
    # mix-skip reads roll-q (not applicable) and long-q (skipped); give long-run an own failure
    result = await run(
        "long-q", "mix-skip-q", long_runs=True, overrides={"long-run": failing(error)}
    )
    assert result.quantities[1].error is not None
    assert result.quantities[1].error.category is ErrorCategory.UPSTREAM_FAILED


# --- warnings -----------------------------------------------------------------------------------


async def test_a_formula_warning_is_listed_with_origin_and_inherited_once() -> None:
    async def warn_twice(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("precondition_unchecked", "g was not checked.", {"parameter": "g"})
        ctx.warn("precondition_unchecked", "g was not checked.", {"parameter": "g"})
        return {"w": num(x, "m")}

    result = await run("weight", "double-weight", "independent-q", overrides={"weight": warn_twice})
    quantities = by_slug(result)
    for slug in ("weight", "double-weight"):
        (warning,) = quantities[slug].warnings
        assert warning.origin == "weight"
        assert warning.code == "precondition_unchecked"
        assert warning.detail == {"parameter": "g"}
    assert quantities["independent-q"].warnings == ()


async def test_the_warning_origin_of_a_multi_output_node_is_its_first_quantity() -> None:
    async def warn(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("precondition_unchecked", "unchecked.")
        return {"a": 1.0, "b": 2.0}

    result = await run("twin-b", overrides={"twin": warn})
    assert result.quantities[0].warnings[0].origin == "twin-a"


async def test_an_unknown_warning_code_is_internal() -> None:
    async def warn(x: Inputs, ctx: Context) -> Mapping[str, object]:
        ctx.warn("not_a_code", "x")
        return {"w": 1.0}

    result = await run("weight", overrides={"weight": warn})
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.category is ErrorCategory.INTERNAL


# --- model defects ------------------------------------------------------------------------------


async def test_a_graph_defect_makes_every_requested_quantity_internal_logged_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    build = make_build()

    def broken(slugs: object) -> object:
        msg = "cycle: a -> b -> a"
        raise GraphModelError(msg)

    monkeypatch.setattr(build.graph, "subtree", broken)
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await evaluate(build, aircraft(), request("weight", "nonsense"))
    errors = [q.error for q in result.quantities]
    assert all(e is not None and e.category is ErrorCategory.INTERNAL for e in errors)
    assert all(e is not None and e.escalate for e in errors)
    assert result.quantities[0].unit == "N"
    assert result.quantities[1].unit is None
    assert "cycle" not in str([e.message for e in errors if e is not None])
    logged = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(logged) == 1
    assert logged[0].exc_info is not None


# --- logging ------------------------------------------------------------------------------------


async def test_one_info_line_per_call_and_debug_per_node_all_with_the_same_call_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.engine"):
        await run("weight", "double-weight")
        info = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info) == 1
        debug = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert len(debug) >= 4  # start and end of two nodes
    ids = {getattr(r, "call_id", None) for r in caplog.records}
    assert len(ids) == 1
    (call_id,) = ids
    assert isinstance(call_id, str)
    assert len(call_id) >= 6
    message = info[0].getMessage()
    assert "2" in message
    assert "ok" in message


async def test_each_call_has_its_own_call_id(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel.engine"):
        await run("weight")
        await run("weight")
    ids = [getattr(r, "call_id", None) for r in caplog.records]
    assert len(ids) == 2
    assert ids[0] != ids[1]
