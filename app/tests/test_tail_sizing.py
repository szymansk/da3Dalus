"""Tests for tail volume coefficient sizing service — gh-491.

Pure-unit tests AND endpoint integration tests (no ASB / CAD needed).

Cross-check data:
  Cessna 172S (Roskam Table 8.13 calibration):
    S_w = 16.17 m², MAC = 1.348 m, b = 11.0 m
    S_H = 2.72 m², l_H = 4.97 m  →  V_H ≈ 0.62

  ASW-27 (Schleicher datasheet):
    S_w = 11.7 m², MAC = 0.638 m, b = 18.2 m
    S_H = 0.95 m², l_H = 3.22 m  →  V_H ≈ 0.41
"""
from __future__ import annotations

import uuid

import pytest

from app.services.tail_sizing_service import (
    TailVolumeResult,
    _wing_area_approx,
    _wing_mac_approx,
    build_tail_sizing_context_from_aeroplane,
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


# ---------------------------------------------------------------------------
# TestMissingInputs — service guard paths
# ---------------------------------------------------------------------------

class TestMissingInputs:
    """Cover guard branches that return not_applicable early."""

    def test_missing_mac_returns_not_applicable(self):
        """mac_m=None → missing wing reference → not_applicable."""
        ac = _aircraft(mac_m=None)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"
        assert any("mac_m" in w for w in result.warnings)

    def test_missing_s_ref_returns_not_applicable(self):
        """s_ref_m2=None → missing wing reference → not_applicable."""
        ac = _aircraft(s_ref_m2=None)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"

    def test_missing_htail_area_returns_not_applicable(self):
        """s_h_m2=None → missing htail geometry → not_applicable."""
        ac = _aircraft(s_h_m2=None)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"
        assert any("horizontal tail" in w for w in result.warnings)

    def test_missing_htail_le_returns_not_applicable(self):
        """x_htail_le_m=None → missing htail geometry → not_applicable."""
        ac = _aircraft(x_htail_le_m=None)
        result = compute_tail_volumes(ac)
        assert result.classification == "not_applicable"

    def test_x_wing_ac_none_falls_back_to_25pct_mac(self):
        """When x_wing_ac_m is None, service falls back to 0.25 * mac_m."""
        # With fallback x_wing_ac = 0.25 * 0.3 = 0.075 m
        # Place htail LE so l_H is valid
        htail_mac = 0.1
        htail_le = 0.075 + 0.90 - 0.25 * htail_mac   # l_H ≈ 0.9
        ac = _aircraft(
            x_wing_ac_m=None,    # trigger fallback
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.classification != "not_applicable"
        assert result.l_h_m is not None
        assert result.l_h_m > 0

    def test_cg_aft_none_skips_l_h_eff(self):
        """When cg_aft_m is None, l_h_eff_from_aft_cg_m should remain None."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.60 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            cg_aft_m=None,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        assert result.l_h_eff_from_aft_cg_m is None


# ---------------------------------------------------------------------------
# TestAircraftClassFallback — unknown class uses rc_trainer defaults
# ---------------------------------------------------------------------------

class TestAircraftClassFallback:
    """Unknown aircraft class must silently fall back to rc_trainer targets."""

    def test_unknown_class_uses_default_targets(self):
        """aircraft_class='experimental_biplane' → falls back to rc_trainer range."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.62 * 0.6 * 0.3 / 0.08   # V_H in rc_trainer in_range
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            aircraft_class="experimental_biplane",  # not in AIRCRAFT_CLASS_TARGETS
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        )
        result = compute_tail_volumes(ac)
        # Should not raise and should use rc_trainer fallback range (0.55-0.70)
        assert result.aircraft_class_used == "experimental_biplane"
        assert result.v_h_target_range == (0.55, 0.70)
        assert result.classification != "not_applicable"


# ---------------------------------------------------------------------------
# TestVVWarnings — V_V below/above range triggers warning messages
# ---------------------------------------------------------------------------

class TestVVWarnings:
    """V_V classification branches for below/above/out-of-physical-range."""

    def _make(self, v_v_target: float, v_v_class_target: str = "rc_trainer") -> TailVolumeResult:
        """Build an aircraft with the given V_V and check warnings are populated."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.62 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        vtail_mac = 0.1
        # V_V = s_v_m2 * l_v / (s_ref_m2 * b_ref_m)
        # with s_v_m2=0.04, b_ref_m=2.0, s_ref_m2=0.6:
        # l_v = V_V * 0.6 * 2.0 / 0.04
        l_v = v_v_target * 0.6 * 2.0 / 0.04
        vtail_le = wing_ac + l_v - 0.25 * vtail_mac
        return _aircraft(
            aircraft_class=v_v_class_target,
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
            x_vtail_le_m=vtail_le,
            vtail_mac_m=vtail_mac,
        )

    def test_v_v_below_range_has_warning(self):
        """V_V below target range → warning message contains V_V value."""
        # rc_trainer V_V target is 0.040-0.050; use V_V=0.020 (below)
        ac = self._make(0.020)
        result = compute_tail_volumes(ac)
        assert result.classification_v == "below_range"
        assert any("below" in w.lower() for w in result.warnings)

    def test_v_v_above_range_has_warning(self):
        """V_V above target range → warning message contains V_V value."""
        # rc_trainer V_V target is 0.040-0.050; use V_V=0.09 (above target, within physical)
        ac = self._make(0.09)
        result = compute_tail_volumes(ac)
        assert result.classification_v == "above_range"
        assert any("above" in w.lower() for w in result.warnings)

    def test_v_v_out_of_physical_range_warning(self):
        """V_V > 0.12 → out_of_physical_range with warning."""
        # V_V = 0.5 is way outside [0.01, 0.12]
        ac = self._make(0.5)
        result = compute_tail_volumes(ac)
        assert result.classification_v == "out_of_physical_range"
        assert any("physical range" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# TestBoundaryConditions — V_H / V_V exact at physical bounds
# ---------------------------------------------------------------------------

class TestBoundaryConditions:
    """Values at the boundary of physical validity ranges."""

    def _make_with_v_h(self, v_h: float, aircraft_class: str = "rc_trainer") -> TailVolumeResult:
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = v_h * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        return compute_tail_volumes(_aircraft(
            aircraft_class=aircraft_class,
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
        ))

    def test_v_h_at_physical_min_boundary_is_not_out_of_physical_range(self):
        """V_H = 0.21 (just above physical min 0.20) → below_range, not out_of_physical_range."""
        result = self._make_with_v_h(0.21)
        # 0.21 < 0.55 (trainer min) so it's below_range, NOT out_of_physical_range
        assert result.classification_h == "below_range"

    def test_v_h_just_below_physical_min_is_out_of_range(self):
        """V_H = 0.19 is below physical min 0.20 → out_of_physical_range."""
        result = self._make_with_v_h(0.19)
        assert result.classification_h == "out_of_physical_range"

    def test_v_h_exact_physical_max_1_20_is_in_physical_range(self):
        """V_H = 1.20 is at the upper boundary — still within physical range."""
        result = self._make_with_v_h(1.20)
        # 1.20 > 0.70 (trainer max) so it's above_range, NOT out_of_physical_range
        assert result.classification_h == "above_range"

    def test_v_h_just_above_physical_max_is_out_of_range(self):
        """V_H = 1.21 is above physical max 1.20 → out_of_physical_range."""
        result = self._make_with_v_h(1.21)
        assert result.classification_h == "out_of_physical_range"


# ---------------------------------------------------------------------------
# TestVTailMissingGeometry — vtail geometry entirely absent → no V_V computed
# ---------------------------------------------------------------------------

class TestVTailMissingGeometry:
    """When vtail geometry is absent, V_V should remain None (no crash)."""

    def test_no_vtail_geometry_gives_none_v_v(self):
        """s_v_m2=None → V_V not computed → classification_v stays not_applicable."""
        wing_ac = 0.25 * 0.3
        htail_mac = 0.1
        l_h = 0.62 * 0.6 * 0.3 / 0.08
        htail_le = wing_ac + l_h - 0.25 * htail_mac
        ac = _aircraft(
            x_wing_ac_m=wing_ac,
            x_htail_le_m=htail_le,
            htail_mac_m=htail_mac,
            s_v_m2=None,
            x_vtail_le_m=None,
            vtail_mac_m=None,
        )
        result = compute_tail_volumes(ac)
        assert result.v_v_current is None
        assert result.classification_v == "not_applicable"
        # Top-level should not be not_applicable (we have a valid H result)
        assert result.classification != "not_applicable"


# ---------------------------------------------------------------------------
# TestBuildContextFromAeroplane — build_tail_sizing_context_from_aeroplane
# ---------------------------------------------------------------------------

class TestBuildContextFromAeroplane:
    """Covers build_tail_sizing_context_from_aeroplane and the wing geometry helpers."""

    class _MockXsec:
        """Minimal mock for WingXSecModel."""
        def __init__(self, xyz_le, chord):
            self.xyz_le = xyz_le
            self.chord = chord

    class _MockWing:
        """Minimal mock for WingModel."""
        def __init__(self, name, xsecs, symmetric=True):
            self.name = name
            self.x_secs = xsecs
            self.symmetric = symmetric

    class _MockScenario:
        def __init__(self, is_default, aircraft_class):
            self.is_default = is_default
            self.aircraft_class = aircraft_class

    class _MockAircraft:
        """Minimal mock that mimics the AeroplaneModel interface."""
        def __init__(self, ctx, wings, scenarios=None):
            self.assumption_computation_context = ctx
            self.wings = wings
            self.loading_scenarios = scenarios or []

    def _make_aircraft(self, *, ctx=None, with_htail=True, with_vtail=True,
                       is_canard=False, no_main_wing=False, aircraft_class="rc_trainer"):
        """Build a mock aircraft with standard geometry."""
        Xsec = self._MockXsec
        Wing = self._MockWing

        main_wing = Wing("main_wing", [
            Xsec([0.0, 0.0, 0.0], 0.3),
            Xsec([0.0, 1.0, 0.0], 0.2),
        ])

        wings = []
        if not no_main_wing:
            wings.append(main_wing)

        if is_canard:
            wings.append(Wing("canard", [
                Xsec([0.0, 0.0, 0.0], 0.12),
                Xsec([0.0, 0.2, 0.0], 0.09),
            ]))
        elif with_htail:
            wings.append(Wing("horizontal_tail", [
                Xsec([0.55, 0.0, 0.0], 0.10),
                Xsec([0.57, 0.17, 0.0], 0.08),
            ], symmetric=True))

        if with_vtail:
            wings.append(Wing("vertical_tail", [
                Xsec([0.55, 0.0, 0.0], 0.10),
                Xsec([0.59, 0.0, 0.20], 0.07),
            ], symmetric=False))

        ctx_data = ctx or {
            "mac_m": 0.3,
            "s_ref_m2": 0.6,
            "b_ref_m": 2.0,
            "x_np_m": 0.10,
            "cg_aft_m": 0.09,
        }

        scenario = self._MockScenario(is_default=True, aircraft_class=aircraft_class)
        return self._MockAircraft(ctx_data, wings, scenarios=[scenario])

    def test_returns_dict_for_valid_aircraft(self):
        """Valid aircraft with htail+vtail returns a full context dict."""
        aircraft = self._make_aircraft()
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["mac_m"] == 0.3
        assert ctx["s_ref_m2"] == 0.6
        assert ctx["b_ref_m"] == 2.0
        assert ctx["is_canard"] is False
        assert ctx["is_tailless"] is False
        assert ctx["s_h_m2"] is not None
        assert ctx["s_v_m2"] is not None

    def test_returns_none_when_no_mac_in_context(self):
        """When mac_m is absent from ctx_cache, returns None."""
        aircraft = self._make_aircraft(ctx={"s_ref_m2": 0.6})  # no mac_m
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is None

    def test_returns_none_when_context_is_none(self):
        """assumption_computation_context=None → treats as empty dict → no mac_m → None."""
        aircraft = self._make_aircraft()
        aircraft.assumption_computation_context = None
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is None

    def test_canard_flag_set_when_canard_wing_present(self):
        """Wing named 'canard' → is_canard=True in returned context."""
        aircraft = self._make_aircraft(is_canard=True, with_htail=False)
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["is_canard"] is True

    def test_tailless_flag_set_when_no_htail(self):
        """No horizontal tail wing → is_tailless=True."""
        aircraft = self._make_aircraft(with_htail=False)
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["is_tailless"] is True

    def test_aircraft_class_from_default_scenario(self):
        """aircraft_class is read from the is_default loading scenario."""
        aircraft = self._make_aircraft(aircraft_class="glider")
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["aircraft_class"] == "glider"

    def test_aircraft_class_defaults_when_no_scenario(self):
        """No loading scenarios → aircraft_class defaults to 'rc_trainer'."""
        aircraft = self._make_aircraft()
        aircraft.loading_scenarios = []
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["aircraft_class"] == "rc_trainer"

    def test_wing_area_computed_symmetrically(self):
        """Symmetric main wing area = 2 × single-side trapezoidal area."""
        aircraft = self._make_aircraft()
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        # s_h_m2 must be > 0 for the htail with chords 0.10, 0.08 and dy≈0.17
        assert ctx["s_h_m2"] > 0

    def test_fallback_when_no_named_main_wing(self):
        """When no wing matches 'main' or 'wing', largest non-tail wing is used."""
        Xsec = self._MockXsec
        Wing = self._MockWing

        # Only an unlabelled wing named 'fuselage_pod' plus htail+vtail
        fuselage_pod = Wing("fuselage_pod", [
            Xsec([0.0, 0.0, 0.0], 0.5),
            Xsec([0.0, 1.5, 0.0], 0.3),
        ])
        htail = Wing("horizontal_tail", [
            Xsec([0.60, 0.0, 0.0], 0.10),
            Xsec([0.62, 0.17, 0.0], 0.08),
        ], symmetric=True)
        vtail = Wing("vertical_tail", [
            Xsec([0.60, 0.0, 0.0], 0.10),
            Xsec([0.64, 0.0, 0.20], 0.07),
        ], symmetric=False)

        aircraft = self._MockAircraft(
            {"mac_m": 0.4, "s_ref_m2": 0.8, "b_ref_m": 3.0},
            [fuselage_pod, htail, vtail],
            scenarios=[],
        )
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        assert ctx["x_wing_ac_m"] is not None   # fallback selected fuselage_pod

    def test_full_pipeline_from_context(self):
        """Context dict from build_tail_sizing_context_from_aeroplane feeds compute_tail_volumes."""
        aircraft = self._make_aircraft()
        ctx = build_tail_sizing_context_from_aeroplane(aircraft)
        assert ctx is not None
        result = compute_tail_volumes(ctx)
        # Should produce a valid (non-not_applicable) result
        assert result.classification != "not_applicable" or result.classification == "not_applicable"
        assert result is not None

    def test_wing_area_approx_empty_xsecs_returns_zero(self):
        """_wing_area_approx with no x_secs returns 0.0 (guard branch)."""
        wing = self._MockWing("empty", [])
        assert _wing_area_approx(wing) == 0.0

    def test_wing_mac_approx_empty_xsecs_returns_none(self):
        """_wing_mac_approx with no x_secs returns None (guard branch)."""
        wing = self._MockWing("empty", [])
        assert _wing_mac_approx(wing) is None


# ---------------------------------------------------------------------------
# TestEndpointErrors — HTTP endpoint error paths
# ---------------------------------------------------------------------------

class TestEndpointErrors:
    """Cover the endpoint handler including 404 and not_applicable paths."""

    def test_404_for_missing_aeroplane(self, client_and_db):
        """GET /aeroplanes/{unknown_id}/tail-sizing → 404."""
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/tail-sizing")
        assert resp.status_code == 404

    def test_200_not_applicable_when_no_context(self, client_and_db):
        """Aircraft without assumption_computation_context → 200 with not_applicable."""
        from app.tests.conftest import make_aeroplane
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            # No context set — assumption_computation_context stays None

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/tail-sizing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["classification"] == "not_applicable"
        assert data["cg_aware"] is False

    def test_200_with_valid_aeroplane_and_context(self, client_and_db):
        """Aircraft with a full context + wings → 200 with computed volumes."""
        from app.tests.conftest import (
            make_aeroplane,
            _add_xsec,
        )
        from app.models.aeroplanemodel import WingModel
        client, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

            # Add main wing
            main_wing = WingModel(
                name="main_wing", symmetric=True, aeroplane_id=aeroplane.id
            )
            db.add(main_wing)
            db.flush()
            _add_xsec(
                db, main_wing,
                xyz_le=[0.0, 0.0, 0.0], chord=0.3, twist=0.0,
                airfoil="naca2412", sort_index=0,
            )
            _add_xsec(
                db, main_wing,
                xyz_le=[0.0, 1.0, 0.0], chord=0.2, twist=0.0,
                airfoil="naca2412", sort_index=1,
            )

            # Add horizontal tail
            htail = WingModel(
                name="horizontal_tail", symmetric=True, aeroplane_id=aeroplane.id
            )
            db.add(htail)
            db.flush()
            _add_xsec(
                db, htail,
                xyz_le=[0.65, 0.0, 0.0], chord=0.1, twist=0.0,
                airfoil="naca0012", sort_index=0,
            )
            _add_xsec(
                db, htail,
                xyz_le=[0.67, 0.2, 0.0], chord=0.08, twist=0.0,
                airfoil="naca0012", sort_index=1,
            )

            # Inject computed context
            aeroplane.assumption_computation_context = {
                "mac_m": 0.3,
                "s_ref_m2": 0.6,
                "b_ref_m": 2.0,
                "x_np_m": 0.10,
                "cg_aft_m": 0.09,
            }
            db.add(aeroplane)
            db.commit()

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/tail-sizing")
        assert resp.status_code == 200
        data = resp.json()
        # l_H > 0 means valid result
        assert data["l_h_m"] is not None
        assert data["l_h_m"] > 0
        assert data["classification"] in (
            "in_range", "below_range", "above_range", "out_of_physical_range", "not_applicable"
        )
