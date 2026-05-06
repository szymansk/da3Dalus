"""Tests for app.schemas.design_assumption — pure-logic schema tests."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.schemas.design_assumption import (
    DESIGN_CHOICE_PARAMS,
    PARAMETER_DEFAULTS,
    PARAMETER_UNITS,
    AssumptionRead,
    AssumptionSourceSwitch,
    AssumptionWrite,
    AssumptionsSummary,
    compute_divergence_pct,
    divergence_level,
)


# ---------------------------------------------------------------------------
# compute_divergence_pct
# ---------------------------------------------------------------------------


class TestComputeDivergencePct:
    def test_none_calculated_returns_none(self):
        assert compute_divergence_pct(1.5, None) is None

    def test_zero_calculated_returns_none(self):
        assert compute_divergence_pct(1.5, 0) is None

    def test_identical_values_returns_zero(self):
        assert compute_divergence_pct(1.5, 1.5) == 0.0

    def test_normal_divergence(self):
        # estimate=1.5, calculated=2.0 -> |1.5-2.0|/|2.0| * 100 = 25.0
        assert compute_divergence_pct(1.5, 2.0) == 25.0

    def test_small_divergence(self):
        # estimate=1.0, calculated=1.02 -> |1.0-1.02|/1.02 * 100 ~ 2.0 (rounded)
        result = compute_divergence_pct(1.0, 1.02)
        assert result == pytest.approx(2.0, abs=0.1)

    def test_negative_calculated_uses_abs(self):
        # calculated is negative: uses abs(calculated) for denominator
        result = compute_divergence_pct(1.0, -2.0)
        # |1.0 - (-2.0)| / |-2.0| * 100 = 3.0/2.0 * 100 = 150.0
        assert result == 150.0


# ---------------------------------------------------------------------------
# divergence_level
# ---------------------------------------------------------------------------


class TestDivergenceLevel:
    def test_none_returns_none_level(self):
        assert divergence_level(None) == "none"

    def test_zero_returns_none_level(self):
        assert divergence_level(0.0) == "none"

    def test_below_5_returns_none_level(self):
        assert divergence_level(4.9) == "none"

    def test_at_5_returns_info(self):
        assert divergence_level(5.0) == "info"

    def test_between_5_and_15_returns_info(self):
        assert divergence_level(10.0) == "info"

    def test_at_15_returns_warning(self):
        assert divergence_level(15.0) == "warning"

    def test_between_15_and_30_returns_warning(self):
        assert divergence_level(25.0) == "warning"

    def test_at_30_returns_warning(self):
        assert divergence_level(30.0) == "warning"

    def test_above_30_returns_alert(self):
        assert divergence_level(31.0) == "alert"

    def test_large_divergence_returns_alert(self):
        assert divergence_level(100.0) == "alert"


# ---------------------------------------------------------------------------
# AssumptionWrite
# ---------------------------------------------------------------------------


class TestAssumptionWrite:
    def test_valid_construction(self):
        w = AssumptionWrite(estimate_value=1.5)
        assert w.estimate_value == 1.5

    def test_zero_value(self):
        w = AssumptionWrite(estimate_value=0.0)
        assert w.estimate_value == 0.0

    def test_negative_value(self):
        w = AssumptionWrite(estimate_value=-1.0)
        assert w.estimate_value == -1.0

    def test_missing_value_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AssumptionWrite()


# ---------------------------------------------------------------------------
# AssumptionSourceSwitch
# ---------------------------------------------------------------------------


class TestAssumptionSourceSwitch:
    def test_estimate_source(self):
        s = AssumptionSourceSwitch(active_source="ESTIMATE")
        assert s.active_source == "ESTIMATE"

    def test_calculated_source(self):
        s = AssumptionSourceSwitch(active_source="CALCULATED")
        assert s.active_source == "CALCULATED"

    def test_invalid_source_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AssumptionSourceSwitch(active_source="INVALID")

    def test_missing_source_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AssumptionSourceSwitch()


# ---------------------------------------------------------------------------
# AssumptionRead
# ---------------------------------------------------------------------------


class TestAssumptionRead:
    def test_full_construction(self):
        now = datetime.now(timezone.utc)
        r = AssumptionRead(
            id=1,
            parameter_name="mass",
            estimate_value=1.5,
            calculated_value=1.6,
            calculated_source="weight_items",
            active_source="ESTIMATE",
            effective_value=1.5,
            divergence_pct=6.3,
            divergence_level="info",
            unit="kg",
            is_design_choice=False,
            updated_at=now,
        )
        assert r.id == 1
        assert r.parameter_name == "mass"
        assert r.estimate_value == 1.5
        assert r.calculated_value == 1.6
        assert r.calculated_source == "weight_items"
        assert r.active_source == "ESTIMATE"
        assert r.effective_value == 1.5
        assert r.divergence_pct == 6.3
        assert r.divergence_level == "info"
        assert r.unit == "kg"
        assert r.is_design_choice is False
        assert r.updated_at == now

    def test_minimal_construction(self):
        now = datetime.now(timezone.utc)
        r = AssumptionRead(
            id=2,
            parameter_name="cd0",
            estimate_value=0.03,
            active_source="ESTIMATE",
            effective_value=0.03,
            divergence_level="none",
            updated_at=now,
        )
        assert r.calculated_value is None
        assert r.calculated_source is None
        assert r.divergence_pct is None
        assert r.unit == ""
        assert r.is_design_choice is False


# ---------------------------------------------------------------------------
# AssumptionsSummary
# ---------------------------------------------------------------------------


class TestAssumptionsSummary:
    def test_empty_summary(self):
        s = AssumptionsSummary()
        assert s.assumptions == []
        assert s.warnings_count == 0

    def test_summary_with_assumptions(self):
        now = datetime.now(timezone.utc)
        a1 = AssumptionRead(
            id=1,
            parameter_name="mass",
            estimate_value=1.5,
            active_source="ESTIMATE",
            effective_value=1.5,
            divergence_level="none",
            updated_at=now,
        )
        s = AssumptionsSummary(assumptions=[a1], warnings_count=0)
        assert len(s.assumptions) == 1


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_parameter_defaults_has_six_entries(self):
        assert len(PARAMETER_DEFAULTS) == 6

    def test_parameter_units_has_six_entries(self):
        assert len(PARAMETER_UNITS) == 6

    def test_design_choice_params(self):
        assert "target_static_margin" in DESIGN_CHOICE_PARAMS
        assert "g_limit" in DESIGN_CHOICE_PARAMS
        assert "mass" not in DESIGN_CHOICE_PARAMS

    def test_all_defaults_have_units(self):
        for key in PARAMETER_DEFAULTS:
            assert key in PARAMETER_UNITS
