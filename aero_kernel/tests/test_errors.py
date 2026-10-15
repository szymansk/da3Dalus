"""Tests for the error catalogue (ARCHITECTURE ch. 8.1, scenarios Q4, Q6, Q23, Q25)."""

import json
import logging

import numpy as np
import pytest
from aero_kernel.errors import (
    CODE_CATALOGUE,
    ErrorCategory,
    FormulaError,
    KernelError,
    aggregate_upstream,
    flags_for,
    format_world_assignment,
    internal_error_from_exception,
    parse_world_assignment,
)
from pydantic import JsonValue, ValidationError

# (category, retryable, escalate) exactly as the table in ch. 8.1.
TABLE: list[tuple[ErrorCategory, bool, bool]] = [
    (ErrorCategory.INVALID_INPUT, False, False),
    (ErrorCategory.UNSUPPORTED_CONFIGURATION, False, False),
    (ErrorCategory.NOT_IMPLEMENTED, False, False),
    (ErrorCategory.NOT_CONVERGED, True, False),
    (ErrorCategory.TIMEOUT, True, False),
    (ErrorCategory.TOOL_UNAVAILABLE, False, True),
    (ErrorCategory.INTERNAL, False, True),
]


def _err(
    quantity: str,
    category: ErrorCategory = ErrorCategory.NOT_CONVERGED,
    code: str | None = None,
) -> KernelError:
    return KernelError(
        code=code or category.value,
        category=category,
        quantity=quantity,
        message=f"{quantity} failed",
        hint=f"Fix {quantity}.",
    )


def test_enum_has_the_eight_error_categories_and_not_not_applicable() -> None:
    names = {c.value for c in ErrorCategory}
    assert names == {
        "invalid_input",
        "unsupported_configuration",
        "not_implemented",
        "not_converged",
        "timeout",
        "tool_unavailable",
        "upstream_failed",
        "internal",
    }
    assert "not_applicable" not in names


@pytest.mark.parametrize(("category", "retryable", "escalate"), TABLE)
def test_flags_for_follows_the_table(
    category: ErrorCategory, retryable: bool, escalate: bool
) -> None:
    assert flags_for(category) == (retryable, escalate)


def test_flags_for_upstream_failed_is_not_defined() -> None:
    with pytest.raises(ValueError, match="upstream_failed"):
        flags_for(ErrorCategory.UPSTREAM_FAILED)


@pytest.mark.parametrize(("category", "retryable", "escalate"), TABLE)
def test_flags_default_from_category(
    category: ErrorCategory, retryable: bool, escalate: bool
) -> None:
    error = _err("stall-speed", category)
    assert (error.retryable, error.escalate) == (retryable, escalate)


@pytest.mark.parametrize(("category", "retryable", "escalate"), TABLE)
def test_contradicting_flags_are_rejected(
    category: ErrorCategory, retryable: bool, escalate: bool
) -> None:
    with pytest.raises(ValidationError, match="contradict"):
        KernelError(
            code=category.value,
            category=category,
            retryable=not retryable,
            escalate=escalate,
            message="m",
            hint="h",
        )
    with pytest.raises(ValidationError, match="contradict"):
        KernelError(
            code=category.value,
            category=category,
            retryable=retryable,
            escalate=not escalate,
            message="m",
            hint="h",
        )


def test_matching_explicit_flags_are_accepted() -> None:
    error = KernelError(
        code="timeout",
        category=ErrorCategory.TIMEOUT,
        retryable=True,
        escalate=False,
        message="m",
        hint="h",
    )
    assert error.retryable is True


def _upstream(
    *, retryable: bool, escalate: bool, detail: dict[str, JsonValue] | None = None
) -> KernelError:
    return KernelError(
        code="upstream_failed",
        category=ErrorCategory.UPSTREAM_FAILED,
        retryable=retryable,
        escalate=escalate,
        message="m",
        hint="h",
        detail={} if detail is None else detail,
    )


_CAUSE_INTERNAL: dict[str, JsonValue] = {"causes": [{"quantity": "a", "code": "internal"}]}


def test_upstream_failed_requires_explicit_flags() -> None:
    with pytest.raises(ValidationError, match="explicit"):
        KernelError(
            code="upstream_failed",
            category=ErrorCategory.UPSTREAM_FAILED,
            message="m",
            hint="h",
            detail=_CAUSE_INTERNAL,
        )
    error = _upstream(retryable=False, escalate=True, detail=_CAUSE_INTERNAL)
    assert (error.retryable, error.escalate) == (False, True)


def test_upstream_failed_flags_must_match_the_root_codes() -> None:
    """The model enforces the aggregation rule, not only aggregate_upstream."""
    with pytest.raises(ValidationError, match="contradict"):
        _upstream(retryable=True, escalate=False, detail=_CAUSE_INTERNAL)
    with pytest.raises(ValidationError, match="contradict"):
        _upstream(retryable=False, escalate=False, detail=_CAUSE_INTERNAL)


def test_upstream_failed_requires_causes_in_detail() -> None:
    with pytest.raises(ValidationError, match="causes"):
        _upstream(retryable=False, escalate=False)
    with pytest.raises(ValidationError, match="causes"):
        _upstream(retryable=False, escalate=False, detail={"causes": []})


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_every_category_serialises_to_json_with_message_and_hint(category: ErrorCategory) -> None:
    """Q6."""
    if category is ErrorCategory.UPSTREAM_FAILED:
        error = KernelError(
            code="upstream_failed",
            category=category,
            retryable=True,
            escalate=False,
            quantity="approach-speed",
            message="stall-speed has no value.",
            hint="Fix `stall-speed` first.",
            detail={"causes": [{"quantity": "stall-speed", "code": "not_converged"}]},
        )
    else:
        error = _err("stall-speed", category)
    payload = json.loads(error.model_dump_json())
    assert payload["message"]
    assert payload["hint"]
    assert payload["category"] == category.value
    assert set(payload) == {
        "code",
        "category",
        "retryable",
        "escalate",
        "quantity",
        "formula",
        "application",
        "world",
        "input_path",
        "message",
        "hint",
        "detail",
    }
    assert KernelError.model_validate_json(error.model_dump_json()) == error


def test_model_is_frozen_and_forbids_extra_fields() -> None:
    error = _err("stall-speed")
    with pytest.raises(ValidationError):
        error.message = "changed"  # type: ignore[misc]  # frozen model: the assignment must fail
    with pytest.raises(ValidationError):
        KernelError.model_validate(
            {"code": "internal", "category": "internal", "message": "m", "hint": "h", "bogus": 1}
        )


@pytest.mark.parametrize("field", ["message", "hint"])
def test_message_and_hint_must_not_be_empty(field: str) -> None:
    kwargs = {"code": "internal", "category": ErrorCategory.INTERNAL, "message": "m", "hint": "h"}
    kwargs[field] = ""
    with pytest.raises(ValidationError):
        KernelError.model_validate(kwargs)


def test_catalogue_contains_the_codes_named_in_the_architecture() -> None:
    assert CODE_CATALOGUE["missing_input"] is ErrorCategory.INVALID_INPUT
    for code in ("target_above_method_maximum", "precondition_violated", "postcondition_violated"):
        assert CODE_CATALOGUE[code] is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert CODE_CATALOGUE["continuous_uncertainty"] is ErrorCategory.NOT_IMPLEMENTED
    for category in ErrorCategory:
        assert CODE_CATALOGUE[category.value] is category


def test_catalogued_code_with_wrong_category_is_rejected() -> None:
    with pytest.raises(ValidationError, match="missing_input"):
        KernelError(code="missing_input", category=ErrorCategory.TIMEOUT, message="m", hint="h")


def test_unresolved_airfoil_is_catalogued() -> None:
    assert CODE_CATALOGUE["unresolved_airfoil"] is ErrorCategory.INVALID_INPUT


def test_uncatalogued_code_is_rejected() -> None:
    """The code table is closed: a new code is added to the table, never invented at the raise site."""
    with pytest.raises(ValidationError, match="some_new_code"):
        _err("x", ErrorCategory.NOT_CONVERGED, code="some_new_code")
    with pytest.raises(ValueError, match="some_new_code"):
        FormulaError(ErrorCategory.NOT_CONVERGED, "some_new_code", "m", "h")


def test_catalogued_codes_get_the_flags_of_their_category() -> None:
    error = KernelError(
        code="target_above_method_maximum",
        category=ErrorCategory.UNSUPPORTED_CONFIGURATION,
        message="m",
        hint="h",
        detail={"max_roll_rate": 1.2, "aileron_deflection_deg": 25.0},
    )
    assert (error.retryable, error.escalate) == (False, False)


# ---- aggregation of upstream_failed (ch. 8.1) -----------------------------------------------


def test_aggregate_single_retryable_cause() -> None:
    result = aggregate_upstream(
        [_err("stall-speed", ErrorCategory.NOT_CONVERGED)], quantity="approach-speed"
    )
    assert result.category is ErrorCategory.UPSTREAM_FAILED
    assert result.code == "upstream_failed"
    assert result.quantity == "approach-speed"
    assert result.retryable is True
    assert result.escalate is False
    assert result.detail == {"causes": [{"quantity": "stall-speed", "code": "not_converged"}]}
    assert "stall-speed" in result.hint


def test_aggregate_retryable_only_if_every_cause_is_retryable() -> None:
    mixed = aggregate_upstream(
        [_err("a", ErrorCategory.NOT_CONVERGED), _err("b", ErrorCategory.INVALID_INPUT)],
        quantity="q",
    )
    assert mixed.retryable is False
    both = aggregate_upstream(
        [_err("a", ErrorCategory.NOT_CONVERGED), _err("b", ErrorCategory.TIMEOUT)], quantity="q"
    )
    assert both.retryable is True


def test_aggregate_escalates_if_any_cause_escalates() -> None:
    result = aggregate_upstream(
        [_err("a", ErrorCategory.NOT_CONVERGED), _err("b", ErrorCategory.INTERNAL)], quantity="q"
    )
    assert result.escalate is True
    assert result.retryable is False
    none = aggregate_upstream(
        [_err("a", ErrorCategory.NOT_CONVERGED), _err("b", ErrorCategory.INVALID_INPUT)],
        quantity="q",
    )
    assert none.escalate is False


def test_aggregate_flattens_nested_upstream_failed_to_roots() -> None:
    inner = aggregate_upstream(
        [_err("stall-speed", ErrorCategory.TIMEOUT)], quantity="approach-speed"
    )
    outer = aggregate_upstream(
        [inner, _err("wing-area", ErrorCategory.INVALID_INPUT, code="missing_input")],
        quantity="landing-distance",
    )
    assert outer.detail == {
        "causes": [
            {"quantity": "stall-speed", "code": "timeout"},
            {"quantity": "wing-area", "code": "missing_input"},
        ]
    }
    # retryable flag of the inner (all roots retryable) combines with the invalid_input root
    assert outer.retryable is False
    assert outer.escalate is False


def test_aggregate_nested_only_keeps_inner_flags() -> None:
    inner = aggregate_upstream([_err("a", ErrorCategory.TIMEOUT)], quantity="b")
    outer = aggregate_upstream([inner], quantity="c")
    assert outer.retryable is True
    assert outer.detail == inner.detail


def test_aggregate_deduplicates_roots_and_preserves_order() -> None:
    root = _err("stall-speed", ErrorCategory.NOT_CONVERGED)
    first = aggregate_upstream([root], quantity="a")
    second = aggregate_upstream([root], quantity="b")
    result = aggregate_upstream([first, second, root], quantity="c")
    assert result.detail == {"causes": [{"quantity": "stall-speed", "code": "not_converged"}]}


def test_aggregate_names_all_roots_in_hint() -> None:
    result = aggregate_upstream([_err("a"), _err("b")], quantity="q")
    assert "`a`" in result.hint
    assert "`b`" in result.hint


def test_aggregate_requires_a_cause() -> None:
    with pytest.raises(ValueError, match="at least one"):
        aggregate_upstream([], quantity="q")


def test_aggregate_root_without_quantity_is_rejected() -> None:
    cause = KernelError(code="timeout", category=ErrorCategory.TIMEOUT, message="m", hint="h")
    with pytest.raises(ValueError, match="quantity"):
        aggregate_upstream([cause], quantity="q")


def test_aggregate_carries_optional_context() -> None:
    result = aggregate_upstream(
        [_err("a")], quantity="q", formula="f", application="app", world="f=w1"
    )
    assert (result.formula, result.application, result.world) == ("f", "app", "f=w1")


# ---- FormulaError translation -------------------------------------------------------------


def test_formula_error_is_an_exception_carrying_its_fields() -> None:
    exc = FormulaError(
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
        "No solution.",
        "Raise the accuracy tier.",
        {"iterations": 50},
    )
    assert isinstance(exc, Exception)
    assert str(exc) == "No solution."
    assert exc.category is ErrorCategory.NOT_CONVERGED
    assert exc.hint == "Raise the accuracy tier."
    assert exc.detail == {"iterations": 50}


def test_formula_error_detail_defaults_to_empty() -> None:
    exc = FormulaError(ErrorCategory.INVALID_INPUT, "missing_input", "m", "h")
    assert exc.detail == {}


@pytest.mark.parametrize(
    "category",
    [
        ErrorCategory.TIMEOUT,
        ErrorCategory.UPSTREAM_FAILED,
        ErrorCategory.NOT_IMPLEMENTED,
        ErrorCategory.INTERNAL,
    ],
)
def test_formula_error_rejects_engine_categories(category: ErrorCategory) -> None:
    with pytest.raises(ValueError, match="engine"):
        FormulaError(category, category.value, "m", "h")


@pytest.mark.parametrize(
    "category",
    [
        ErrorCategory.INVALID_INPUT,
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        ErrorCategory.NOT_CONVERGED,
        ErrorCategory.TOOL_UNAVAILABLE,
    ],
)
def test_formula_error_accepts_formula_categories(category: ErrorCategory) -> None:
    assert FormulaError(category, category.value, "m", "h").category is category


def test_formula_error_carries_input_path_into_the_kernel_error() -> None:
    exc = FormulaError(
        ErrorCategory.INVALID_INPUT,
        "missing_input",
        "m",
        "h",
        input_path="values.flap-deflection-landing",
    )
    assert exc.to_kernel_error(quantity="q").input_path == "values.flap-deflection-landing"


def test_formula_error_translates_with_context() -> None:
    exc = FormulaError(
        ErrorCategory.INVALID_INPUT,
        "missing_input",
        "Flap deflection is missing.",
        "Pass `values.flap-deflection-landing`.",
        {"input": "values.flap-deflection-landing"},
    )
    error = exc.to_kernel_error(
        quantity="stall-speed-landing", formula="stall-speed", application="landing", world="f=asb"
    )
    assert error.category is ErrorCategory.INVALID_INPUT
    assert error.code == "missing_input"
    assert error.message == "Flap deflection is missing."
    assert error.hint == "Pass `values.flap-deflection-landing`."
    assert error.detail == {"input": "values.flap-deflection-landing"}
    assert (error.quantity, error.formula, error.application, error.world) == (
        "stall-speed-landing",
        "stall-speed",
        "landing",
        "f=asb",
    )
    assert (error.retryable, error.escalate) == (False, False)


def test_formula_error_translation_context_is_optional() -> None:
    error = FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", "m", "h").to_kernel_error(
        quantity="q"
    )
    assert error.quantity == "q"
    assert error.formula is None
    assert error.retryable is True


def test_formula_error_with_wrong_category_for_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="missing_input"):
        FormulaError(ErrorCategory.NOT_CONVERGED, "missing_input", "m", "h")


def test_internal_error_from_exception_leaks_no_exception_text() -> None:
    """ADR 0019: str(exc) can carry paths and internals; it goes to the log only."""
    error = internal_error_from_exception(
        ZeroDivisionError("/secret/path"), quantity="q", formula="f", application="a", world="f=w"
    )
    assert error.category is ErrorCategory.INTERNAL
    assert error.code == "internal"
    assert error.message == "Internal error (ZeroDivisionError) while computing `q`."
    assert "/secret/path" not in error.model_dump_json()
    assert error.hint == "Report it; attach input and provenance."
    assert error.escalate is True
    assert error.detail == {}
    assert (error.quantity, error.formula, error.application, error.world) == ("q", "f", "a", "f=w")


def test_invalid_category_is_rejected() -> None:
    with pytest.raises(ValidationError):
        KernelError.model_validate(
            {"code": "internal", "category": "nope", "message": "m", "hint": "h"}
        )


def test_non_mapping_input_is_rejected() -> None:
    with pytest.raises(ValidationError):
        KernelError.model_validate("not a mapping")


@pytest.mark.parametrize(
    ("causes", "match"),
    [
        (["text"], "objects"),
        ([{"quantity": "a"}], "string quantity"),
        ([{"quantity": 1, "code": "timeout"}], "string quantity"),
        ([{"quantity": "a", "code": "made_up"}], "no root code"),
        ([{"quantity": "a", "code": "upstream_failed"}], "no root code"),
    ],
)
def test_upstream_failed_with_malformed_causes_is_rejected(causes: JsonValue, match: str) -> None:
    with pytest.raises(ValidationError, match=match):
        _upstream(retryable=False, escalate=False, detail={"causes": causes})


def test_aggregate_hint_lists_several_roots() -> None:
    result = aggregate_upstream([_err("a"), _err("b")], quantity="q")
    assert result.hint == "Fix `a`, `b` first."
    assert aggregate_upstream([_err("a")], quantity="q").hint == "Fix `a` first."


def test_internal_error_logs_the_exception_text_at_error_level(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The text and traceback go to the log only, with the call context in ``extra``."""
    exc = ZeroDivisionError("/secret/path")
    with caplog.at_level(logging.ERROR, logger="aero_kernel.errors"):
        internal_error_from_exception(
            exc,
            quantity="q",
            formula="f",
            application="a",
            world="f=w",
            call_id="c1",
            scope="tenant",
        )
    records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(records) == 1
    record = records[0]
    assert "/secret/path" in record.getMessage()
    assert record.exc_info is not None
    assert record.exc_info[1] is exc
    assert (record.call_id, record.scope) == ("c1", "tenant")  # type: ignore[attr-defined]  # ``extra`` attributes are set dynamically on the record
    assert (record.quantity, record.formula, record.application, record.world) == (  # type: ignore[attr-defined]  # ``extra`` attributes are set dynamically on the record
        "q",
        "f",
        "a",
        "f=w",
    )


def test_internal_error_hides_the_exception_text_everywhere() -> None:
    error = internal_error_from_exception(ValueError("/secret/path"), quantity="q")
    assert "/secret/path" not in error.message
    assert "/secret/path" not in error.hint
    assert "/secret/path" not in json.dumps(error.detail)


def test_json_schema_validation_mode_makes_flags_optional_without_a_default() -> None:
    schema = KernelError.model_json_schema(mode="validation")
    for name in ("retryable", "escalate"):
        assert name not in schema["required"]
        assert "default" not in schema["properties"][name]
        assert "category table" in schema["properties"][name]["description"]


def test_json_schema_serialization_mode_requires_flags() -> None:
    schema = KernelError.model_json_schema(mode="serialization")
    assert {"retryable", "escalate"} <= set(schema["required"])


def test_catalogue_holds_exactly_the_codes_the_architecture_names() -> None:
    """The table is closed: a warning code or a new code must not slip in."""
    assert set(CODE_CATALOGUE) == {category.value for category in ErrorCategory} | {
        "missing_input",
        "unresolved_airfoil",
        "target_above_method_maximum",
        "precondition_violated",
        "postcondition_violated",
        "continuous_uncertainty",
        "non_scalar_result",
    }


@pytest.mark.parametrize("field", ["message", "hint"])
def test_formula_error_rejects_empty_message_or_hint_at_the_raise_site(field: str) -> None:
    message, hint = ("" if field == "message" else "m"), ("" if field == "hint" else "h")
    with pytest.raises(ValueError, match=field):
        FormulaError(ErrorCategory.NOT_CONVERGED, "not_converged", message, hint)


def test_formula_error_rejects_non_json_detail_at_the_raise_site() -> None:
    """A numpy scalar is not JSON; it must fail in __init__, not later in to_kernel_error."""
    with pytest.raises(ValueError, match="detail"):
        FormulaError(
            ErrorCategory.NOT_CONVERGED,
            "not_converged",
            "m",
            "h",
            {"v": np.int64(3)},  # pyright: ignore[reportArgumentType]  # the wrong type is the point
        )


def test_formula_error_accepts_json_detail() -> None:
    exc = FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "m", "h", {"v": [1, 2.5, None, "x"]}
    )
    assert exc.to_kernel_error(quantity="q").detail == {"v": [1, 2.5, None, "x"]}


def test_aggregate_message_quotes_the_quantity_and_the_roots() -> None:
    result = aggregate_upstream([_err("a"), _err("b")], quantity="q")
    assert result.message == "`q` has no value because `a`, `b` failed."


def test_aggregate_names_a_quantity_once_when_two_roots_share_it() -> None:
    result = aggregate_upstream(
        [
            _err("a", ErrorCategory.NOT_CONVERGED),
            _err("a", ErrorCategory.TIMEOUT),
            _err("b", ErrorCategory.NOT_CONVERGED),
        ],
        quantity="q",
    )
    assert result.detail == {
        "causes": [
            {"quantity": "a", "code": "not_converged"},
            {"quantity": "a", "code": "timeout"},
            {"quantity": "b", "code": "not_converged"},
        ]
    }
    assert result.hint == "Fix `a`, `b` first."
    assert result.message == "`q` has no value because `a`, `b` failed."


# ---- world assignment (ch. 8.13) ----------------------------------------------------------


def _err_in_world(world: str) -> KernelError:
    return KernelError(
        code="not_converged",
        category=ErrorCategory.NOT_CONVERGED,
        world=world,
        message="m",
        hint="h",
    )


@pytest.mark.parametrize("world", ["neutral-point=avl", "neutral-point=avl,roll-rate=aerobuildup"])
def test_kernel_error_accepts_canonical_world(world: str) -> None:
    assert _err_in_world(world).world == world


@pytest.mark.parametrize(
    "world",
    [
        "avl",
        "roll-rate=aerobuildup,neutral-point=avl",
        "neutral-point=avl,neutral-point=avl",
        "neutral-point",
        "neutral-point=avl,",
    ],
)
def test_kernel_error_rejects_malformed_world(world: str) -> None:
    with pytest.raises(ValidationError, match="world"):
        _err_in_world(world)


def test_world_helpers_live_in_errors() -> None:
    assert parse_world_assignment("a-b=c_d") == {"a-b": "c_d"}
    assert format_world_assignment({"z": "y", "a": "b"}) == "a=b,z=y"
