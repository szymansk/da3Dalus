"""Unit tests for the aircraft speed polar service (gh-841).

Tests are pure math — no DB, no AeroSandbox, no HTTP.

Hand-chosen reference aircraft (based on a typical RC trainer):
    mass_kg   = 2.0
    s_ref_m2  = 0.4
    AR        = 8.0
    e_oswald  = 0.80
    CD0       = 0.025

Derived reference values (closed-form):
    g         = 9.80665 m/s²
    W         = 2.0 × 9.80665 = 19.6133 N
    k         = 1 / (π × 8 × 0.8) ≈ 0.04974

    CL_bg     = sqrt(0.025 / 0.04974)     ≈ 0.70914
    CL_ms     = sqrt(3 × 0.025 / 0.04974) ≈ 1.22867  (= √3 × CL_bg)
    V_bg      = sqrt(2×W / (ρ×S×CL_bg))  ≈ 10.63 m/s
    V_ms      ≈ 0.759 × V_bg              ≈  8.08 m/s  (≈ 0.76 per spec)

    Sink_min  = V_ms × CD_ms / CL_ms
    CD_ms     = CD0 + k × CL_ms²  ≈ 0.025 + 0.04974 × 1.22867² ≈ 0.1000
    Sink_min  ≈ 8.08 × 0.1000 / 1.22867 ≈ 0.658 m/s

The tests verify all closed-form invariants within engineering tolerances.
"""

from __future__ import annotations

import math
import pytest

from app.services.speed_polar_service import (
    SpeedPolarResult,
    compute_speed_polar,
    is_missing,
    _check_inputs,
    _induced_drag_factor,
    _cl_best_glide,
    _cl_min_sink,
    _velocity,
    _sink_rate,
    _linspace,
)

# ---------------------------------------------------------------------------
# Reference aircraft (hand-chosen for easy mental cross-check)
# ---------------------------------------------------------------------------

REF = dict(
    mass_kg=2.0,
    s_ref_m2=0.40,
    ar=8.0,
    e_oswald=0.80,
    cd0=0.025,
)

G = 9.80665
RHO = 1.225


# ---------------------------------------------------------------------------
# Pure math helpers
# ---------------------------------------------------------------------------


class TestInducedDragFactor:
    def test_known_value(self):
        k = _induced_drag_factor(ar=8.0, e_oswald=0.80)
        expected = 1.0 / (math.pi * 8.0 * 0.80)
        assert abs(k - expected) < 1e-10

    def test_higher_ar_gives_lower_k(self):
        k_low = _induced_drag_factor(ar=4.0, e_oswald=0.8)
        k_high = _induced_drag_factor(ar=10.0, e_oswald=0.8)
        assert k_high < k_low

    def test_higher_e_gives_lower_k(self):
        k_low_e = _induced_drag_factor(ar=8.0, e_oswald=0.6)
        k_high_e = _induced_drag_factor(ar=8.0, e_oswald=1.0)
        assert k_high_e < k_low_e


class TestClBestGlide:
    def test_formula(self):
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(cd0=0.025, k=k)
        assert abs(cl_bg - math.sqrt(0.025 / k)) < 1e-12

    def test_reference_value(self):
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(0.025, k)
        assert abs(cl_bg - 0.7091) < 5e-4


class TestClMinSink:
    def test_is_sqrt3_times_cl_bg(self):
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(0.025, k)
        cl_ms = _cl_min_sink(0.025, k)
        assert abs(cl_ms - math.sqrt(3) * cl_bg) < 1e-10

    def test_greater_than_cl_bg(self):
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(0.025, k)
        cl_ms = _cl_min_sink(0.025, k)
        assert cl_ms > cl_bg


class TestVelocity:
    def test_higher_cl_gives_lower_v(self):
        w = 2.0 * G
        v_low_cl = _velocity(w, RHO, 0.40, cl=0.5)
        v_high_cl = _velocity(w, RHO, 0.40, cl=1.5)
        assert v_high_cl < v_low_cl

    def test_reference_v_bg(self):
        """V_bg ≈ 10.63 m/s for the reference aircraft."""
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(0.025, k)
        w = 2.0 * G
        v_bg = _velocity(w, RHO, 0.40, cl_bg)
        assert abs(v_bg - 10.63) < 0.10

    def test_v_ms_approx_0_76_v_bg(self):
        """V_ms / V_bg ≈ 0.76 as given in the spec."""
        k = _induced_drag_factor(8.0, 0.80)
        cl_bg = _cl_best_glide(0.025, k)
        cl_ms = _cl_min_sink(0.025, k)
        w = 2.0 * G
        v_bg = _velocity(w, RHO, 0.40, cl_bg)
        v_ms = _velocity(w, RHO, 0.40, cl_ms)
        ratio = v_ms / v_bg
        # Exact closed-form ratio is (3)^(-1/4) ≈ 0.7598 ≈ 0.76
        assert abs(ratio - 0.76) < 0.005


class TestSinkRate:
    def test_sink_positive(self):
        sink = _sink_rate(v_mps=10.0, cd0=0.025, k=0.05, cl=0.8)
        assert sink > 0

    def test_sink_at_cl_ms_is_minimum(self):
        """The sink rate is minimum at CL_ms — by definition."""
        k = _induced_drag_factor(8.0, 0.80)
        cl_ms = _cl_min_sink(0.025, k)
        w = 2.0 * G
        v_ms = _velocity(w, RHO, 0.40, cl_ms)
        sink_at_ms = _sink_rate(v_ms, 0.025, k, cl_ms)

        # Check several CL values on both sides
        for cl_other in [cl_ms * 0.7, cl_ms * 0.85, cl_ms * 1.15, cl_ms * 1.3]:
            v_other = _velocity(w, RHO, 0.40, cl_other)
            sink_other = _sink_rate(v_other, 0.025, k, cl_other)
            assert sink_at_ms < sink_other + 1e-6  # CL_ms is minimum


class TestLinspace:
    def test_endpoints(self):
        xs = _linspace(0.0, 1.0, 5)
        assert abs(xs[0] - 0.0) < 1e-12
        assert abs(xs[-1] - 1.0) < 1e-12

    def test_length(self):
        assert len(_linspace(0.0, 1.0, 10)) == 10

    def test_single_point(self):
        xs = _linspace(3.0, 9.0, 1)
        assert xs == [3.0]


class TestCheckInputs:
    def test_all_valid_returns_empty(self):
        missing = _check_inputs(mass_kg=2.0, s_ref_m2=0.4, ar=8.0, e_oswald=0.8, cd0=0.025)
        assert missing == []

    def test_none_mass_reported(self):
        missing = _check_inputs(mass_kg=None, s_ref_m2=0.4, ar=8.0, e_oswald=0.8, cd0=0.025)
        assert "mass_kg" in missing

    def test_zero_ar_reported(self):
        missing = _check_inputs(mass_kg=2.0, s_ref_m2=0.4, ar=0.0, e_oswald=0.8, cd0=0.025)
        assert "ar" in missing

    def test_negative_cd0_reported(self):
        missing = _check_inputs(mass_kg=2.0, s_ref_m2=0.4, ar=8.0, e_oswald=0.8, cd0=-0.01)
        assert "cd0" in missing

    def test_nan_reported(self):
        import math

        missing = _check_inputs(mass_kg=2.0, s_ref_m2=0.4, ar=math.nan, e_oswald=0.8, cd0=0.025)
        assert "ar" in missing

    def test_multiple_missing(self):
        missing = _check_inputs(mass_kg=None, s_ref_m2=None, ar=8.0, e_oswald=0.8, cd0=0.025)
        assert set(missing) == {"mass_kg", "s_ref_m2"}


# ---------------------------------------------------------------------------
# Full compute_speed_polar integration
# ---------------------------------------------------------------------------


class TestComputeSpeedPolar:
    def test_returns_speed_polar_result(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        assert not is_missing(result)

    def test_curve_lengths_consistent(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        assert len(result.v_mps) == len(result.sink_mps) == len(result.cl)
        assert len(result.v_mps) > 1

    def test_v_ascending(self):
        """Speed is monotonically increasing as CL decreases."""
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        for i in range(1, len(result.v_mps)):
            assert result.v_mps[i] >= result.v_mps[i - 1]

    def test_best_glide_cl_correct(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        k = _induced_drag_factor(REF["ar"], REF["e_oswald"])
        expected_cl_bg = _cl_best_glide(REF["cd0"], k)
        assert abs(result.best_glide.cl - expected_cl_bg) < 1e-4

    def test_min_sink_cl_is_sqrt3_times_cl_bg(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        ratio = result.min_sink.cl / result.best_glide.cl
        assert abs(ratio - math.sqrt(3)) < 1e-4

    def test_v_ms_approx_076_v_bg(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        ratio = result.min_sink.v_mps / result.best_glide.v_mps
        assert abs(ratio - 0.76) < 0.005

    def test_min_sink_has_lower_sink_than_best_glide(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        assert result.min_sink.sink_mps < result.best_glide.sink_mps

    def test_inputs_preserved_in_result(self):
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        assert result.inputs["mass_kg"] == REF["mass_kg"]
        assert result.inputs["cd0"] == REF["cd0"]

    def test_missing_mass_returns_missing_inputs(self):
        result = compute_speed_polar(mass_kg=None, s_ref_m2=0.4, ar=8.0, e_oswald=0.8, cd0=0.025)
        assert is_missing(result)

    def test_missing_cd0_returns_missing_inputs(self):
        result = compute_speed_polar(mass_kg=2.0, s_ref_m2=0.4, ar=8.0, e_oswald=0.8, cd0=None)
        assert is_missing(result)

    def test_all_missing_returns_missing_inputs(self):
        result = compute_speed_polar(mass_kg=None, s_ref_m2=None, ar=None, e_oswald=None, cd0=None)
        assert is_missing(result)
        assert len(result.missing) == 5  # type: ignore[union-attr]

    def test_sink_curve_shape_has_minimum(self):
        """Sink curve has a U-shape — minimum is in the middle, not at endpoints."""
        result = compute_speed_polar(**REF)
        assert isinstance(result, SpeedPolarResult)
        sinks = result.sink_mps
        min_idx = sinks.index(min(sinks))
        # Minimum should NOT be at the very first or very last point
        assert 0 < min_idx < len(sinks) - 1

    def test_custom_rho_changes_velocities(self):
        result_sl = compute_speed_polar(**REF, rho=1.225)
        result_alt = compute_speed_polar(**REF, rho=1.0)
        assert isinstance(result_sl, SpeedPolarResult)
        assert isinstance(result_alt, SpeedPolarResult)
        # Lower density → higher speed for same CL
        assert result_alt.best_glide.v_mps > result_sl.best_glide.v_mps


# ---------------------------------------------------------------------------
# Reynolds mode (gh-924) — polar markers must match the characteristic-speed
# chips: cd0(V)/e(V) from the polar_re_table, CL_max clamp, sweep truncation.
# ---------------------------------------------------------------------------


def _fallback_table(cl_max: float = 1.256) -> list[dict]:
    """All-fallback Re table → lookup_cd0_at_v returns 0.03, e returns 0.8."""
    return [
        {"re": 85000, "v_mps": 9.0, "cd0": None, "e_oswald": None,
         "cl_max": cl_max, "fallback_used": True},
        {"re": 170000, "v_mps": 18.0, "cd0": None, "e_oswald": None,
         "cl_max": cl_max, "fallback_used": True},
    ]


class TestComputeSpeedPolarReynolds:
    # eHawk-like high-AR glider: scalar cd0/e differ from the fallback table
    EH = dict(mass_kg=1.5, s_ref_m2=0.1999, ar=11.3, e_oswald=0.7916, cd0=0.02364)
    MAC = 0.1398
    CL_MAX = 1.256

    def test_uses_reynolds_cd0_not_passed_cd0(self):
        """Best-glide uses cd0(V)=0.03 from the fallback table, NOT cd0=0.02364."""
        res = compute_speed_polar(
            **self.EH, polar_re_table=_fallback_table(self.CL_MAX),
            mac_m=self.MAC, cl_max=self.CL_MAX,
        )
        assert isinstance(res, SpeedPolarResult)
        # Closed-form best-glide with the FALLBACK cd0=0.03, e=0.8:
        k = _induced_drag_factor(11.3, 0.8)
        cl_bg = _cl_best_glide(0.03, k)
        v_bg = _velocity(1.5 * G, RHO, 0.1999, cl_bg)
        assert res.best_glide.v_mps == pytest.approx(v_bg, abs=0.05)
        # And distinctly NOT the value the passed cd0=0.02364 would give
        v_bg_passed = _velocity(
            1.5 * G, RHO, 0.1999,
            _cl_best_glide(0.02364, _induced_drag_factor(11.3, 0.7916)),
        )
        assert abs(res.best_glide.v_mps - v_bg_passed) > 0.3

    def test_min_sink_clamped_to_v_stall(self):
        """CL_min_sink > CL_max → min-sink marker sits at V_stall, not sub-stall."""
        res = compute_speed_polar(
            **self.EH, polar_re_table=_fallback_table(self.CL_MAX),
            mac_m=self.MAC, cl_max=self.CL_MAX,
        )
        assert isinstance(res, SpeedPolarResult)
        v_stall = _velocity(1.5 * G, RHO, 0.1999, self.CL_MAX)
        assert res.min_sink.v_mps == pytest.approx(v_stall, abs=0.05)
        assert res.min_sink.cl == pytest.approx(self.CL_MAX, abs=1e-3)

    def test_sweep_does_not_go_below_v_stall(self):
        """Curve is truncated at CL_max — nothing plotted past stall."""
        res = compute_speed_polar(
            **self.EH, polar_re_table=_fallback_table(self.CL_MAX),
            mac_m=self.MAC, cl_max=self.CL_MAX,
        )
        assert isinstance(res, SpeedPolarResult)
        v_stall = _velocity(1.5 * G, RHO, 0.1999, self.CL_MAX)
        assert min(res.v_mps) >= v_stall - 0.05
        assert max(res.cl) <= self.CL_MAX + 1e-6

    def test_markers_match_chip_speeds_ehawk(self):
        """Regression for the reported bug: polar V_md/V_min_sink == the chips."""
        res = compute_speed_polar(
            **self.EH, polar_re_table=_fallback_table(self.CL_MAX),
            mac_m=self.MAC, cl_max=self.CL_MAX,
        )
        assert isinstance(res, SpeedPolarResult)
        # The chips (assumption_compute_service) report 11.4 / 9.8 for eHawk
        assert res.best_glide.v_mps == pytest.approx(11.4, abs=0.1)
        assert res.min_sink.v_mps == pytest.approx(9.8, abs=0.1)

    def test_legacy_mode_unchanged_without_table(self):
        """No polar_re_table → identical to the legacy closed-form path."""
        legacy = compute_speed_polar(**self.EH)
        with_clmax_only = compute_speed_polar(**self.EH)  # still legacy
        assert isinstance(legacy, SpeedPolarResult)
        # Legacy best-glide uses the PASSED cd0/e (no Reynolds override, no clamp)
        k = _induced_drag_factor(11.3, 0.7916)
        v_bg = _velocity(1.5 * G, RHO, 0.1999, _cl_best_glide(0.02364, k))
        assert legacy.best_glide.v_mps == pytest.approx(v_bg, abs=0.05)
        assert legacy.best_glide.v_mps == with_clmax_only.best_glide.v_mps
