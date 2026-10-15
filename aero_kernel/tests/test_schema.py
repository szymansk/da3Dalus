"""Tests for the result types (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4; scenarios Q3, Q15, Q23, Q26, Q31)."""

import pytest
from aero_kernel.schema import DesignWarning, Interval, WarningSeverity
from pydantic import ValidationError


def make_warning(**overrides: object) -> DesignWarning:
    """Build a valid practice warning, with fields overridden."""
    fields: dict[str, object] = {
        "severity": "practice",
        "code": "default_target_used",
        "message": "target taken from the canon default",
        "quantity": "approach-speed",
        "origin": "approach-speed-margin-target",
    }
    return DesignWarning.model_validate(fields | overrides)


class TestDesignWarning:
    def test_accepts_valid_warning(self) -> None:
        warning = make_warning()
        assert warning.severity is WarningSeverity.PRACTICE
        assert warning.origin == "approach-speed-margin-target"

    @pytest.mark.parametrize("field", ["code", "message", "origin"])
    def test_rejects_empty_text(self, field: str) -> None:
        with pytest.raises(ValidationError):
            make_warning(**{field: ""})

    def test_rejects_unknown_severity(self) -> None:
        with pytest.raises(ValidationError):
            make_warning(severity="info")

    def test_rejects_extra_field_and_is_frozen(self) -> None:
        with pytest.raises(ValidationError):
            make_warning(extra=1)
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
