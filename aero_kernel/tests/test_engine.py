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
from aero_kernel.schema import (
    AircraftInput,
    ComputeResult,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
)
from aero_kernel.tests.engine_builders import (
    STANDARD,
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


async def test_q26_not_applicable_beats_a_failed_predecessor() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    mixed = await run("mix-q", overrides={"weight": failing(error)})
    assert mixed.quantities[0].status is QuantityStatus.NOT_APPLICABLE
    assert mixed.quantities[0].reason is not None
    assert mixed.quantities[0].reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE
    assert mixed.quantities[0].reason.message == "`mix-q` reads `roll-q`, which is not applicable."
    alone = await run("double-weight", overrides={"weight": failing(error)})
    assert alone.quantities[0].error is not None
    assert alone.quantities[0].error.category is ErrorCategory.UPSTREAM_FAILED


async def test_q26_not_applicable_beats_a_skipped_predecessor() -> None:
    result = await run("mix-skip-q")
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE
    assert result.quantities[0].status is QuantityStatus.NOT_APPLICABLE


async def test_a_skipped_predecessor_alone_skips_its_reader() -> None:
    result = await run("after-long-q")
    assert result.quantities[0].status is QuantityStatus.SKIPPED
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.code is ReasonCode.DEPENDS_ON_SKIPPED
    assert result.quantities[0].reason.message == "`after-long-q` reads `long-q`, which is skipped."


# --- the one status order (ch. 8.13): 1 unmet condition, 2 not applicable predecessor,
# --- 3 not implemented, 4 failed predecessor, 5 missing input, 6 long run, 7 skipped predecessor --


async def first(*slugs: str, **kwargs: Any) -> QuantityResult:
    result = await run(*slugs, **kwargs)
    return result.quantities[0]


def failure() -> FormulaError:
    return FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")


async def test_order_1_an_unmet_condition_beats_a_not_applicable_predecessor() -> None:
    quantity = await first("na-when-q")
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET


async def test_order_1_an_unmet_condition_beats_a_failed_predecessor() -> None:
    quantity = await first("when-after-weight-q", overrides={"weight": failing(failure())})
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET


async def test_order_2_a_not_applicable_predecessor_beats_no_implementation() -> None:
    quantity = await first("after-roll-q", drop=("after-roll",))
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE


async def test_order_3_no_implementation_beats_a_failed_predecessor() -> None:
    quantity = await first(
        "double-weight", drop=("double",), overrides={"weight": failing(failure())}
    )
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.NOT_IMPLEMENTED


async def test_order_3_no_implementation_beats_a_missing_input() -> None:
    no_mass = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(
        make_build(registry_with(drop=("unimplemented",))), no_mass, request("unimpl-q")
    )
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.category is ErrorCategory.NOT_IMPLEMENTED


async def test_order_3_a_pending_when_term_beats_a_failed_predecessor() -> None:
    model_with_failing_reader = await first("tail-q", overrides={"tail": failing(failure())})
    assert model_with_failing_reader.error is not None
    assert model_with_failing_reader.error.category is ErrorCategory.NOT_IMPLEMENTED


async def test_order_3_an_unsupported_read_beats_a_missing_input() -> None:
    no_mass = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(make_build(), no_mass, request("needs-components-q"))
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.code == "unsupported_value_type"


async def test_order_4_a_failed_predecessor_beats_a_missing_input() -> None:
    quantity = await first("err-missing-q", overrides={"weight": failing(failure())})
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.UPSTREAM_FAILED


async def test_order_5_a_missing_input_beats_a_long_run_skip() -> None:
    quantity = await first("long-needs-t-q")
    assert quantity.error is not None
    assert quantity.error.code == "missing_input"
    assert quantity.error.input_path == "values.target-t"


async def test_order_6_a_long_run_beats_a_skipped_predecessor() -> None:
    quantity = await first("long-after-long-q")
    assert quantity.status is QuantityStatus.SKIPPED
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
    assert quantity.reason.message == (
        "`long-after-long-q` is a long run and the request does not include long runs."
    )


async def test_x05_a_long_run_with_a_not_applicable_predecessor_is_not_applicable() -> None:
    quantity = await first("long-after-roll-q")
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE


async def test_a_long_run_with_a_failed_predecessor_is_upstream_failed() -> None:
    quantity = await first("long-after-weight-q", overrides={"weight": failing(failure())})
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.UPSTREAM_FAILED


# --- exported outputs of a type v1 cannot carry (amendment 1.1, Q38) ----------------------------


async def test_a_polar_is_discarded_and_its_scalar_sibling_is_produced_once() -> None:
    calls: list[str] = []

    async def polar_twin(x: Inputs, ctx: Context) -> Mapping[str, object]:
        calls.append("called")
        return {"pol": object(), "s": 5.0}

    result = await run("polar-q", "polar-scalar-q", overrides={"polar-twin": polar_twin})
    polar, scalar = result.quantities
    assert polar.error is not None
    assert polar.error.code == "non_scalar_result"
    assert (scalar.status, scalar.value) == (QuantityStatus.OK, 5.0)
    assert calls == ["called"]


async def test_a_missing_polar_key_is_internal() -> None:
    async def no_polar(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"s": 5.0}

    quantity = await first("polar-scalar-q", overrides={"polar-twin": no_polar})
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.INTERNAL


async def test_a_reader_of_a_polar_is_not_implemented() -> None:
    quantity = await first("polar-read-q")
    assert quantity.error is not None
    assert (quantity.error.category, quantity.error.code) == (
        ErrorCategory.NOT_IMPLEMENTED,
        "unsupported_value_type",
    )
    assert quantity.error.message == (
        "`polar-read-q` reads `polar-q` (a polar), which the kernel cannot carry yet."
    )


async def test_a_requested_polar_is_non_scalar_result() -> None:
    quantity = await first("polar-q")
    assert quantity.error is not None
    assert quantity.error.code == "non_scalar_result"


# --- exact fields of every engine-built error ---------------------------------------------------

REPORT = "Report it; attach input and provenance."


async def test_the_exact_fields_of_every_engine_built_error() -> None:
    cases: list[tuple[str, QuantityResult, tuple[str, str, str, str, str, str | None]]] = []
    boom = await first("weight", overrides={"weight": _boom})
    cases.append(
        (
            "exception",
            boom,
            (
                "weight",
                "weight",
                "default",
                "Internal error (RuntimeError) while computing `weight`.",
                REPORT,
                None,
            ),
        )
    )
    formula_error = FormulaError(
        ErrorCategory.INVALID_INPUT,
        "missing_input",
        "gravity is needed.",
        "Pass gravity.",
        parameter="g",
    )
    raised = await first("weight", overrides={"weight": failing(formula_error)})
    cases.append(
        (
            "formula error",
            raised,
            (
                "weight",
                "weight",
                "default",
                "gravity is needed.",
                "Pass gravity.",
                "values.gravity",
            ),
        )
    )
    no_g = AircraftInput.model_validate(
        {"airplane": {"name": "t"}, "values": {"aircraft-mass": 2.0}}
    )
    missing = (await evaluate(make_build(), no_g, request("weight"))).quantities[0]
    cases.append(
        (
            "missing input",
            missing,
            (
                "weight",
                "weight",
                "default",
                "`weight` needs `gravity`, which was not supplied.",
                "Supply `gravity` in `values`.",
                "values.gravity",
            ),
        )
    )
    cases.append(
        (
            "not implemented",
            await first("unimpl-q"),
            (
                "unimpl-q",
                "unimplemented",
                "default",
                "`unimplemented` is in the canon, not in the kernel yet.",
                "Request a quantity whose formula is implemented.",
                None,
            ),
        )
    )
    cases.append(
        (
            "pending term",
            await first("tail-q"),
            (
                "tail-q",
                "tail",
                "default",
                "The condition `has_horizontal_tail` cannot be evaluated yet.",
                "Its fact is not implemented (#1187).",
                None,
            ),
        )
    )
    upstream = await first("double-weight", overrides={"weight": failing(failure())})
    cases.append(
        (
            "upstream failed",
            upstream,
            (
                "double-weight",
                "double",
                "default",
                "`double-weight` has no value because `weight` failed.",
                "Fix `weight` first.",
                None,
            ),
        )
    )
    cases.append(
        (
            "unsupported value type",
            await first("curve-read-q"),
            (
                "curve-read-q",
                "curve-reader",
                "default",
                "`curve-read-q` reads `curve-q` (a curve), which the kernel cannot carry yet.",
                "Request a quantity that reads scalars and the airplane only.",
                None,
            ),
        )
    )
    for name, quantity, expected in cases:
        error = quantity.error
        assert error is not None, name
        actual = (
            error.quantity,
            error.formula,
            error.application,
            error.message,
            error.hint,
            error.input_path,
        )
        assert actual == expected, name


# --- requested spelling (Q-C / R4) --------------------------------------------------------------


async def test_a_crash_names_only_the_requested_sibling_and_the_log_carries_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        quantity = await first("twin-b", overrides={"twin": _boom})
    assert quantity.error is not None
    assert quantity.error.quantity == "twin-b"
    assert quantity.error.message == "Internal error (RuntimeError) while computing `twin-b`."
    (record,) = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert (record.quantity, record.formula, record.application) == (  # type: ignore[attr-defined]  # logging extra
        "twin-b",
        "twin",
        "default",
    )
    assert isinstance(getattr(record, "call_id", None), str)


async def test_an_upstream_message_names_the_requested_sibling() -> None:
    quantity = await first("after-b", overrides={"twin": failing(failure())})
    assert quantity.error is not None
    assert quantity.error.message == "`after-b` has no value because `twin-b` failed."


async def test_a_skip_reason_names_the_requested_spelling() -> None:
    quantity = await first("calc:long-q")
    assert quantity.slug == "calc:long-q"
    assert quantity.reason is not None
    assert quantity.reason.message == (
        "`calc:long-q` is a long run and the request does not include long runs."
    )


async def test_long_run_twins_requested_in_two_spellings_name_themselves() -> None:
    result = await run("long-twin-a", "calc:long-twin-b")
    assert result.quantities[0].reason is not None
    assert result.quantities[0].reason.message == (
        "`long-twin-a` is a long run and the request does not include long runs."
    )
    assert result.quantities[1].reason is not None
    assert result.quantities[1].reason.message == (
        "`calc:long-twin-b` is a long run and the request does not include long runs."
    )


# --- values and validation of outputs -----------------------------------------------------------


async def test_every_output_of_a_node_carries_its_own_value() -> None:
    result = await run("twin-a", "twin-b", "after-a", "after-b")
    assert [q.value for q in result.quantities] == [2.0, 4.0, 3.0, 5.0]


async def test_a_non_finite_second_output_makes_that_quantity_internal_and_logs_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def nan_b(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"a": 1.0, "b": math.nan}

    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        quantity = await first("twin-b", overrides={"twin": nan_b})
    assert quantity.error is not None
    assert quantity.error.category is ErrorCategory.INTERNAL
    assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) == 1


async def test_a_formula_that_omits_an_unexposed_output_is_internal() -> None:
    async def omit(x: Inputs, ctx: Context) -> Mapping[str, object]:
        return {"r": 1.0}

    internal = await first("unexposed-q", overrides={"unexposed": omit})
    assert internal.error is not None
    assert internal.error.category is ErrorCategory.INTERNAL
    complete = await first("unexposed-q")
    assert (complete.status, complete.value) == (QuantityStatus.OK, 1.0)


async def test_zero_is_a_value() -> None:
    quantity = await first("weight", values={"gravity": 0.0})
    assert (quantity.status, quantity.value) == (QuantityStatus.OK, 0.0)


# --- several missing inputs, exact wording ------------------------------------------------------


async def test_several_missing_inputs_name_every_display_name_in_message_and_hint() -> None:
    nothing = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(make_build(), nothing, request("weight"))
    error = result.quantities[0].error
    assert error is not None
    assert error.hint == "Supply `aircraft-mass` and `gravity` in `values`."
    assert "calc:" not in f"{error.message} {error.hint}"


async def test_three_missing_inputs_read_as_a_list() -> None:
    nothing = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(make_build(), nothing, request("long-needs-t-q"))
    error = result.quantities[0].error
    assert error is not None
    assert error.message == (
        "`long-needs-t-q` needs `aircraft-mass` and `target-t`, which were not supplied."
    )


# --- input_path of a formula error blaming a target ---------------------------------------------


async def test_a_formula_error_blaming_a_target_binding_points_into_values() -> None:
    error = FormulaError(ErrorCategory.INVALID_INPUT, "invalid_input", "m", "h", parameter="t")
    quantity = await first(
        "given-q", values={"target-t": 1.0}, overrides={"given-only": failing(error)}
    )
    assert quantity.error is not None
    assert quantity.error.input_path == "values.target-t"


# --- causes per edge ----------------------------------------------------------------------------


async def test_a_node_reading_both_siblings_lists_both_causes() -> None:
    quantity = await first("after-both-q", overrides={"twin": failing(failure())})
    assert quantity.error is not None
    assert quantity.error.detail == {
        "causes": [
            {"quantity": "twin-a", "code": "not_converged"},
            {"quantity": "twin-b", "code": "not_converged"},
        ]
    }


# --- logging ------------------------------------------------------------------------------------


async def test_the_info_line_carries_slugs_flag_and_exact_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await run("weight", "double-weight", "nonsense", "roll-q", long_runs=True)
    (info,) = [r for r in caplog.records if r.levelno == logging.INFO]
    assert info.getMessage().startswith(
        "compute: [weight, double-weight, nonsense, roll-q] include_long_runs=True, "
        "4 quantities (error=1, not_applicable=1, ok=2), 0 input errors, "
    )
    assert isinstance(getattr(info, "call_id", None), str)


async def test_the_input_errors_path_logs_exactly_one_info_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        await run("weight", values={"aircraft-mass": 0.0})
    (info,) = [r for r in caplog.records if r.levelno == logging.INFO]
    assert info.getMessage().startswith(
        "compute: [weight] include_long_runs=False, 0 quantities (none), 1 input errors, "
    )
    assert isinstance(getattr(info, "call_id", None), str)


async def test_an_absent_optional_input_adds_no_info_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    only_mass = AircraftInput.model_validate(
        {"airplane": {"name": "t"}, "values": {"aircraft-mass": 2.0}}
    )
    with caplog.at_level(logging.INFO, logger="aero_kernel"):
        await evaluate(make_build(), only_mass, request("opt-q"))
    assert len([r for r in caplog.records if r.levelno == logging.INFO]) == 1


async def test_every_debug_line_of_a_node_carries_formula_and_application(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel.engine"):
        await run("weight")
    node_lines = [r for r in caplog.records if r.levelno == logging.DEBUG]
    assert [r.getMessage().split(":")[0] for r in node_lines] == ["node started", "node finished"]
    for record in node_lines:
        assert (record.formula, record.application) == ("weight", "default")  # type: ignore[attr-defined]  # logging extra


# --- provenance and the shared input dict -------------------------------------------------------


async def test_provenance_equals_the_builds() -> None:
    build = make_build()
    result = await evaluate(build, aircraft(), request("weight"))
    assert result.provenance.canon_model_hash == build.model.content_hash
    assert result.provenance.canon_source_commit == build.model.source_commit
    assert result.provenance.build_digest == build.digest
    refused = await evaluate(build, aircraft({"aircraft-mass": 0.0}), request("weight"))
    assert refused.provenance == result.provenance


async def test_every_node_gets_exactly_the_parameters_of_its_formula() -> None:
    seen: dict[str, set[str]] = {}
    model = fixture_model()

    def spying(slug: str, original: Impl) -> Impl:
        async def spy(x: Inputs, ctx: Context) -> Mapping[str, object]:
            seen[slug] = set(x)
            return await original(x, ctx)

        return spy

    registry = registry_with({slug: spying(slug, impl) for slug, impl in STANDARD.items()})
    result = await evaluate(
        make_build(registry, model),
        aircraft({"target-t": 1.0}, wings=aileron_wing()),
        request(
            "weight",
            "scaled-q",
            "opt-q",
            "span-q",
            "twin-a",
            "given-q",
            "after-roll-q",
            "cfg-span-q",
            "after-both-q",
            "double-weight",
            "independent-q",
            "unexposed-q",
        ),
    )
    assert all(q.status is QuantityStatus.OK for q in result.quantities)
    assert len(seen) >= 10
    for slug, parameters in seen.items():
        formula = model.formula(slug)
        assert formula is not None
        assert parameters == set(formula.inputs), slug


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
    result = await run("long-after-weight-q", overrides={"weight": failing(error)})
    downstream = result.quantities[0].error
    assert result.quantities[0].status is QuantityStatus.ERROR
    assert downstream is not None
    assert downstream.category is ErrorCategory.UPSTREAM_FAILED


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
    assert (
        info[0]
        .getMessage()
        .startswith(
            "compute: [weight, double-weight] include_long_runs=False, "
            "2 quantities (ok=2), 0 input errors, "
        )
    )


async def test_each_call_has_its_own_call_id(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="aero_kernel.engine"):
        await run("weight")
        await run("weight")
    ids = [getattr(r, "call_id", None) for r in caplog.records]
    assert len(ids) == 2
    assert ids[0] != ids[1]


# --- one status per node, worded for each requested quantity (R4) -------------------------------


async def test_a_not_applicable_sibling_names_its_own_slug() -> None:
    result = await run("na-twin-a", "na-twin-b")
    for quantity in result.quantities:
        assert quantity.reason is not None
        assert quantity.reason.code is ReasonCode.DEPENDS_ON_NOT_APPLICABLE
        assert f"`{quantity.slug}`" in quantity.reason.message
    assert "`na-twin-a`" not in result.quantities[1].reason.message  # type: ignore[union-attr]


async def test_a_long_run_skipped_sibling_names_its_own_slug() -> None:
    result = await run("long-twin-a", "long-twin-b")
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.SKIPPED
        assert quantity.reason is not None
        assert quantity.reason.code is ReasonCode.LONG_RUN_NOT_INCLUDED
        assert f"`{quantity.slug}`" in quantity.reason.message


async def test_an_upstream_failed_sibling_names_its_own_slug() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")
    result = await run("dep-twin-a", "dep-twin-b", overrides={"weight": failing(error)})
    for quantity in result.quantities:
        assert quantity.error is not None
        assert quantity.error.quantity == quantity.slug
        assert f"`{quantity.slug}`" in quantity.error.message


async def test_a_missing_input_sibling_names_its_own_slug() -> None:
    no_mass = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(make_build(), no_mass, request("twin-a", "twin-b"))
    for quantity in result.quantities:
        assert quantity.error is not None
        assert quantity.error.code == "missing_input"
        assert f"`{quantity.slug}`" in quantity.error.message


async def test_a_not_implemented_sibling_names_its_own_slug() -> None:
    result = await run("twin-a", "twin-b", drop=("twin",))
    for quantity in result.quantities:
        assert quantity.error is not None
        assert quantity.error.category is ErrorCategory.NOT_IMPLEMENTED
        assert quantity.error.quantity == quantity.slug


async def test_a_formula_authored_text_is_never_rewritten() -> None:
    error = FormulaError(
        ErrorCategory.INVALID_INPUT,
        "invalid_input",
        "`twin-a` exceeds `twin-b`.",
        "Lower `twin-a` or raise `twin-b`.",
    )
    result = await run("twin-a", "twin-b", overrides={"twin": failing(error)})
    for quantity in result.quantities:
        assert quantity.error is not None
        assert quantity.error.quantity == quantity.slug
        assert quantity.error.message == "`twin-a` exceeds `twin-b`."
        assert quantity.error.hint == "Lower `twin-a` or raise `twin-b`."


async def test_a_crash_logs_once_and_each_sibling_names_its_own_slug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG, logger="aero_kernel"):
        result = await run("twin-a", "twin-b", overrides={"twin": _boom})
    assert len([r for r in caplog.records if r.levelno >= logging.ERROR]) == 1
    for quantity in result.quantities:
        assert quantity.error is not None
        assert f"`{quantity.slug}`" in quantity.error.message
        assert quantity.error.quantity == quantity.slug


# --- values the kernel cannot carry yet (R2) ----------------------------------------------------


async def test_reading_a_curve_is_not_implemented_with_its_own_code() -> None:
    result = await run("curve-read-q")
    error = result.quantities[0].error
    assert error is not None
    assert (error.category, error.code) == (
        ErrorCategory.NOT_IMPLEMENTED,
        "unsupported_value_type",
    )
    assert "`curve-q`" in error.message
    assert "curve" in error.message
    assert error.quantity == "curve-read-q"


async def test_reading_the_components_input_is_not_implemented_never_missing_input() -> None:
    result = await run("needs-components-q")
    error = result.quantities[0].error
    assert error is not None
    assert error.code == "unsupported_value_type"
    assert "`components`" in error.message
    assert error.input_path is None


async def test_an_unsupported_read_fails_only_its_reader() -> None:
    result = await run("curve-read-q", "independent-q")
    assert result.quantities[1].status is QuantityStatus.OK


# --- several missing inputs (N7) ----------------------------------------------------------------


async def test_several_missing_inputs_are_one_error_with_the_first_as_input_path() -> None:
    nothing = AircraftInput.model_validate({"airplane": {"name": "t"}, "values": {}})
    result = await evaluate(make_build(), nothing, request("weight"))
    error = result.quantities[0].error
    assert error is not None
    assert error.input_path == "values.aircraft-mass"
    assert error.detail == {"inputs": ["aircraft-mass", "gravity"]}
    assert error.message == "`weight` needs `aircraft-mass` and `gravity`, which were not supplied."


async def test_one_missing_input_reads_in_the_singular() -> None:
    only_mass = AircraftInput.model_validate(
        {"airplane": {"name": "t"}, "values": {"aircraft-mass": 2.0}}
    )
    result = await evaluate(make_build(), only_mass, request("weight"))
    assert result.quantities[0].error is not None
    assert result.quantities[0].error.message == "`weight` needs `gravity`, which was not supplied."


# --- a failing node does not cancel its layer (S9) ----------------------------------------------


async def test_a_failing_node_leaves_its_in_flight_sibling_of_the_layer_alone() -> None:
    barrier = asyncio.Barrier(2)
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "No solution.", "Retry.")

    async def raiser(x: Inputs, ctx: Context) -> Mapping[str, object]:
        async with asyncio.timeout(2):
            await barrier.wait()
        raise error

    async def slow(x: Inputs, ctx: Context) -> Mapping[str, object]:
        async with asyncio.timeout(2):
            await barrier.wait()
        await asyncio.sleep(0.01)
        return {"r": 7.0}

    result = await run("weight", "independent-q", overrides={"weight": raiser, "independent": slow})
    assert result.quantities[0].status is QuantityStatus.ERROR
    assert result.quantities[1].status is QuantityStatus.OK
    assert result.quantities[1].value == 7.0
