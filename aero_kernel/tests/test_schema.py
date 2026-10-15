"""Tests for the result types (ARCHITECTURE ch. 5, 8.2, 8.3, 8.4; scenarios Q3, Q15, Q23, Q26, Q31)."""

import pytest
from aero_kernel.schema import (
    WARNING_CATALOGUE,
    Interval,
    KernelWarning,
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
