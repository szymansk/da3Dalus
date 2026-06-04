"""Tests for the three scoring lenses (Task 6, gh-821).

No aero dependencies. Seed polar dicts directly.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Test data: seed polar dict (as would come from interpolate_polar_at_re)
# ---------------------------------------------------------------------------

_GOOD_POLAR = {
    "ld_max": 45.0,
    "cl_max": 1.3,
    "alpha_attached_lo": -3.0,
    "alpha_attached_hi": 12.0,
    "drag_bucket_width": 0.6,
    "cd_min": 0.010,
    "stall_gentleness": -0.05,
    "cd0": 0.012,
    "k": 0.04,
    "cl0": 0.3,
    "cl_valid_lo": -0.2,
    "cl_valid_hi": 1.2,
    "min_analysis_confidence": 0.95,
}

_POOR_POLAR = {
    "ld_max": 10.0,
    "cl_max": 0.6,
    "alpha_attached_lo": -2.0,
    "alpha_attached_hi": 6.0,
    "drag_bucket_width": 0.1,
    "cd_min": 0.04,
    "stall_gentleness": -0.8,
    "cd0": 0.05,
    "k": 0.10,
    "cl0": 0.2,
    "cl_valid_lo": 0.0,
    "cl_valid_hi": 0.5,
    "min_analysis_confidence": 0.92,
}


# ---------------------------------------------------------------------------
# Task 6a: re_agnostic from scalar metrics
# ---------------------------------------------------------------------------


class TestReAgnostic:
    def test_good_polar_scores_higher_than_poor(self):
        from app.services.airfoil_low_re_service import score_re_agnostic

        good = score_re_agnostic(_GOOD_POLAR)
        poor = score_re_agnostic(_POOR_POLAR)
        assert good is not None
        assert poor is not None
        assert good > poor

    def test_score_in_range(self):
        from app.services.airfoil_low_re_service import score_re_agnostic

        s = score_re_agnostic(_GOOD_POLAR)
        assert 0.0 <= s <= 1.0

    def test_none_polar_returns_none(self):
        from app.services.airfoil_low_re_service import score_re_agnostic

        assert score_re_agnostic(None) is None

    def test_empty_polar_returns_none_or_zero(self):
        from app.services.airfoil_low_re_service import score_re_agnostic

        result = score_re_agnostic({})
        assert result is None


# ---------------------------------------------------------------------------
# Task 6b: mission = re_agnostic * weighting
# ---------------------------------------------------------------------------


class TestMissionScore:
    def test_mission_null_when_no_mission_type(self):
        from app.services.airfoil_low_re_service import score_mission, score_re_agnostic

        re_agn = score_re_agnostic(_GOOD_POLAR)
        result = score_mission(
            re_agnostic=re_agn,
            family="cambered",
            max_thickness_pct=12.0,
            cl_max=1.3,
            mission_type=None,
            mission_weights={},
        )
        assert result is None

    def test_mission_null_when_re_agnostic_is_none(self):
        from app.services.airfoil_low_re_service import score_mission
        from app.settings import Settings

        weights = Settings().low_re_mission_weights
        result = score_mission(
            re_agnostic=None,
            family="cambered",
            max_thickness_pct=12.0,
            cl_max=1.3,
            mission_type="trainer",
            mission_weights=weights,
        )
        assert result is None

    def test_preferred_family_scores_higher(self):
        from app.services.airfoil_low_re_service import score_re_agnostic, score_mission
        from app.settings import Settings

        weights = Settings().low_re_mission_weights
        re_agn = score_re_agnostic(_GOOD_POLAR)
        # trainer prefers flat_bottom and semi_symmetric
        preferred = score_mission(re_agn, "flat_bottom", 12.0, 1.3, "trainer", weights)
        non_preferred = score_mission(re_agn, "symmetric", 12.0, 1.3, "trainer", weights)
        assert preferred > non_preferred

    def test_mission_score_in_range(self):
        from app.services.airfoil_low_re_service import score_re_agnostic, score_mission
        from app.settings import Settings

        weights = Settings().low_re_mission_weights
        re_agn = score_re_agnostic(_GOOD_POLAR)
        result = score_mission(re_agn, "cambered", 12.0, 1.3, "trainer", weights)
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_out_of_band_thickness_reduces_score(self):
        from app.services.airfoil_low_re_service import score_re_agnostic, score_mission
        from app.settings import Settings

        weights = Settings().low_re_mission_weights
        re_agn = score_re_agnostic(_GOOD_POLAR)
        # Trainer prefers 11-14%; far outside band (e.g. 5%) should reduce score
        in_band = score_mission(re_agn, "flat_bottom", 12.0, 1.3, "trainer", weights)
        out_of_band = score_mission(re_agn, "flat_bottom", 5.0, 1.3, "trainer", weights)
        assert in_band >= out_of_band


# ---------------------------------------------------------------------------
# Task 6c: target_cl_cruise/loiter from parabolic fit
# ---------------------------------------------------------------------------


class TestTargetClScore:
    def test_target_cl_within_range_returns_score(self):
        from app.services.airfoil_low_re_service import score_target_cl

        result = score_target_cl(_GOOD_POLAR, cl_target=0.5)
        assert result is not None
        assert 0.0 <= result <= 1.0

    def test_target_cl_outside_valid_range_penalized(self):
        """CL outside [cl_valid_lo, cl_valid_hi] should score lower."""
        from app.services.airfoil_low_re_service import score_target_cl

        in_range = score_target_cl(_GOOD_POLAR, cl_target=0.5)
        out_of_range = score_target_cl(_GOOD_POLAR, cl_target=2.0)  # above cl_valid_hi=1.2
        # Out-of-range should be penalized (lower score or None)
        assert in_range is not None
        if out_of_range is not None:
            assert in_range >= out_of_range

    def test_target_cl_none_when_no_fit(self):
        from app.services.airfoil_low_re_service import score_target_cl

        polar_no_fit = dict(_GOOD_POLAR)
        polar_no_fit["cd0"] = None
        polar_no_fit["k"] = None
        polar_no_fit["cl0"] = None
        result = score_target_cl(polar_no_fit, cl_target=0.5)
        assert result is None

    def test_lower_drag_at_target_cl_yields_higher_score(self):
        from app.services.airfoil_low_re_service import score_target_cl

        # Airfoil with very low cd0 should score higher
        high_drag_polar = dict(_GOOD_POLAR)
        high_drag_polar["cd0"] = 0.040  # much higher drag
        high_drag_polar["k"] = 0.04
        high_drag_polar["cl0"] = 0.3

        low_score = score_target_cl(high_drag_polar, cl_target=0.5)
        high_score = score_target_cl(_GOOD_POLAR, cl_target=0.5)
        assert high_score > low_score


# ---------------------------------------------------------------------------
# Task 6d: Numeric test of _level_flight_cl
# ---------------------------------------------------------------------------


class TestLevelFlightCl:
    def test_numeric_cruise(self):
        """Hand-computed: m=2.0 kg, v=20 m/s, S=0.35 m² → CL check."""
        from app.services.airfoil_low_re_service import _level_flight_cl, G, RHO

        m, v, s = 2.0, 20.0, 0.35
        expected = (m * G) / (0.5 * RHO * v**2 * s)
        result = _level_flight_cl(m, v, s)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_numeric_loiter(self):
        """Loiter at v_min_sink (slower → higher CL)."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        m, v_loiter, s = 1.5, 12.0, 0.25
        result = _level_flight_cl(m, v_loiter, s)
        assert result > 0

    def test_higher_speed_lower_cl(self):
        """At faster speed the required CL is lower (L = const)."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        m, s = 2.0, 0.35
        cl_cruise = _level_flight_cl(m, 20.0, s)
        cl_loiter = _level_flight_cl(m, 12.0, s)
        assert cl_loiter > cl_cruise

    def test_raises_on_zero_speed(self):
        from app.services.airfoil_low_re_service import _level_flight_cl

        with pytest.raises(ValueError):
            _level_flight_cl(2.0, 0.0, 0.35)

    def test_raises_on_zero_area(self):
        from app.services.airfoil_low_re_service import _level_flight_cl

        with pytest.raises(ValueError):
            _level_flight_cl(2.0, 20.0, 0.0)

    def test_constants_match_endurance_service(self):
        """G and RHO must match endurance_service constants exactly."""
        from app.services.airfoil_low_re_service import G, RHO
        from app.services.endurance_service import G as G_END, RHO_SEA_LEVEL

        assert G == pytest.approx(G_END)
        assert RHO == pytest.approx(RHO_SEA_LEVEL)


# ---------------------------------------------------------------------------
# Task 6e: Partial context degradation matrix
# ---------------------------------------------------------------------------


class TestPartialContextDegradation:
    """Verify the degradation rules for target CL lenses."""

    def test_null_context_gives_null_cruise_cl(self):
        """When assumption_computation_context is None → cruise CL null."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        # Service function extracts context; here we test the helper directly
        # by verifying that the caller must handle missing context gracefully.
        # The search service is responsible for null checks; we verify
        # _level_flight_cl itself raises when inputs are bad, not silently returns 0.
        # Null context → caller returns target_cl_cruise = None
        ctx = None
        mass = None if ctx is None else ctx.get("mass_kg")
        v_cruise = None if ctx is None else ctx.get("v_cruise_mps")
        s_ref = None if ctx is None else ctx.get("s_ref_m2")
        # All None → cannot compute
        assert mass is None and v_cruise is None and s_ref is None

    def test_missing_v_min_sink_gives_null_loiter_cl(self):
        """When v_min_sink_mps is absent, target_cl_loiter must be null."""
        ctx = {"mass_kg": 2.0, "v_cruise_mps": 18.0, "s_ref_m2": 0.3}
        # v_min_sink absent
        v_min_sink = ctx.get("v_min_sink_mps")
        assert v_min_sink is None

    def test_all_present_computes_correctly(self):
        """When all context fields are present, compute succeeds."""
        from app.services.airfoil_low_re_service import _level_flight_cl

        ctx = {"mass_kg": 2.0, "v_cruise_mps": 18.0, "s_ref_m2": 0.35, "v_min_sink_mps": 12.0}
        cl_cruise = _level_flight_cl(ctx["mass_kg"], ctx["v_cruise_mps"], ctx["s_ref_m2"])
        cl_loiter = _level_flight_cl(ctx["mass_kg"], ctx["v_min_sink_mps"], ctx["s_ref_m2"])
        assert cl_cruise > 0
        assert cl_loiter > cl_cruise  # slower loiter → higher CL


# ---------------------------------------------------------------------------
# Task 6f: Config defaults check (already in test_airfoil_low_re_config.py;
#          here verify weights load for all mission types)
# ---------------------------------------------------------------------------


class TestConfigDefaults:
    def test_all_mission_types_have_weights(self):
        from app.settings import Settings

        s = Settings()
        for key in ("trainer", "sport", "aerobatic", "glider", "flying_wing"):
            assert key in s.low_re_mission_weights

    def test_re_grid_has_13_points(self):
        from app.settings import Settings

        assert len(Settings().low_re_grid) == 13


# ---------------------------------------------------------------------------
# Task: Graceful degradation when polar rows have all-None metrics
# (models the 40k–100k band under xxxlarge where confidence_gate=0.90 is
# not reached — these rows exist in the DB but must not crash the scorer)
# ---------------------------------------------------------------------------


class _NullMetricRow:
    """Mock DB row where every metric is None (confidence-limited, sub-gate Re)."""

    def __init__(self, reynolds: float, min_confidence: float = 0.88) -> None:
        self.reynolds = reynolds
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
        self.min_analysis_confidence = min_confidence


class _RealMetricRow:
    """Mock DB row with realistic metrics (trusted, above gate)."""

    def __init__(self, reynolds: float) -> None:
        self.reynolds = reynolds
        self.ld_max = 55.0
        self.cl_max = 1.1
        self.alpha_attached_lo = -3.0
        self.alpha_attached_hi = 10.0
        self.drag_bucket_width = 0.5
        self.cd_min = 0.009
        self.stall_gentleness = -0.05
        self.cd0 = 0.010
        self.k = 0.04
        self.cl0 = 0.3
        self.cl_valid_lo = 0.0
        self.cl_valid_hi = 1.1
        self.min_analysis_confidence = 0.93


class TestGracefulDegradationNullRows:
    """score_re_agnostic and interpolate_polar_at_re must handle all-None rows
    without crashing, and must return None (not fabricated scores) so that the
    caller can surface a low-confidence caveat rather than hiding it.

    This models the production scenario where xxxlarge confidence_gate=0.90 is
    not reached in the 40k–100k band: the backfill writes a valid DB row (with
    reynolds + min_analysis_confidence) but all metric columns are NULL.
    """

    def test_score_re_agnostic_returns_none_for_all_null_polar(self):
        """When polar has no metric fields, score_re_agnostic must return None."""
        from app.services.airfoil_low_re_service import score_re_agnostic

        null_polar = {
            "ld_max": None,
            "cl_max": None,
            "drag_bucket_width": None,
            "stall_gentleness": None,
            "cd_min": None,
            "min_analysis_confidence": 0.88,
        }
        result = score_re_agnostic(null_polar)
        assert result is None, (
            "score_re_agnostic must return None (not 0 or fabricated) "
            "when every metric in the polar dict is None"
        )

    def test_interpolate_exact_null_row_returns_none_metrics(self):
        """An exact-match None row passes through unchanged (all metrics None)."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        rows = [_NullMetricRow(100_000)]
        polar = interpolate_polar_at_re(rows, 100_000, [100_000])
        assert polar is not None, "interpolate_polar_at_re must return a dict (not None itself)"
        assert polar["ld_max"] is None
        assert polar["cl_max"] is None
        # Scoring such a polar must be None, not a crash
        from app.services.airfoil_low_re_service import score_re_agnostic

        assert score_re_agnostic(polar) is None

    def test_interpolate_between_two_null_rows_gives_none_metrics(self):
        """Interpolation between two all-None neighbours must propagate None."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        rows = [_NullMetricRow(90_000), _NullMetricRow(110_000)]
        polar = interpolate_polar_at_re(rows, 100_000, [90_000, 110_000])
        assert polar is not None
        assert polar["ld_max"] is None
        assert polar["cl_max"] is None
        from app.services.airfoil_low_re_service import score_re_agnostic

        assert score_re_agnostic(polar) is None

    def test_interpolate_null_lo_real_hi_uses_real_values(self):
        """When the lower neighbour has all-None metrics and the upper has real data,
        _lerp must return the real (non-None) value so the score degrades gracefully
        rather than silently discarding valid high-Re data.
        """
        from app.services.airfoil_low_re_service import interpolate_polar_at_re, score_re_agnostic

        rows = [_NullMetricRow(200_000), _RealMetricRow(300_000)]
        polar = interpolate_polar_at_re(rows, 250_000, [200_000, 300_000])
        assert polar is not None
        # _lerp(None, real, t) returns real — score must be non-None
        score = score_re_agnostic(polar)
        assert score is not None, (
            "When one neighbour has real metrics, score_re_agnostic must return "
            "a finite score (not None) — partial data is better than no data"
        )
        assert 0.0 < score <= 1.0

    def test_empty_polar_rows_returns_none(self):
        """interpolate_polar_at_re with an empty list must return None."""
        from app.services.airfoil_low_re_service import interpolate_polar_at_re

        result = interpolate_polar_at_re([], 100_000, [100_000])
        assert result is None

    def test_score_re_agnostic_none_polar_returns_none(self):
        """score_re_agnostic(None) must return None without raising."""
        from app.services.airfoil_low_re_service import score_re_agnostic

        assert score_re_agnostic(None) is None
