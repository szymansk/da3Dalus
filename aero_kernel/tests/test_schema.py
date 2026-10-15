"""Tests for the result types (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4; scenarios Q3, Q15, Q23, Q26, Q31)."""

import pytest
from aero_kernel.errors import ErrorCategory
from aero_kernel.schema import (
    WARNING_CATALOGUE,
    Interval,
    KernelError,
    KernelWarning,
    QuantityResult,
    QuantityStatus,
    ReasonCode,
    WarningSeverity,
)
from pydantic import ValidationError


def make_warning(**overrides: object) -> KernelWarning:
    """Build a valid practice warning, with fields overridden."""
    fields: dict[str, object] = {
        "severity": "practice",
        "code": "default_target_used",
        "message": "target taken from the canon default",
        "origin": "approach-speed-margin-target",
    }
    return KernelWarning.model_validate(fields | overrides)


class TestKernelWarning:
    def test_accepts_valid_warning(self) -> None:
        warning = make_warning()
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.origin == "approach-speed-margin-target"
        assert warning.world is None
        assert warning.detail == {}

    @pytest.mark.parametrize("field", ["code", "message"])
    def test_rejects_empty_text(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_warning(**{field: ""})

    def test_origin_is_optional_but_not_empty(self) -> None:
        assert make_warning(origin=None).origin is None
        with pytest.raises(ValidationError):
            make_warning(origin="")

    def test_rejects_uncatalogued_code(self) -> None:
        with pytest.raises(ValidationError, match="catalogue"):
            make_warning(code="invented_code")

    def test_rejects_severity_contradicting_the_table(self) -> None:
        with pytest.raises(ValidationError, match="severity"):
            make_warning(severity="defect")

    def test_catalogue_holds_the_initial_codes(self) -> None:
        assert WARNING_CATALOGUE == {
            "conflicting_mass": WarningSeverity.PRACTICE,
            "default_target_used": WarningSeverity.PRACTICE,
            "deflection_without_flap": WarningSeverity.PRACTICE,
            "precondition_unchecked": WarningSeverity.PRACTICE,
            "precondition_violated": WarningSeverity.DEFECT,
            "postcondition_unchecked": WarningSeverity.PRACTICE,
            "postcondition_violated": WarningSeverity.DEFECT,
        }

    def test_carries_world_and_json_detail(self) -> None:
        warning = make_warning(world="neutral-point=avl", detail={"mass_kg": 2.5})
        assert warning.world == "neutral-point=avl"
        assert warning.detail == {"mass_kg": 2.5}

    def test_rejects_extra_field_and_is_frozen(self) -> None:
        with pytest.raises(ValidationError):
            make_warning(quantity="x")
        with pytest.raises(ValidationError):
            make_warning().code = "x"  # pyright: ignore[reportAttributeAccessIssue]  # frozen: assignment must fail


WORLDS = {"neutral-point=avl": 0.30, "neutral-point=textbook": 0.34}


class TestInterval:
    def test_accepts_min_max_matching_worlds(self) -> None:
        interval = Interval(min=0.30, max=0.34, worlds=WORLDS)
        assert interval.worlds == WORLDS

    def test_rejects_min_not_matching_worlds(self) -> None:
        with pytest.raises(ValidationError, match="min"):
            Interval(min=0.29, max=0.34, worlds=WORLDS)

    def test_rejects_max_not_matching_worlds(self) -> None:
        with pytest.raises(ValidationError, match="max"):
            Interval(min=0.30, max=0.40, worlds=WORLDS)

    def test_rejects_empty_worlds(self) -> None:
        with pytest.raises(ValidationError):
            Interval(min=0.0, max=0.0, worlds={})

    def test_single_world_is_a_zero_width_interval(self) -> None:
        interval = Interval(min=0.3, max=0.3, worlds={"neutral-point=avl": 0.3})
        assert interval.min == interval.max


def make_quantity(**overrides: object) -> QuantityResult:
    """Build a valid ``ok`` quantity with a value, with fields overridden."""
    fields: dict[str, object] = {
        "slug": "stall-speed",
        "unit": "m/s",
        "status": "ok",
        "value": 12.5,
    }
    return QuantityResult.model_validate(fields | overrides)


class TestQuantityResultOk:
    def test_ok_with_value(self) -> None:
        result = make_quantity()
        assert result.status is QuantityStatus.OK
        assert result.value == 12.5
        assert result.validated is False
        assert result.from_cache is False
        assert result.warnings == ()

    def test_ok_with_interval(self) -> None:
        result = make_quantity(value=None, interval=Interval(min=0.30, max=0.34, worlds=WORLDS))
        assert result.interval is not None

    def test_ok_rejects_value_and_interval_together(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            make_quantity(interval=Interval(min=0.30, max=0.34, worlds=WORLDS))

    def test_ok_rejects_neither_value_nor_interval(self) -> None:
        with pytest.raises(ValidationError, match="exactly one"):
            make_quantity(value=None)


def make_error() -> KernelError:
    """Build a valid ``missing_input`` error."""
    return KernelError(
        code="missing_input",
        category=ErrorCategory.INVALID_INPUT,
        quantity="stall-speed",
        message="aircraft-mass is missing",
        hint="Pass aircraft-mass.",
    )


class TestQuantityResultError:
    def test_error_with_error_and_no_value(self) -> None:
        result = make_quantity(status="error", value=None, error=make_error())
        assert result.error is not None
        assert result.error.code == "missing_input"

    def test_error_requires_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(status="error", value=None)

    def test_error_rejects_value(self) -> None:
        with pytest.raises(ValidationError, match="value"):
            make_quantity(status="error", error=make_error())

    def test_error_rejects_interval(self) -> None:
        with pytest.raises(ValidationError, match="value"):
            make_quantity(
                status="error",
                value=None,
                interval=Interval(min=0.30, max=0.34, worlds=WORLDS),
                error=make_error(),
            )

    def test_ok_rejects_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(error=make_error())


def make_reason(code: str) -> dict[str, str]:
    """Build the raw form of a reason."""
    return {"code": code, "message": "explained"}


class TestQuantityResultReason:
    @pytest.mark.parametrize(
        ("status", "code"),
        [
            ("not_applicable", "condition_not_met"),
            ("not_applicable", "not_given"),
            ("not_applicable", "depends_on_not_applicable"),
            ("skipped", "long_run_not_included"),
            ("skipped", "depends_on_skipped"),
        ],
    )
    def test_accepts_fitting_reason(self, status: str, code: str) -> None:
        result = make_quantity(status=status, value=None, reason=make_reason(code))
        assert result.reason is not None
        assert result.reason.code is ReasonCode(code)

    @pytest.mark.parametrize(
        ("status", "code"),
        [
            ("not_applicable", "long_run_not_included"),
            ("not_applicable", "depends_on_skipped"),
            ("skipped", "condition_not_met"),
            ("skipped", "not_given"),
            ("skipped", "depends_on_not_applicable"),
        ],
    )
    def test_rejects_reason_of_the_other_status(self, status: str, code: str) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(status=status, value=None, reason=make_reason(code))

    @pytest.mark.parametrize("status", ["not_applicable", "skipped"])
    def test_non_ok_status_requires_reason(self, status: str) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(status=status, value=None)

    def test_ok_rejects_reason(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(reason=make_reason("not_given"))

    def test_error_rejects_reason(self) -> None:
        with pytest.raises(ValidationError, match="reason"):
            make_quantity(
                status="error", value=None, error=make_error(), reason=make_reason("not_given")
            )

    def test_not_applicable_rejects_error(self) -> None:
        with pytest.raises(ValidationError, match="error"):
            make_quantity(
                status="not_applicable",
                value=None,
                error=make_error(),
                reason=make_reason("not_given"),
            )

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(ValidationError):
            make_quantity(
                status="skipped", value=None, reason={"code": "depends_on_skipped", "message": ""}
            )


class TestQuantityResultInvariants:
    def test_validated_can_not_be_true(self) -> None:
        with pytest.raises(ValidationError):
            make_quantity(validated=True)

    def test_rejects_duplicate_warning_key(self) -> None:
        with pytest.raises(ValidationError, match="duplicate"):
            make_quantity(warnings=[make_warning(), make_warning(message="again")])

    def test_same_code_and_origin_in_different_worlds_is_kept(self) -> None:
        result = make_quantity(
            warnings=[make_warning(world="a=1"), make_warning(world="a=2")],
        )
        assert len(result.warnings) == 2

    def test_same_code_with_different_origin_is_kept(self) -> None:
        result = make_quantity(warnings=[make_warning(), make_warning(origin="other")])
        assert len(result.warnings) == 2
