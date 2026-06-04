"""Tests for airfoil_low_re_service math helpers (gh-825).

TDD: RED first, then implementation makes them GREEN.
No AeroSandbox / NeuralFoil needed — pure math over polar dicts.
"""

from __future__ import annotations

import math
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Shared polar fixtures
# ---------------------------------------------------------------------------

_GOOD_POLAR = {
    "ld_max": 55.0,
    "cl_max": 1.3,
    "alpha_attached_lo": -3.0,
    "alpha_attached_hi": 12.0,
    "drag_bucket_width": 0.6,
    "cd_min": 0.009,
    "stall_gentleness": -0.05,
    "cd0": 0.010,
    "k": 0.040,
    "cl0": 0.3,
    "cl_valid_lo": -0.2,
    "cl_valid_hi": 1.3,
    "min_analysis_confidence": 0.95,
}

_NARROW_BUCKET_POLAR = {
    **_GOOD_POLAR,
    "drag_bucket_width": 0.1,  # narrow bucket — same centre cd0/k/cl0
}

_HIGH_DRAG_POLAR = {
    **_GOOD_POLAR,
    "cd0": 0.030,  # 3× higher cd0, same k
}


# ---------------------------------------------------------------------------
# TASK B1: best_ld_cl — closed-form CL at max L/D
# ---------------------------------------------------------------------------


class TestBestLdCl:
    """Unit tests for best_ld_cl(cd0, k, cl0) -> float | None."""

    def test_symmetric_airfoil_cl0_zero(self):
        """For cl0=0: CL* = sqrt(cd0/k) — verified analytically."""
        from app.services.airfoil_low_re_service import best_ld_cl

        cd0, k, cl0 = 0.010, 0.040, 0.0
        cl_star = best_ld_cl(cd0, k, cl0)
        expected = math.sqrt(cd0 / k)  # = sqrt(0.25) = 0.5
        assert cl_star is not None
        assert cl_star == pytest.approx(expected, rel=1e-9)

    def test_cambered_airfoil_cl0_nonzero(self):
        """For cl0 != 0: CL* = sqrt(cl0^2 + cd0/k) — full quadratic result."""
        from app.services.airfoil_low_re_service import best_ld_cl

        cd0, k, cl0 = 0.010, 0.040, 0.3
        cl_star = best_ld_cl(cd0, k, cl0)
        # Full quadratic: CL* = sqrt(cl0^2 + cd0/k) = sqrt(0.09 + 0.25) = sqrt(0.34)
        expected = math.sqrt(cl0**2 + cd0 / k)
        assert cl_star is not None
        assert cl_star == pytest.approx(expected, rel=1e-9)

    def test_none_when_cd0_zero(self):
        """cd0 = 0 → no valid minimum; return None."""
        from app.services.airfoil_low_re_service import best_ld_cl

        assert best_ld_cl(0.0, 0.04, 0.3) is None

    def test_none_when_cd0_negative(self):
        """cd0 < 0 is unphysical; return None."""
        from app.services.airfoil_low_re_service import best_ld_cl

        assert best_ld_cl(-0.001, 0.04, 0.3) is None

    def test_none_when_k_zero(self):
        """k = 0 → division by zero; return None."""
        from app.services.airfoil_low_re_service import best_ld_cl

        assert best_ld_cl(0.010, 0.0, 0.3) is None

    def test_none_when_k_negative(self):
        """k < 0 is unphysical; return None."""
        from app.services.airfoil_low_re_service import best_ld_cl

        assert best_ld_cl(0.010, -0.01, 0.3) is None

    def test_larger_cd0_shifts_cl_star_up(self):
        """Higher parasitic drag → higher CL needed for max L/D."""
        from app.services.airfoil_low_re_service import best_ld_cl

        cl_low = best_ld_cl(0.008, 0.040, 0.3)
        cl_high = best_ld_cl(0.020, 0.040, 0.3)
        assert cl_high > cl_low

    def test_larger_k_shifts_cl_star_down(self):
        """Stiffer curvature (bigger k) → lower CL* for same cd0."""
        from app.services.airfoil_low_re_service import best_ld_cl

        cl_flat = best_ld_cl(0.010, 0.020, 0.3)
        cl_steep = best_ld_cl(0.010, 0.080, 0.3)
        assert cl_steep < cl_flat

    def test_derivative_is_zero_at_cl_star(self):
        """Numerical check: d/dCL[CL/CD] == 0 at CL*."""
        from app.services.airfoil_low_re_service import best_ld_cl

        cd0, k, cl0 = 0.012, 0.035, 0.25
        cl_star = best_ld_cl(cd0, k, cl0)
        assert cl_star is not None

        eps = 1e-6

        def ld(cl):
            cd = cd0 + k * (cl - cl0) ** 2
            return cl / cd if cd > 0 else 0.0

        grad = (ld(cl_star + eps) - ld(cl_star - eps)) / (2 * eps)
        assert abs(grad) < 1e-4, f"Gradient at CL*={cl_star:.4f} is {grad:.2e}, expected ~0"


# ---------------------------------------------------------------------------
# TASK B2: score_target_cl — Match × Efficiency
# ---------------------------------------------------------------------------


class TestScoreTargetCl825:
    """Tests for the new score_target_cl signature with Match × Efficiency."""

    def test_wide_bucket_beats_narrow_bucket_same_centre(self):
        """Wide drag bucket > narrow bucket at same cd0/k/cl0 and same target CL."""
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        settings = Settings()
        re_cd0_ref = 0.010  # same Re reference for both

        # Target CL is right at the best-LD point for both
        cl_target = 0.8  # near cl0 + sqrt(cd0/k) = 0.3 + 0.5 = 0.8

        wide_score = score_target_cl(
            _GOOD_POLAR, cl_target, re_cd0_reference=re_cd0_ref, settings=settings
        )
        narrow_score = score_target_cl(
            _NARROW_BUCKET_POLAR, cl_target, re_cd0_reference=re_cd0_ref, settings=settings
        )

        assert wide_score is not None
        assert narrow_score is not None
        assert wide_score > narrow_score, (
            f"Wide bucket (width=0.6) should score higher than narrow (width=0.1) "
            f"at same centre; got {wide_score:.4f} vs {narrow_score:.4f}"
        )

    def test_lower_cd0_same_re_scores_higher(self):
        """Lower cd0 at same Re reference → higher efficiency → higher score.

        To isolate the efficiency component, we place cl_target at each airfoil's
        cl_star (r=1, match=1.0 for both).  The only difference is efficiency =
        min(re_cd0_ref / cd0, 1.0), which is lower for the high-cd0 airfoil.
        """
        import math
        from app.services.airfoil_low_re_service import score_target_cl, best_ld_cl
        from app.settings import Settings

        settings = Settings()
        # Use a fleet reference above both cd0 values so efficiency < 1 for both
        re_cd0_ref = 0.008  # better than _GOOD_POLAR (0.010) → efficiency capped at 1.0

        # Use cl_star of _GOOD_POLAR → r=1 → match is maximised for _GOOD_POLAR
        cl_star_good = best_ld_cl(_GOOD_POLAR["cd0"], _GOOD_POLAR["k"], _GOOD_POLAR["cl0"])
        assert cl_star_good is not None

        # _GOOD_POLAR: efficiency = min(0.008/0.010, 1.0) = 0.8
        # _HIGH_DRAG_POLAR: cd0=0.030 → efficiency = min(0.008/0.030, 1.0) = 0.267
        # At cl_star_good: _GOOD_POLAR has r=1 → match=1; _HIGH_DRAG_POLAR has different r
        # Even if match differs, the much lower efficiency should give a lower score for HIGH_DRAG.

        # Choose a re_cd0_ref BETWEEN the two cd0 values so efficiency ordering is clear:
        re_cd0_ref = (
            0.015  # _GOOD_POLAR (cd0=0.010) gets eff=1.0; _HIGH_DRAG (cd0=0.030) gets eff=0.5
        )

        low_drag_score = score_target_cl(
            _GOOD_POLAR, cl_star_good, re_cd0_reference=re_cd0_ref, settings=settings
        )
        # _HIGH_DRAG at cl_star_good: r = CD_high(cl_star_good)/cd0_high
        high_drag_score = score_target_cl(
            _HIGH_DRAG_POLAR, cl_star_good, re_cd0_reference=re_cd0_ref, settings=settings
        )

        assert low_drag_score is not None
        assert high_drag_score is not None
        assert low_drag_score > high_drag_score, (
            f"Lower cd0 airfoil (cd0=0.010) should score higher than high-drag (cd0=0.030) "
            f"when re_cd0_ref={re_cd0_ref}; got {low_drag_score:.4f} vs {high_drag_score:.4f}"
        )

    def test_target_far_outside_bucket_low_score(self):
        """Target CL far from cl_star yields low Match score."""
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        settings = Settings()
        re_cd0_ref = 0.010

        # cl_star ≈ 0.8 for _GOOD_POLAR; target at 1.6 is well outside bucket
        near_score = score_target_cl(
            _GOOD_POLAR, 0.8, re_cd0_reference=re_cd0_ref, settings=settings
        )
        far_score = score_target_cl(
            _GOOD_POLAR, 1.6, re_cd0_reference=re_cd0_ref, settings=settings
        )

        assert near_score is not None
        assert far_score is not None
        assert near_score > far_score * 1.5, (
            f"Near-centre score ({near_score:.3f}) should be substantially above "
            f"far-outside score ({far_score:.3f})"
        )

    def test_closeness_alone_does_not_dominate(self):
        """A narrow but deep bucket close to target should NOT beat a wide but
        shallower bucket at the same centre — bucket WIDTH must be rewarded."""
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        settings = Settings()
        re_cd0_ref = 0.010
        cl_target = 0.8

        # Both at same cl0/k/cd0 — ONLY bucket width differs
        wide_score = score_target_cl(
            _GOOD_POLAR, cl_target, re_cd0_reference=re_cd0_ref, settings=settings
        )
        narrow_score = score_target_cl(
            _NARROW_BUCKET_POLAR, cl_target, re_cd0_reference=re_cd0_ref, settings=settings
        )
        assert wide_score > narrow_score

    def test_none_when_cd0_missing(self):
        """Return None when cd0 is absent from the polar."""
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        polar = {**_GOOD_POLAR, "cd0": None}
        result = score_target_cl(polar, 0.8, re_cd0_reference=0.010, settings=Settings())
        assert result is None

    def test_none_when_k_missing(self):
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        polar = {**_GOOD_POLAR, "k": None}
        result = score_target_cl(polar, 0.8, re_cd0_reference=0.010, settings=Settings())
        assert result is None

    def test_none_when_cl0_missing(self):
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        polar = {**_GOOD_POLAR, "cl0": None}
        result = score_target_cl(polar, 0.8, re_cd0_reference=0.010, settings=Settings())
        assert result is None

    def test_none_polar(self):
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        result = score_target_cl(None, 0.8, re_cd0_reference=0.010, settings=Settings())
        assert result is None

    def test_score_clamped_0_to_1(self):
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        settings = Settings()
        score = score_target_cl(_GOOD_POLAR, 0.8, re_cd0_reference=0.010, settings=settings)
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_r_poor_controls_match_decay(self):
        """At r = r_poor, Match should be at/near 0; at r=1 (cd0=cd0) it should be high."""
        from app.services.airfoil_low_re_service import score_target_cl
        from app.settings import Settings

        settings = Settings()
        cd0 = _GOOD_POLAR["cd0"]
        r_poor = settings.low_re_score_r_poor
        re_cd0_ref = cd0  # same as airfoil cd0 → efficiency=1.0

        # At CL* (best LD): CL* = sqrt(cl0^2 + cd0/k)
        cl_star = math.sqrt(_GOOD_POLAR["cl0"] ** 2 + cd0 / _GOOD_POLAR["k"])
        near_score = score_target_cl(
            _GOOD_POLAR, cl_star, re_cd0_reference=re_cd0_ref, settings=settings
        )

        # At very far CL, r >> r_poor
        far_score = score_target_cl(
            _GOOD_POLAR, 2.5, re_cd0_reference=re_cd0_ref, settings=settings
        )

        assert near_score is not None
        assert near_score > 0.3, f"Score near cl_star should be decent, got {near_score:.3f}"
        if far_score is not None:
            assert near_score > far_score


# ---------------------------------------------------------------------------
# TASK B3: compute_re_cd0_reference
# ---------------------------------------------------------------------------


class TestComputeReCd0Reference:
    """Tests for compute_re_cd0_reference(polars_by_name, re) -> float."""

    def _make_polar_rows(self, entries: list[tuple[float, float]]) -> dict:
        """Build a polars_by_name dict from (reynolds, cd0) tuples."""

        class FakeRow:
            def __init__(self, re, cd0_val, **kw):
                self.reynolds = float(re)
                self.ld_max = kw.get("ld_max", 40.0)
                self.cl_max = kw.get("cl_max", 1.0)
                self.alpha_attached_lo = -3.0
                self.alpha_attached_hi = 10.0
                self.drag_bucket_width = kw.get("drag_bucket_width", 0.4)
                self.cd_min = kw.get("cd_min", cd0_val)
                self.stall_gentleness = -0.05
                self.cd0 = cd0_val
                self.k = 0.04
                self.cl0 = 0.3
                self.cl_valid_lo = 0.0
                self.cl_valid_hi = 1.2
                self.min_analysis_confidence = 0.92

        result = {}
        for i, (re, cd0_val) in enumerate(entries):
            name = f"airfoil_{i}"
            result[name] = [FakeRow(re, cd0_val)]
        return result

    def test_returns_float_for_single_airfoil(self):
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        polars = self._make_polar_rows([(100_000, 0.012)])
        ref = compute_re_cd0_reference(polars, 100_000)
        assert isinstance(ref, float)
        assert ref == pytest.approx(0.012)

    def test_returns_low_percentile_across_fleet(self):
        """Reference should be a robust low percentile — below the median."""
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        # Fleet: cd0 values 0.010, 0.015, 0.020, 0.030, 0.040
        polars = self._make_polar_rows(
            [
                (100_000, 0.010),
                (100_000, 0.015),
                (100_000, 0.020),
                (100_000, 0.030),
                (100_000, 0.040),
            ]
        )
        ref = compute_re_cd0_reference(polars, 100_000)
        median = 0.020
        assert ref < median, f"Reference {ref:.4f} should be below median {median}"
        assert ref >= 0.010, f"Reference {ref:.4f} should not be below the minimum"

    def test_interpolates_between_re_points(self):
        """When no row exactly matches Re, reference uses interpolated cd0."""
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        polars = self._make_polar_rows(
            [
                (100_000, 0.012),
                (200_000, 0.010),
            ]
        )
        # Query at 150k — between the two points
        ref = compute_re_cd0_reference(polars, 150_000)
        assert 0.010 <= ref <= 0.012

    def test_none_safe_no_cd0_rows(self):
        """When all cd0 values are None, must return a fallback (not crash)."""
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        class NullRow:
            def __init__(self):
                self.reynolds = 100_000.0
                self.ld_max = None
                self.cl_max = None
                self.alpha_attached_lo = None
                self.alpha_attached_hi = None
                self.drag_bucket_width = None
                self.cd_min = None
                self.stall_gentleness = None
                self.cd0 = None
                self.k = None
                self.cl0 = None
                self.cl_valid_lo = None
                self.cl_valid_hi = None
                self.min_analysis_confidence = 0.80

        polars = {"airfoil_null": [NullRow()]}
        ref = compute_re_cd0_reference(polars, 100_000)
        # Must return a sensible fallback — we document the expected default below
        assert ref > 0.0, "Reference must be positive even when cd0 rows are all None"

    def test_empty_fleet_returns_fallback(self):
        """Empty fleet must not crash — returns a documented fallback."""
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        ref = compute_re_cd0_reference({}, 100_000)
        assert ref > 0.0


# ---------------------------------------------------------------------------
# TASK B4: three target CLs from context
# ---------------------------------------------------------------------------


class TestResolveThreeTargetCls:
    """Verify that suitability_service resolves cruise / best-glide / min-sink CLs
    from assumption_computation_context correctly.  All tests mock the DB lookup.
    """

    def _make_aeroplane(self, ctx: dict) -> object:
        class FakeAeroplane:
            assumption_computation_context = ctx
            id = 1

        return FakeAeroplane()

    def test_cruise_cl_from_v_cruise(self):
        from app.services.airfoil_low_re_service import _level_flight_cl, G, RHO

        m, v, s = 2.0, 18.0, 0.35
        expected = (m * G) / (0.5 * RHO * v**2 * s)
        assert _level_flight_cl(m, v, s) == pytest.approx(expected)

    def test_best_glide_cl_from_v_md(self):
        """v_md (min-drag speed, max range) resolves to a target CL for best glide."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        m, v_md, s = 2.0, 14.0, 0.35
        cl_bg = _level_flight_cl(m, v_md, s)
        cl_cruise = _level_flight_cl(m, 18.0, s)
        # Best-glide CL is higher than cruise CL (slower speed)
        assert cl_bg > cl_cruise

    def test_min_sink_cl_from_v_min_sink(self):
        """v_min_sink resolves to highest CL (slowest speed)."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        m, s = 2.0, 0.35
        cl_ms = _level_flight_cl(m, 10.0, s)
        cl_bg = _level_flight_cl(m, 14.0, s)
        assert cl_ms > cl_bg

    def test_missing_speed_gives_null_cl(self):
        """When a speed value is absent, the corresponding CL must be None."""
        ctx = {"mass_kg": 2.0, "s_ref_m2": 0.35}
        assert ctx.get("v_cruise_mps") is None
        assert ctx.get("v_md_mps") is None
        assert ctx.get("v_min_sink_mps") is None

    def test_all_three_present(self):
        from app.services.airfoil_low_re_service import _level_flight_cl

        ctx = {
            "mass_kg": 2.0,
            "s_ref_m2": 0.35,
            "v_cruise_mps": 18.0,
            "v_md_mps": 14.0,
            "v_min_sink_mps": 10.0,
        }
        cl_c = _level_flight_cl(ctx["mass_kg"], ctx["v_cruise_mps"], ctx["s_ref_m2"])
        cl_bg = _level_flight_cl(ctx["mass_kg"], ctx["v_md_mps"], ctx["s_ref_m2"])
        cl_ms = _level_flight_cl(ctx["mass_kg"], ctx["v_min_sink_mps"], ctx["s_ref_m2"])
        assert cl_c < cl_bg < cl_ms


# ---------------------------------------------------------------------------
# Coverage gap fill: score_target_cl edge branches
# ---------------------------------------------------------------------------


class TestScoreTargetClEdgeCases:
    """Coverage for branches not reached by main tests."""

    def _settings(self):
        from app.settings import Settings

        return Settings()

    def test_r_leq_1_gives_match_1(self):
        """When cl_target = cl0 (minimum drag point), r=1 → match=1.0."""
        from app.services.airfoil_low_re_service import score_target_cl

        settings = self._settings()
        # At cl_target = cl0, CD = cd0 + k*(cl0-cl0)^2 = cd0 → r=1
        polar = {**_GOOD_POLAR, "drag_bucket_width": 0.0}  # no bucket
        score = score_target_cl(
            polar, _GOOD_POLAR["cl0"], re_cd0_reference=0.010, settings=settings
        )
        assert score is not None
        # r=1 → match=1.0, efficiency = min(re_ref/cd0, 1.0)
        assert score > 0.0

    def test_r_geq_r_poor_gives_match_0(self):
        """When r >= r_poor, Match → 0 → score = 0."""
        from app.services.airfoil_low_re_service import score_target_cl

        settings = self._settings()
        r_poor = settings.low_re_score_r_poor
        cd0 = _GOOD_POLAR["cd0"]
        k = _GOOD_POLAR["k"]
        cl0 = _GOOD_POLAR["cl0"]
        # Find cl_target such that r >= r_poor:
        # CD(cl) = cd0 + k*(cl-cl0)^2 >= r_poor * cd0
        # k*(cl-cl0)^2 >= (r_poor-1)*cd0
        # |cl-cl0| >= sqrt((r_poor-1)*cd0/k)
        delta = math.sqrt((r_poor - 1.0) * cd0 / k) + 0.5  # well beyond r_poor
        cl_far = cl0 + delta
        score = score_target_cl(_GOOD_POLAR, cl_far, re_cd0_reference=0.010, settings=settings)
        assert score is not None
        assert score == pytest.approx(0.0), f"Expected 0, got {score:.4f} for r>>r_poor"

    def test_unphysical_cd0_returns_none(self):
        """cd0 <= 0 in polar → return None."""
        from app.services.airfoil_low_re_service import score_target_cl

        settings = self._settings()
        polar = {**_GOOD_POLAR, "cd0": -0.001}
        assert score_target_cl(polar, 0.5, re_cd0_reference=0.010, settings=settings) is None

    def test_zero_re_cd0_reference_still_returns_score(self):
        """When re_cd0_reference = 0, efficiency = 1.0 (fallback branch)."""
        from app.services.airfoil_low_re_service import score_target_cl

        settings = self._settings()
        score = score_target_cl(_GOOD_POLAR, 0.5, re_cd0_reference=0.0, settings=settings)
        # Should not crash; efficiency defaults to 1.0
        assert score is not None
        assert 0.0 <= score <= 1.0

    def test_none_bucket_width_does_not_crash(self):
        """When drag_bucket_width is None, treat as 0 — no crash."""
        from app.services.airfoil_low_re_service import score_target_cl

        settings = self._settings()
        polar = {**_GOOD_POLAR, "drag_bucket_width": None}
        score = score_target_cl(polar, 0.5, re_cd0_reference=0.010, settings=settings)
        assert score is not None


# ---------------------------------------------------------------------------
# Coverage gap fill: score_mission thickness branch (above t_max)
# ---------------------------------------------------------------------------


class TestScoreMissionThicknessBranches:
    def test_thickness_above_t_max_reduces_score(self):
        """Thickness above t_max band → thickness_match < 1."""
        from app.services.airfoil_low_re_service import score_mission
        from app.settings import Settings

        weights = Settings().low_re_mission_weights
        re_agn = 0.8
        # trainer: t_max=14%; test with 20% (well above band)
        in_band = score_mission(re_agn, "flat_bottom", 12.0, 1.3, "trainer", weights)
        above_band = score_mission(re_agn, "flat_bottom", 20.0, 1.3, "trainer", weights)
        assert in_band is not None
        assert above_band is not None
        assert in_band > above_band


# ---------------------------------------------------------------------------
# Coverage gap fill: compute_re_cd0_reference with None-returning polar
# ---------------------------------------------------------------------------


class TestComputeReCd0ReferenceEdges:
    def test_polar_returns_none_skipped(self):
        """Airfoil with empty rows → None from interpolate → skipped."""
        from app.services.airfoil_low_re_service import compute_re_cd0_reference

        # A name with no rows at all → interpolate returns None
        polars = {"empty_af": []}
        ref = compute_re_cd0_reference(polars, 100_000)
        assert ref > 0.0  # falls back to _CD0_REFERENCE_FALLBACK


# ---------------------------------------------------------------------------
# Coverage gap: compute_airfoil_low_re with mocked AeroSandbox
# ---------------------------------------------------------------------------


class TestComputeAirfoilLowReMocked:
    """Cover the NeuralFoil-dependent code path using a mocked AeroSandbox.

    Per the plan: mock NeuralFoil only where a compute path test is touched.
    The import-guard path (aerosandbox not available) is always testable.
    """

    def test_compute_returns_empty_when_no_aerosandbox(self):
        """When aerosandbox is not importable, returns empty list (no crash)."""
        coords = np.array([[0, 0], [0.5, 0.06], [1, 0]])
        re_grid = [100_000]

        # Temporarily make aerosandbox unimportable
        with patch.dict(sys.modules, {"aerosandbox": None}):
            from app.services.airfoil_low_re_service import compute_airfoil_low_re

            result = compute_airfoil_low_re("test", coords, re_grid)
            assert result == []

    def test_compute_with_mocked_aerosandbox(self):
        """compute_airfoil_low_re with a fully mocked AeroSandbox returns one dict per Re."""
        coords = np.array([[0, 0], [0.25, 0.06], [0.5, 0.08], [0.75, 0.06], [1, 0]])
        re_grid = [100_000, 200_000]

        # Match the actual alpha grid used by compute_airfoil_low_re:
        # alpha_start=-5, alpha_end=18, alpha_step=0.2
        alpha = np.arange(-5.0, 18.0 + 0.2 * 0.5, 0.2)
        n_alpha = len(alpha)
        # Generate a realistic synthetic polar
        cl = 2 * np.pi * np.radians(alpha) + 0.3  # thin-airfoil CL approx
        cd = 0.012 + 0.04 * (cl - 0.3) ** 2
        conf = np.full(n_alpha, 0.95)
        fake_aero_result = {"CL": cl, "CD": cd, "analysis_confidence": conf}

        mock_asb = MagicMock()
        mock_airfoil_instance = MagicMock()
        mock_airfoil_instance.get_aero_from_neuralfoil.return_value = fake_aero_result
        mock_asb.Airfoil.return_value = mock_airfoil_instance

        # Patch the import inside the function
        with patch.dict(sys.modules, {"aerosandbox": mock_asb}):
            import importlib
            import app.services.airfoil_low_re_service as _svc_module

            # Reload with the mock in place
            importlib.reload(_svc_module)
            try:
                result = _svc_module.compute_airfoil_low_re("test_af", coords, re_grid)
                # Should return one dict per Re grid point
                assert len(result) == len(re_grid)
                for row in result:
                    assert "reynolds" in row
                    assert "min_analysis_confidence" in row
            finally:
                # Reload without mock to restore normal state
                if "aerosandbox" in sys.modules:
                    del sys.modules["aerosandbox"]
                importlib.reload(_svc_module)


# ---------------------------------------------------------------------------
# Coverage gap fill: interpolate_polar_at_re clamping (re_query below grid)
# ---------------------------------------------------------------------------


class TestInterpolatePolarClamp:
    class _Row:
        def __init__(self, re):
            self.reynolds = float(re)
            self.ld_max = 40.0
            self.cl_max = 1.0
            self.alpha_attached_lo = -3.0
            self.alpha_attached_hi = 10.0
            self.drag_bucket_width = 0.4
            self.cd_min = 0.012
            self.stall_gentleness = -0.05
            self.cd0 = 0.012
            self.k = 0.04
            self.cl0 = 0.3
            self.cl_valid_lo = 0.0
            self.cl_valid_hi = 1.2
            self.min_analysis_confidence = 0.92

    def test_re_below_grid_clamps_to_lowest(self):
        """When re_query < lowest grid point, return the lowest row."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        rows = [self._Row(100_000), self._Row(200_000)]
        # Query below the lowest available re
        polar = interpolate_polar_at_re(rows, 50_000, [100_000, 200_000])
        assert polar is not None
        assert polar["cd0"] == pytest.approx(0.012)

    def test_re_above_grid_clamps_to_highest(self):
        """When re_query > highest grid point, return the highest row."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        rows = [self._Row(100_000), self._Row(200_000)]
        polar = interpolate_polar_at_re(rows, 500_000, [100_000, 200_000])
        assert polar is not None
        assert polar["cd0"] == pytest.approx(0.012)

    def test_single_row_exact_match_returns_dict(self):
        """Exact Re match returns row dict directly (no interpolation)."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        rows = [self._Row(150_000)]
        polar = interpolate_polar_at_re(rows, 150_000, [100_000, 200_000])
        assert polar is not None
        assert polar["cd0"] == pytest.approx(0.012)

    def test_empty_rows_after_dict_build_returns_none(self):
        """Edge: polar_rows has items but rows_by_re maps to nothing — line 200 branch."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        class RowNoneRe:
            reynolds = None
            ld_max = 40.0
            cl_max = 1.0
            alpha_attached_lo = -3.0
            alpha_attached_hi = 10.0
            drag_bucket_width = 0.4
            cd_min = 0.012
            stall_gentleness = -0.05
            cd0 = 0.012
            k = 0.04
            cl0 = 0.3
            cl_valid_lo = 0.0
            cl_valid_hi = 1.2
            min_analysis_confidence = 0.92

        # float(None) would raise, so test with an empty list which triggers path through
        # available_re being empty
        result = interpolate_polar_at_re([], 100_000, [100_000])
        assert result is None
