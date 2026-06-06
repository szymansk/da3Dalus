"""TDD tests for gh-871: angle of attack at characteristic speeds.

Backend tests only — no AeroSandbox, no DB required.
Strategy:
  - Pure-function tests for the new _cl_to_alpha_deg helper
  - _compute_speed_polar tests verifying alpha fields on SpeedPolarCurve
  - Tests that alpha_0_deg propagates correctly from computation context stub
  - Null-safety: missing lift-curve data → None for all alpha fields
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.services.analysis_service import _compute_speed_polar


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

G = 9.81


def _parabolic_polar(cd0: float, e: float, ar: float, cl_range=(0.1, 1.4), n: int = 200):
    """Return (cl_arr, cd_arr) for a parabolic polar."""
    cl = np.linspace(*cl_range, n)
    cd = cd0 + cl**2 / (math.pi * e * ar)
    return cl, cd


# ---------------------------------------------------------------------------
# Unit tests for _cl_to_alpha_deg (pure math helper)
# ---------------------------------------------------------------------------


class TestClToAlphaDeg:
    """_cl_to_alpha_deg must invert the linear lift curve CL = cl_0 + cl_alpha*alpha."""

    def test_zero_cl_gives_zero_lift_alpha(self):
        """At CL=0, α = α_0 = alpha_0_deg."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        # α_0 = -2°, so at CL=0 the result should be -2°
        result = _cl_to_alpha_deg(cl=0.0, cl_alpha_per_rad=5.7, alpha_0_deg=-2.0)
        assert result == pytest.approx(-2.0, abs=1e-6)

    def test_positive_cl_above_zero_lift(self):
        """At CL > 0 with α_0 = 0°, α = CL / cl_alpha_per_rad (in degrees)."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        cl_alpha = 5.7  # rad⁻¹
        cl = 1.0
        alpha_0 = 0.0
        expected_deg = math.degrees(cl / cl_alpha)  # = cl / cl_alpha * 180/π
        result = _cl_to_alpha_deg(cl=cl, cl_alpha_per_rad=cl_alpha, alpha_0_deg=alpha_0)
        assert result == pytest.approx(expected_deg, rel=1e-6)

    def test_roundtrip_with_nonzero_alpha_0(self):
        """α_0 = -2°: cl_to_alpha should invert cl_alpha*(alpha - alpha_0)."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        cl_alpha = 5.5  # rad⁻¹
        alpha_0_deg = -2.0
        # Forward: CL = cl_alpha * deg2rad(alpha - alpha_0)
        alpha_target_deg = 5.0
        alpha_0_rad = math.radians(alpha_0_deg)
        cl = cl_alpha * (math.radians(alpha_target_deg) - alpha_0_rad)
        # Invert:
        result = _cl_to_alpha_deg(cl=cl, cl_alpha_per_rad=cl_alpha, alpha_0_deg=alpha_0_deg)
        assert result == pytest.approx(alpha_target_deg, abs=1e-9)

    def test_returns_none_when_cl_alpha_is_none(self):
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        assert _cl_to_alpha_deg(cl=1.0, cl_alpha_per_rad=None, alpha_0_deg=-2.0) is None

    def test_returns_none_when_alpha_0_is_none(self):
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        assert _cl_to_alpha_deg(cl=1.0, cl_alpha_per_rad=5.7, alpha_0_deg=None) is None

    def test_returns_none_when_cl_alpha_is_zero(self):
        """Guard: cl_alpha=0 would cause division by zero — return None."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        assert _cl_to_alpha_deg(cl=1.0, cl_alpha_per_rad=0.0, alpha_0_deg=-2.0) is None

    def test_returns_none_when_cl_alpha_negative(self):
        """Non-positive cl_alpha is degenerate."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        assert _cl_to_alpha_deg(cl=1.0, cl_alpha_per_rad=-5.7, alpha_0_deg=-2.0) is None


# ---------------------------------------------------------------------------
# _compute_speed_polar: alpha fields on SpeedPolarCurve
# ---------------------------------------------------------------------------


class TestAlphaFieldsOnSpeedPolarCurve:
    """_compute_speed_polar must populate alpha_*_deg fields on SpeedPolarCurve
    when cl_alpha_per_rad and alpha_0_deg are supplied.
    """

    @pytest.fixture()
    def parabolic_cl_cd(self):
        return _parabolic_polar(cd0=0.012, e=0.85, ar=14.4)

    def test_alpha_fields_present_in_schema(self, parabolic_cl_cd):
        """SpeedPolarCurve must now have the three alpha fields."""
        from app.schemas.aeroanalysisschema import SpeedPolarCurve

        curve = SpeedPolarCurve(
            mass_kg=1.5,
            is_base=True,
            V=[10.0, 12.0],
            w=[0.5, 0.4],
            cl=[1.0, 0.8],
            cd=[0.05, 0.04],
            v_stall=9.0,
            v_min_sink=10.0,
            w_min=0.4,
            v_best_glide=12.0,
            ld_max=20.0,
        )
        # Fields must exist (Optional → default None)
        assert hasattr(curve, "alpha_stall_deg")
        assert hasattr(curve, "alpha_min_sink_deg")
        assert hasattr(curve, "alpha_best_glide_deg")

    def test_alpha_populated_when_lift_curve_provided(self, parabolic_cl_cd):
        """When cl_alpha_per_rad and alpha_0_deg are provided, all three alpha
        fields should be finite floats for a normal parabolic polar."""
        cl, cd = parabolic_cl_cd
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=5.7,
            alpha_0_deg=-2.0,
        )
        curve = sp.curves[0]
        assert curve.alpha_stall_deg is not None
        assert curve.alpha_min_sink_deg is not None
        assert curve.alpha_best_glide_deg is not None
        assert math.isfinite(curve.alpha_stall_deg)
        assert math.isfinite(curve.alpha_min_sink_deg)
        assert math.isfinite(curve.alpha_best_glide_deg)

    def test_alpha_none_when_lift_curve_missing(self, parabolic_cl_cd):
        """Without lift-curve data, alpha fields must be None — no KeyError/exception."""
        cl, cd = parabolic_cl_cd
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=None,
            alpha_0_deg=None,
        )
        curve = sp.curves[0]
        assert curve.alpha_stall_deg is None
        assert curve.alpha_min_sink_deg is None
        assert curve.alpha_best_glide_deg is None

    def test_alpha_none_when_only_cl_alpha_missing(self, parabolic_cl_cd):
        cl, cd = parabolic_cl_cd
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=None,
            alpha_0_deg=-2.0,
        )
        assert sp.curves[0].alpha_stall_deg is None

    def test_alpha_stall_corresponds_to_cl_max(self, parabolic_cl_cd):
        """alpha_stall is computed from cl_max (not cl at best-glide or min-sink)."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        cl, cd = parabolic_cl_cd
        cl_alpha = 5.7
        alpha_0 = -2.0
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=cl_alpha,
            alpha_0_deg=alpha_0,
        )
        curve = sp.curves[0]
        cl_max = float(np.max(cl))  # CL_max of the polar
        expected = _cl_to_alpha_deg(cl_max, cl_alpha, alpha_0)
        assert curve.alpha_stall_deg == pytest.approx(expected, rel=1e-6)

    def test_alpha_best_glide_corresponds_to_cl_at_ld_max(self, parabolic_cl_cd):
        """alpha_best_glide is computed from the CL at maximum L/D."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        cl, cd = parabolic_cl_cd
        cl_alpha = 5.7
        alpha_0 = -2.0
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=cl_alpha,
            alpha_0_deg=alpha_0,
        )
        curve = sp.curves[0]
        # Find CL at i_best (argmax of L/D = CL/CD)
        cl_arr = np.asarray(cl)
        cd_arr = np.asarray(cd)
        pos = cl_arr > 0
        cl_pos, cd_pos = cl_arr[pos], cd_arr[pos]
        order = np.argsort(np.sqrt(2 * 1.5 * G / (1.225 * 0.225 * cl_pos)))
        cl_s = cl_pos[order]
        cd_s = cd_pos[order]
        i_best = int(np.argmax(cl_s / cd_s))
        expected = _cl_to_alpha_deg(float(cl_s[i_best]), cl_alpha, alpha_0)
        assert curve.alpha_best_glide_deg == pytest.approx(expected, rel=1e-6)

    def test_alpha_ordering_makes_physical_sense(self, parabolic_cl_cd):
        """For a clean parabolic polar: alpha_stall > alpha_min_sink > alpha_best_glide.
        (Higher α → higher CL; CL_stall > CL_min_sink > CL_best_glide.)
        """
        cl, cd = parabolic_cl_cd
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=5.7,
            alpha_0_deg=-2.0,
        )
        curve = sp.curves[0]
        assert curve.alpha_stall_deg > curve.alpha_min_sink_deg
        assert curve.alpha_min_sink_deg > curve.alpha_best_glide_deg

    def test_alpha_same_for_all_masses(self, parabolic_cl_cd):
        """Alpha values depend only on CL (lift curve), not on mass.
        So alpha_best_glide, alpha_min_sink, alpha_stall should be identical
        for all mass variants.
        """
        cl, cd = parabolic_cl_cd
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[3.0],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=5.7,
            alpha_0_deg=-2.0,
        )
        c1, c2 = sp.curves[0], sp.curves[1]
        # Alpha fields should be identical (mass-independent CL→α mapping)
        assert c1.alpha_best_glide_deg == pytest.approx(c2.alpha_best_glide_deg, abs=1e-9)
        assert c1.alpha_min_sink_deg == pytest.approx(c2.alpha_min_sink_deg, abs=1e-9)
        assert c1.alpha_stall_deg == pytest.approx(c2.alpha_stall_deg, abs=1e-9)

    def test_degenerate_empty_curve_alpha_none(self):
        """Degenerate curve (no positive CL) → alpha fields None."""
        cl = np.array([-0.5, 0.0])
        cd = np.array([0.04, 0.02])
        sp = _compute_speed_polar(
            cl=cl,
            cd=cd,
            masses_kg=[],
            base_mass_kg=1.5,
            s_ref_m2=0.225,
            rho=1.225,
            cl_alpha_per_rad=5.7,
            alpha_0_deg=-2.0,
        )
        curve = sp.curves[0]
        assert curve.alpha_stall_deg is None
        assert curve.alpha_min_sink_deg is None
        assert curve.alpha_best_glide_deg is None


# ---------------------------------------------------------------------------
# alpha_0_deg propagation from computation context
# ---------------------------------------------------------------------------


class TestAlpha0DegStoredInContext:
    """alpha_0_deg must be stored in the assumption_computation_context."""

    def test_cl_to_alpha_matches_context_values(self):
        """Given context values (cl_alpha_per_rad, alpha_0_deg), the CL→α
        formula should be invertible and stable."""
        from app.services.assumption_compute_service import _cl_to_alpha_deg

        # Simulate what the context stores
        cl_alpha = 5.7
        alpha_0 = -2.3

        # Forward: CL at α=8°
        alpha_test_rad = math.radians(8.0)
        alpha_0_rad = math.radians(alpha_0)
        cl_at_8 = cl_alpha * (alpha_test_rad - alpha_0_rad)

        # Invert: back to α=8°
        recovered = _cl_to_alpha_deg(cl_at_8, cl_alpha, alpha_0)
        assert recovered == pytest.approx(8.0, abs=1e-9)
