"""Tests for tail volume coefficient sizing service — gh-491.

All tests are pure-unit tests (no DB / ASB needed).

Cross-check data:
  Cessna 172S (Roskam Table 8.13 calibration):
    S_w = 16.17 m², MAC = 1.348 m, b = 11.0 m
    S_H = 2.72 m², l_H = 4.97 m  →  V_H ≈ 0.62

  ASW-27 (Schleicher datasheet):
    S_w = 11.7 m², MAC = 0.638 m, b = 18.2 m
    S_H = 0.95 m², l_H = 3.22 m  →  V_H ≈ 0.41
"""
from __future__ import annotations

import pytest

from app.services.tail_sizing_service import (
    TailVolumeResult,
    compute_tail_volumes,
)


# ---------------------------------------------------------------------------
# Minimal aircraft stand-ins for pure-unit tests
# ---------------------------------------------------------------------------

def _aircraft(
    *,
    mac_m: float = 0.3,
    s_ref_m2: float = 0.6,
    b_ref_m: float = 2.0,
    x_wing_ac_m: float | None = 0.07,
    x_np_m: float | None = 0.10,
    cg_aft_m: float | None = 0.09,
    # horizontal tail
    s_h_m2: float | None = 0.08,
    x_htail_le_m: float | None = 0.60,
    htail_mac_m: float | None = 0.12,
    # vertical tail
    s_v_m2: float | None = 0.04,
    x_vtail_le_m: float | None = 0.60,
    vtail_mac_m: float | None = 0.12,
    # aircraft class from the default scenario
    aircraft_class: str = "rc_trainer",
    # config flags
    is_canard: bool = False,
    is_tailless: bool = False,
    is_v_tail: bool = False,
):
    """Return a minimal dict mimicking the context fed to compute_tail_volumes."""
    return {
        "mac_m": mac_m,
        "s_ref_m2": s_ref_m2,
        "b_ref_m": b_ref_m,
        "x_wing_ac_m": x_wing_ac_m,
        "x_np_m": x_np_m,
        "cg_aft_m": cg_aft_m,
        "s_h_m2": s_h_m2,
        "x_htail_le_m": x_htail_le_m,
        "htail_mac_m": htail_mac_m,
        "s_v_m2": s_v_m2,
        "x_vtail_le_m": x_vtail_le_m,
        "vtail_mac_m": vtail_mac_m,
        "aircraft_class": aircraft_class,
        "is_canard": is_canard,
        "is_tailless": is_tailless,
        "is_v_tail": is_v_tail,
    }


# ---------------------------------------------------------------------------
# TestTailVolumeFormula — cross-checks against published data
# ---------------------------------------------------------------------------

class TestTailVolumeFormula:
    """Verify formula V_H = S_H · l_H / (S_w · MAC) against real aircraft."""

    def test_v_h_cessna_172_within_5pct(self):
        """Cessna 172S: V_H ≈ 0.62 (Roskam Table 8.13)."""
        # S_w=16.17 m², MAC=1.348 m, S_H=2.72 m²
        # tail-AC at 0.25*htail_mac ahead of tail LE
        # l_H = x_htail_AC - x_wing_AC = 4.97 m (calibrated)
        # wing AC at x=0.337 (25% of 1.348 m from root LE at x=0)
        wing_ac = 0.25 * 1.348          # ≈ 0.337 m
        htail_mac = 0.6                 # reasonable stub
        htail_le = wing_ac + 4.97 - 0.25 * htail_mac  # place tail AC at correct distance
        ac = _aircraft(
            mac_m=1.348,
            s_ref_m2=16.17,
            b_ref_m=11.0,
            x_wing_ac_m=wing_ac,
            x_np_m=wing_ac + 0.05,     # slightly aft of AC
            cg_aft_m=wing_ac,
            s_h_m2=2.72,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
            s_v_m2=0.5,
            x_vtail_le_m=htail_le,
            vtail_mac_m=0.5,
            aircraft_class="rc_trainer",
        )
        result = compute_tail_volumes(ac)
        assert result is not None
        assert result.classification != "not_applicable"
        assert abs(result.v_h_current - 0.62) / 0.62 < 0.05, (
            f"V_H = {result.v_h_current:.4f}, expected ≈ 0.62 ±5%"
        )

    def test_v_h_asw27_within_5pct(self):
        """ASW-27: V_H ≈ 0.41 (Schleicher datasheet)."""
        wing_ac = 0.25 * 0.638
        htail_mac = 0.35
        htail_le = wing_ac + 3.22 - 0.25 * htail_mac
        ac = _aircraft(
            mac_m=0.638,
            s_ref_m2=11.7,
            b_ref_m=18.2,
            x_wing_ac_m=wing_ac,
            x_np_m=wing_ac + 0.03,
            cg_aft_m=wing_ac,
            s_h_m2=0.95,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
            s_v_m2=0.25,
            x_vtail_le_m=htail_le,
            vtail_mac_m=0.35,
            aircraft_class="glider",
        )
        result = compute_tail_volumes(ac)
        assert result is not None
        assert result.classification != "not_applicable"
        assert abs(result.v_h_current - 0.41) / 0.41 < 0.05, (
            f"V_H = {result.v_h_current:.4f}, expected ≈ 0.41 ±5%"
        )


# ---------------------------------------------------------------------------
# TestRecommendation — target-range per aircraft class
# ---------------------------------------------------------------------------

class TestRecommendation:
    """Verify that recommended S_H is computed from the right target range."""

    def test_aerobatic_class_uses_low_target(self):
        """rc_aerobatic target V_H = 0.35–0.55 → midpoint ≈ 0.45."""
        # Use a V_H that is in_range for aerobatic but below for trainer.
        # V_H = 0.40: in aerobatic range (0.35–0.55), below trainer range (0.55–0.70)
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        # l_H to give V_H ≈ 0.40: l_H = 0.40 * 0.6 * 0.3 / 0.08 = 0.9
        l_h = 0.40 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            aircraft_class="rc_aerobatic",
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification_h == "in_range", (
            f"Expected in_range for aerobatic but got {result.classification_h}"
        )

    def test_trainer_class_uses_high_target(self):
        """rc_trainer target V_H = 0.55–0.70 → V_H=0.40 should be below_range."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.40 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            aircraft_class="rc_trainer",
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification_h == "below_range", (
            f"Expected below_range for trainer but got {result.classification_h}"
        )

    def test_recommendation_uses_wing_to_tail_ac(self):
        """l_h_m must be wing-AC → tail-AC distance, not CG → tail-AC."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.90
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        # Place CG far from wing-AC to verify l_h_m ≠ l_h_eff_from_aft_cg_m
        cg_aft = wing_ac + 0.15   # ≠ wing_ac
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            cg_aft_m=cg_aft,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        # l_h_m should equal the wing-AC → tail-AC distance
        assert abs(result.l_h_m - l_h) < 0.01, (
            f"l_h_m={result.l_h_m:.4f}, expected≈{l_h:.4f}"
        )
        # l_h_eff_from_aft_cg_m should differ
        expected_eff = (wing_ac + l_h) - cg_aft
        assert abs(result.l_h_eff_from_aft_cg_m - expected_eff) < 0.01, (
            f"l_h_eff={result.l_h_eff_from_aft_cg_m:.4f}, expected≈{expected_eff:.4f}"
        )


# ---------------------------------------------------------------------------
# TestClassification — in_range / below_range / above_range / out_of_physical_range
# ---------------------------------------------------------------------------

class TestClassification:
    """Range and out-of-physical-range classification."""

    def _make_with_v_h(self, v_h: float, aircraft_class: str = "rc_trainer") -> TailVolumeResult:
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = v_h * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            aircraft_class=aircraft_class,
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        return compute_tail_volumes(ac)

    def test_v_h_below_range_warns(self):
        result = self._make_with_v_h(0.45, "rc_trainer")  # below 0.55–0.70
        assert result.classification_h == "below_range"

    def test_v_h_in_range_ok(self):
        result = self._make_with_v_h(0.60, "rc_trainer")  # in 0.55–0.70
        assert result.classification_h == "in_range"

    def test_v_h_above_range_warns(self):
        result = self._make_with_v_h(0.80, "rc_trainer")  # above 0.55–0.70
        assert result.classification_h == "above_range"

    def test_out_of_physical_range_v_h_2_0(self):
        """V_H = 2.0 ∉ [0.2, 1.2] → out_of_physical_range."""
        result = self._make_with_v_h(2.0, "rc_trainer")
        assert result.classification_h == "out_of_physical_range"

    def test_out_of_physical_range_v_v_0_5(self):
        """V_V = 0.5 ∉ [0.01, 0.12] → out_of_physical_range."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        # normal V_H
        l_h = 0.60 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        vtail_mac = 0.1
        # massively large V_V: l_v = 0.5 * 0.6 * 2.0 / 0.04 = 15 m
        l_v = 0.5 * 0.6 * 2.0 / 0.04
        vtail_le = wing_ac + l_v - 0.25 * vtail_mac
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
            x_vtail_le_m=vtail_le,
            vtail_mac_m=vtail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification_v == "out_of_physical_range"


# ---------------------------------------------------------------------------
# TestNotApplicable
# ---------------------------------------------------------------------------

class TestNotApplicable:
    def test_canard_returns_not_applicable(self):
        ac = _aircraft(is_canard=True)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"

    def test_tailless_returns_not_applicable(self):
        ac = _aircraft(is_tailless=True)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"

    def test_negative_l_h_returns_not_applicable(self):
        """Tail ahead of wing → canard-like → not_applicable."""
        # Tail AC before wing AC: x_htail_AC < x_wing_AC
        wing_ac = 0.50
        htail_mac = 0.1
        htail_le = 0.05  # tail well in front of wing
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"


# ---------------------------------------------------------------------------
# TestFallback — cg_aware flag
# ---------------------------------------------------------------------------

class TestFallback:
    def test_no_x_np_uses_wing_ac_only_cg_aware_false(self):
        """When x_np_m is None, still compute V_H but mark cg_aware=False."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.60 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            x_np_m=None,    # no polar yet
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification != "not_applicable"
        assert result.cg_aware is False

    def test_with_x_np_cg_aware_true(self):
        """When x_np_m is available, cg_aware=True."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.60 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            x_np_m=0.12,
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.cg_aware is True


# ---------------------------------------------------------------------------
# TestBrefInContext — sub-task: b_ref_m must be present in context
# ---------------------------------------------------------------------------

class TestBrefInContext:
    def test_b_ref_m_is_read_from_context(self):
        """Service must consume b_ref_m from context (not raise KeyError)."""
        ac = _aircraft(b_ref_m=11.0)
        result = compute_tail_volumes(ac)
        # As long as we don't get a KeyError, b_ref_m is consumed correctly.
        assert result is not None
        # Check that b_ref_m is passed through (affects V_V calculation)
        assert result.v_v_current is not None or result.classification == "not_applicable"


# ---------------------------------------------------------------------------
# TestSecondaryMetric — l_h_eff_from_aft_cg_m
# ---------------------------------------------------------------------------

class TestSecondaryMetric:
    def test_l_h_eff_from_aft_cg_returned_for_display(self):
        """l_h_eff_from_aft_cg_m = tail-AC.x - cg_aft_m (display-only)."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.60 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        cg_aft = wing_ac + 0.05  # slightly aft of wing AC
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            cg_aft_m=cg_aft,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        tail_ac_x = htail_le + 0.25 * htail_mac
        expected_eff = tail_ac_x - cg_aft
        assert abs(result.l_h_eff_from_aft_cg_m - expected_eff) < 0.001
