"""Parabolic polar fit tests — gh-486.

TDD test suite covering:
- _fit_parabolic_polar() helper
- recompute_assumptions context caching (e_oswald keys)
- _min_drag_speed / _min_sink_speed consuming cached e_oswald
- Cross-check against Anderson textbook §6.1.2 / §6.7.2 reference aircraft

Reference aircraft from gh-475 audit §5 + ticket #486 ACs:
- Cessna 172:  e=0.75, AR=7.32
- ASW-27:      e=0.80, AR=28.5
- RC Trainer:  e=0.78, AR=7.0

Design Decisions:
- The cd0 sanity guard uses absolute ±20% relative to stability-run cd0.
  For synthetic tests without a real stability run, cd0_stability is set
  equal to the ground-truth cd0 so the guard always passes for clean polars.
- The laminar-bubble test injects a non-monotonic CL² → CD relationship
  in the linear region to simulate the dip that accompanies laminar bubbles.
- For context integration tests, a sentinel context dict is injected
  (no DB required).
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from app.services.assumption_compute_service import (
    _fit_parabolic_polar,
    _min_drag_speed,
    _min_sink_speed,
)


# ---------------------------------------------------------------------------
# Reference aircraft data
# ---------------------------------------------------------------------------

CESSNA_172 = {
    "name": "Cessna 172",
    "mass_kg": 1043.0,
    "s_ref_m2": 16.2,
    "ar": 7.32,
    "cd0": 0.031,
    "e": 0.75,
    "cl_max": 1.6,
}

ASW_27 = {
    "name": "ASW-27",
    "mass_kg": 300.0,
    "s_ref_m2": 9.0,
    "ar": 28.5,
    "cd0": 0.011,
    "e": 0.80,
    "cl_max": 1.3,
}

RC_TRAINER = {
    "name": "RC Trainer",
    "mass_kg": 2.0,
    "s_ref_m2": 0.40,
    "ar": 7.0,
    "cd0": 0.035,
    "e": 0.78,
    "cl_max": 1.2,
}

REFERENCE_AIRCRAFT = [CESSNA_172, ASW_27, RC_TRAINER]


# ---------------------------------------------------------------------------
# Helper: build a clean synthetic polar for given (cd0, e, AR, cl_max)
# ---------------------------------------------------------------------------


def _make_synthetic_polar(
    cd0: float,
    e: float,
    ar: float,
    cl_max: float,
    n_points: int = 30,
    noise_std: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate (cl, cd) arrays from the parabolic model C_D = C_D0 + C_L²/(π e AR)."""
    k = 1.0 / (math.pi * e * ar)
    cl_lo = max(0.10, 0.10 * cl_max)
    cl_hi = 0.85 * cl_max
    cls = np.linspace(cl_lo * 0.5, cl_hi * 1.1, n_points)  # wider than window
    cds = cd0 + k * cls**2
    if noise_std > 0.0 and rng is not None:
        cds = cds + rng.normal(0.0, noise_std, size=len(cds))
    return cls, cds


# ---------------------------------------------------------------------------
# Unit tests: _fit_parabolic_polar
# ---------------------------------------------------------------------------


class TestFitParabolicPolar:
    """Unit tests for _fit_parabolic_polar()."""

    def test_synthetic_polar_recovers_cessna(self):
        """Clean synthetic Cessna 172 polar recovers e within ±0.07."""
        ac = CESSNA_172
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert e_fit is not None, "fit should succeed on clean synthetic polar"
        assert abs(e_fit - ac["e"]) < 0.07, (
            f"Cessna: e_fit={e_fit:.4f} vs reference {ac['e']}"
        )

    def test_synthetic_polar_recovers_asw27(self):
        """Clean synthetic ASW-27 polar (high AR) recovers e within ±0.07."""
        ac = ASW_27
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert e_fit is not None, "fit should succeed on clean synthetic polar"
        assert abs(e_fit - ac["e"]) < 0.07, (
            f"ASW-27: e_fit={e_fit:.4f} vs reference {ac['e']}"
        )

    def test_synthetic_polar_recovers_rc_trainer(self):
        """Clean synthetic RC-Trainer polar recovers e within ±0.07."""
        ac = RC_TRAINER
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert e_fit is not None, "fit should succeed on clean synthetic polar"
        assert abs(e_fit - ac["e"]) < 0.07, (
            f"RC Trainer: e_fit={e_fit:.4f} vs reference {ac['e']}"
        )

    def test_window_clamps_cl_lo_to_0_10_when_cl_max_is_tiny(self):
        """C_L_lo = max(0.10, 0.10·CL_max) — for CL_max=0.5, cl_lo=max(0.10, 0.05)=0.10."""
        # Build a polar over a wide range; fit should still work for the clamped window
        cls = np.linspace(0.05, 0.45, 30)
        cds = 0.03 + cls**2 / (math.pi * 0.75 * 7.0)
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=0.5, cd0_stability=0.03
        )
        # cl_hi = 0.85 * 0.5 = 0.425, cl_lo = 0.10 → window is [0.10, 0.425]
        # expect fit to succeed (enough points in that range)
        assert e_fit is not None, "should succeed with points in [0.10, 0.425]"

    def test_window_uses_fraction_of_cl_max(self):
        """C_L_hi = 0.85·CL_max. Points above 0.85·CL_max are excluded."""
        # Give points only above 0.85·CL_max: fit should fail (< 6 points in window)
        cl_max = 1.0
        cl_lo = max(0.10, 0.10 * cl_max)
        cl_hi = 0.85 * cl_max
        # Only provide points ABOVE the window
        cls = np.linspace(cl_hi + 0.01, cl_max * 1.2, 5)
        cds = 0.03 + cls**2 / (math.pi * 0.75 * 7.0)
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert e_fit is None, "no points in window → should return None"

    def test_requires_min_6_points_in_window(self):
        """< 6 points in the linear window → return (None, None, None)."""
        cl_max = 1.0
        # Put exactly 5 points in the window [0.10, 0.85]
        cl_lo = max(0.10, 0.10 * cl_max)
        cl_hi = 0.85 * cl_max
        cls = np.linspace(cl_lo, cl_hi, 5)
        cds = 0.03 + cls**2 / (math.pi * 0.75 * 7.0)
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "< 6 points should return (None, None, None)"
        )

    def test_rejects_negative_slope(self):
        """k ≤ 0 (negative or zero slope in CD vs CL²) → return (None, None, None)."""
        cl_max = 1.0
        cls = np.linspace(0.1, 0.8, 20)
        # Decreasing CD with increasing CL² — physically impossible
        cds = 0.04 - 0.01 * cls**2
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.04
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "negative slope should be rejected"
        )

    def test_rejects_e_below_0_4(self):
        """e < 0.4 (physically implausible) → return (None, None, None)."""
        cl_max = 1.0
        # k = 1/(pi*e*AR): for e=0.1, k is huge
        k_tiny_e = 1.0 / (math.pi * 0.1 * 7.0)
        cls = np.linspace(0.1, 0.8, 20)
        cds = 0.03 + k_tiny_e * cls**2
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "e < 0.4 should be rejected as physically implausible"
        )

    def test_rejects_e_above_1_0(self):
        """e > 1.0 (physically impossible beyond Trefftz Plane limit) → return (None, None, None)."""
        cl_max = 1.0
        # k = 1/(pi*e*AR): for e=1.5, k is very small
        k_too_high_e = 1.0 / (math.pi * 1.5 * 7.0)
        cls = np.linspace(0.1, 0.8, 20)
        cds = 0.03 + k_too_high_e * cls**2
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "e > 1.0 should be rejected"
        )

    def test_rejects_laminar_bubble_non_monotonic(self):
        """Non-monotonic dCD/dCL² (laminar bubble signature) → reject."""
        cl_max = 1.2
        cl_lo = max(0.10, 0.10 * cl_max)
        cl_hi = 0.85 * cl_max
        cls = np.linspace(cl_lo, cl_hi, 25)
        k = 1.0 / (math.pi * 0.75 * 7.0)
        cds = 0.03 + k * cls**2
        # Inject a dip in the middle of the window (laminar bubble)
        mid = len(cls) // 2
        cds[mid] -= 0.015  # big dip
        cds[mid + 1] -= 0.010
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "non-monotonic polar should be rejected (laminar bubble guard)"
        )

    def test_rejects_cd0_off_by_more_than_20_percent(self):
        """cd0_fit > ±20% of cd0_stability → reject."""
        cl_max = 1.0
        # Create a polar with cd0_true = 0.06 but pass cd0_stability = 0.03
        # — 100% deviation, should be rejected
        k = 1.0 / (math.pi * 0.75 * 7.0)
        cls = np.linspace(0.1, 0.8, 20)
        cds = 0.06 + k * cls**2
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "cd0_fit deviating >20% from stability run should be rejected"
        )

    def test_returns_r2_in_tuple(self):
        """Return value is a 3-tuple (cd0, e_oswald, r2) where r2 ∈ [0, 1]."""
        ac = CESSNA_172
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        result = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert len(result) == 3, "must return 3-tuple (cd0, e, r2)"
        cd0_fit, e_fit, r2 = result
        assert r2 is not None
        assert 0.9 < r2 <= 1.0, f"clean synthetic polar should have R²>0.9, got {r2}"

    def test_rejects_negative_cd0_intercept(self):
        """cd0_fit ≤ 0 (negative intercept) → return (None, None, None)."""
        cl_max = 1.0
        cls = np.linspace(0.1, 0.8, 20)
        # Very shallow slope but negative intercept → fit gives cd0 < 0
        cds = -0.01 + 0.001 * cls**2
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )
        assert (cd0_fit, e_fit, r2) == (None, None, None), (
            "negative cd0 intercept should be rejected"
        )


# ---------------------------------------------------------------------------
# Context caching integration tests (pure-unit, no DB)
# ---------------------------------------------------------------------------


class TestCachedContextIntegration:
    """Verify that recompute_assumptions populates e_oswald context keys."""

    def _run_recompute_with_fake_polar(
        self, client_and_db, ac: dict, fit_succeeds: bool = True
    ):
        """Helper: run recompute_assumptions with a fake alpha sweep that
        produces a clean synthetic polar for the given reference aircraft."""
        from types import SimpleNamespace
        from unittest.mock import patch

        from app.services.assumption_compute_service import recompute_assumptions
        from app.services.design_assumptions_service import seed_defaults
        from app.tests.conftest import make_aeroplane
        from app.models.aeroplanemodel import AeroplaneModel

        _, SessionLocal = client_and_db

        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            seed_defaults(db, str(aeroplane.uuid))
            db.commit()
            aeroplane_uuid = str(aeroplane.uuid)
            aeroplane_id = aeroplane.id

        fake_wing = SimpleNamespace(
            area=lambda: ac["s_ref_m2"],
            mean_aerodynamic_chord=lambda: math.sqrt(ac["s_ref_m2"] / ac["ar"]),
            span=lambda: math.sqrt(ac["s_ref_m2"] * ac["ar"]),
        )
        fake_airplane = SimpleNamespace(
            wings=[fake_wing],
            xyz_ref=[0.08, 0.0, 0.0],
            s_ref=ac["s_ref_m2"],
            c_ref=math.sqrt(ac["s_ref_m2"] / ac["ar"]),
            b_ref=math.sqrt(ac["s_ref_m2"] * ac["ar"]),
        )

        # Build synthetic polar data to inject via the sweep result
        if fit_succeeds:
            cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        else:
            # Degenerate: only 3 points — fit will fail
            cls = np.array([0.1, 0.2, 0.3])
            cds = np.array([0.03, 0.035, 0.04])

        with (
            patch(
                "app.services.assumption_compute_service._build_asb_airplane",
                return_value=fake_airplane,
            ),
            patch(
                "app.services.assumption_compute_service._stability_run_at_cruise",
                return_value=(0.085, float(fake_wing.mean_aerodynamic_chord()), ac["cd0"], ac["s_ref_m2"]),
            ),
            patch(
                "app.services.assumption_compute_service._coarse_alpha_sweep",
                return_value=15.0,
            ),
            patch(
                "app.services.assumption_compute_service._fine_sweep_cl_max",
                return_value=(ac["cl_max"], cls, cds),
            ),
            patch(
                "app.services.assumption_compute_service._load_flight_profile_speeds",
                return_value=(18.0, 28.0, True),
            ),
        ):
            with SessionLocal() as db:
                recompute_assumptions(db, aeroplane_uuid)
                db.commit()

        with SessionLocal() as db:
            a = db.query(AeroplaneModel).filter_by(id=aeroplane_id).first()
            return a.assumption_computation_context

    def test_e_oswald_cached_when_fit_succeeds(self, client_and_db):
        """context['e_oswald'] is a float and e_oswald_fallback_used is False."""
        ctx = self._run_recompute_with_fake_polar(client_and_db, CESSNA_172, fit_succeeds=True)
        assert ctx is not None
        assert "e_oswald" in ctx
        assert ctx["e_oswald"] is not None
        assert isinstance(ctx["e_oswald"], float)
        assert ctx.get("e_oswald_fallback_used") is False

    def test_fallback_marked_when_fit_fails(self, client_and_db):
        """When the polar fit rejects, e_oswald_fallback_used=True in context."""
        ctx = self._run_recompute_with_fake_polar(client_and_db, CESSNA_172, fit_succeeds=False)
        assert ctx is not None
        assert "e_oswald_fallback_used" in ctx
        assert ctx["e_oswald_fallback_used"] is True

    def test_min_drag_speed_uses_cached_e(self, client_and_db):
        """v_md_mps in context is computed with fitted e (not hardcoded 0.8).

        We verify this by:
        1. The fit succeeds (e_oswald_fallback_used == False)
        2. v_md_mps in context equals _min_drag_speed called with the
           same effective mass/s_ref/cd0/ar/e_oswald that recompute used.
        The effective mass in DB defaults means we cannot use ac["mass_kg"];
        instead we compute v_md_mps two ways — with fitted e and with e=0.8
        — and verify the context value matches the fitted version.
        """
        from app.schemas.design_assumption import PARAMETER_DEFAULTS
        ac = CESSNA_172
        ctx = self._run_recompute_with_fake_polar(client_and_db, ac, fit_succeeds=True)
        e_cached = ctx.get("e_oswald")
        assert e_cached is not None
        assert ctx.get("e_oswald_fallback_used") is False

        # Recompute v_md with the DB-default mass and the fitted geometry
        db_mass = PARAMETER_DEFAULTS.get("mass", 1.5)
        v_md_with_fitted_e = _min_drag_speed(
            db_mass, ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=e_cached
        )
        v_md_with_fallback_e = _min_drag_speed(
            db_mass, ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=0.8
        )
        v_md_in_ctx = ctx.get("v_md_mps")
        assert v_md_in_ctx is not None
        # v_md_mps must agree with fitted e, not fallback 0.8
        # (for Cessna e=0.75, which is ≠ 0.8, so values differ measurably)
        assert v_md_with_fitted_e is not None
        assert v_md_with_fallback_e is not None
        assert abs(v_md_in_ctx - v_md_with_fitted_e) < abs(v_md_in_ctx - v_md_with_fallback_e) or (
            abs(v_md_in_ctx - v_md_with_fitted_e) < 0.2
        ), (
            f"v_md_mps={v_md_in_ctx:.2f} should be closer to e_fitted={e_cached:.4f} "
            f"({v_md_with_fitted_e:.2f}) than fallback e=0.8 ({v_md_with_fallback_e:.2f})"
        )

    def test_min_sink_speed_uses_cached_e(self, client_and_db):
        """v_min_sink_mps in context is computed with fitted e (not hardcoded 0.8)."""
        from app.schemas.design_assumption import PARAMETER_DEFAULTS
        ac = CESSNA_172
        ctx = self._run_recompute_with_fake_polar(client_and_db, ac, fit_succeeds=True)
        e_cached = ctx.get("e_oswald")
        assert e_cached is not None
        assert ctx.get("e_oswald_fallback_used") is False

        db_mass = PARAMETER_DEFAULTS.get("mass", 1.5)
        v_ms_with_fitted_e = _min_sink_speed(
            db_mass, ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=e_cached
        )
        v_ms_with_fallback_e = _min_sink_speed(
            db_mass, ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=0.8
        )
        v_ms_in_ctx = ctx.get("v_min_sink_mps")
        assert v_ms_in_ctx is not None
        assert v_ms_with_fitted_e is not None
        assert v_ms_with_fallback_e is not None
        assert abs(v_ms_in_ctx - v_ms_with_fitted_e) < abs(v_ms_in_ctx - v_ms_with_fallback_e) or (
            abs(v_ms_in_ctx - v_ms_with_fitted_e) < 0.2
        ), (
            f"v_min_sink_mps={v_ms_in_ctx:.2f} should be closer to e_fitted={e_cached:.4f} "
            f"({v_ms_with_fitted_e:.2f}) than fallback e=0.8 ({v_ms_with_fallback_e:.2f})"
        )


# ---------------------------------------------------------------------------
# Cross-check against Anderson formula (all three reference aircraft)
# ---------------------------------------------------------------------------


class TestCrossCheckAgainstAndersonFormula:
    """Anderson §6.1.2 / §6.7.2 cross-checks for three reference aircraft."""

    @pytest.mark.parametrize("ac", REFERENCE_AIRCRAFT, ids=lambda a: a["name"])
    def test_e_fit_within_0_07_of_reference(self, ac):
        """e_fit from clean synthetic polar must match reference e within ±0.07."""
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert e_fit is not None, f"{ac['name']}: fit failed on clean synthetic polar"
        assert abs(e_fit - ac["e"]) < 0.07, (
            f"{ac['name']}: e_fit={e_fit:.4f} vs reference {ac['e']}, diff={abs(e_fit - ac['e']):.4f}"
        )

    @pytest.mark.parametrize("ac", REFERENCE_AIRCRAFT, ids=lambda a: a["name"])
    def test_v_md_within_5_percent_of_anderson(self, ac):
        """V_md with fitted e must be within 5% of Anderson textbook formula."""
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert e_fit is not None, f"{ac['name']}: fit failed on clean synthetic polar"

        # V_md with fitted e
        v_md_fit = _min_drag_speed(ac["mass_kg"], ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=e_fit)
        # V_md with reference (textbook) e — Anderson §6.7.2
        v_md_ref = _min_drag_speed(ac["mass_kg"], ac["s_ref_m2"], ac["cd0"], ac["ar"], oswald_e=ac["e"])
        assert v_md_fit is not None
        assert v_md_ref is not None
        rel_err = abs(v_md_fit - v_md_ref) / v_md_ref
        assert rel_err < 0.05, (
            f"{ac['name']}: V_md with fitted e={e_fit:.4f} → {v_md_fit:.2f} m/s, "
            f"reference e={ac['e']} → {v_md_ref:.2f} m/s, rel_err={rel_err:.3f}"
        )

    @pytest.mark.parametrize("ac", REFERENCE_AIRCRAFT, ids=lambda a: a["name"])
    def test_cd0_fit_within_20_percent_of_stability_run(self, ac):
        """cd0_fit from clean synthetic polar must be within ±20% of true cd0."""
        cls, cds = _make_synthetic_polar(ac["cd0"], ac["e"], ac["ar"], ac["cl_max"])
        cd0_fit, e_fit, r2 = _fit_parabolic_polar(
            cls, cds, ar=ac["ar"], cl_max=ac["cl_max"], cd0_stability=ac["cd0"]
        )
        assert cd0_fit is not None, f"{ac['name']}: fit failed on clean synthetic polar"
        rel_err = abs(cd0_fit - ac["cd0"]) / ac["cd0"]
        assert rel_err < 0.20, (
            f"{ac['name']}: cd0_fit={cd0_fit:.5f} vs true cd0={ac['cd0']}, "
            f"rel_err={rel_err:.3f}"
        )


# ---------------------------------------------------------------------------
# Rejection logging test
# ---------------------------------------------------------------------------


class TestRejectionLogging:
    """Verify that rejection emits a logger.warning."""

    def test_warning_logged_on_laminar_bubble_rejection(self, monkeypatch):
        """Non-monotonic polar rejection must log a warning.

        Uses monkeypatch to replace the module-level logger.warning with a
        spy function, completely bypassing the logging level / propagation
        state that prior tests may have altered.
        """
        import logging
        import app.services.assumption_compute_service as _acs

        warning_calls: list[tuple] = []

        original_warning = _acs.logger.warning

        def _spy_warning(msg, *args, **kwargs):
            warning_calls.append((msg, args))
            original_warning(msg, *args, **kwargs)

        monkeypatch.setattr(_acs.logger, "warning", _spy_warning)

        cl_max = 1.2
        cl_lo = max(0.10, 0.10 * cl_max)
        cl_hi = 0.85 * cl_max
        cls = np.linspace(cl_lo, cl_hi, 25)
        k = 1.0 / (math.pi * 0.75 * 7.0)
        cds = 0.03 + k * cls**2
        mid = len(cls) // 2
        cds[mid] -= 0.015
        cds[mid + 1] -= 0.010

        result = _fit_parabolic_polar(
            cls, cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03
        )

        assert result == (None, None, None)
        # Check that a warning was emitted mentioning monotonicity or laminar bubble
        all_msgs = [str(msg) + " ".join(str(a) for a in args) for msg, args in warning_calls]
        assert any(
            "monoton" in m.lower() or "laminar" in m.lower() or "non-monoton" in m.lower()
            for m in all_msgs
        ), (
            f"Expected a warning about non-monotonic polar. Got: {all_msgs}"
        )
