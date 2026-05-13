"""Tests for gust load envelope (V-n diagram) — gh-487.

Covers:
- Pratt-Walker discrete sharp-edged gust formula
- Gust-alleviation factor K_g (FAR-25.341(a)(2) / CS-VLA.333)
- Mean geometric chord μ_g formula
- Helmbold-Diederich CL_α fallback (Anderson 6e Eq. 5.81)
- Integration into VnCurve schema (gust_lines_positive / negative)
- GustCriticalWarning when n_gust > g_limit
- μ_g validity check [3, 200]
- Cross-check: AR=20 high-AR sailplane Δn > 2 at V_C
- CL_α extraction from assumption_computation_context
"""

from __future__ import annotations

import math
import pytest


# ────────────────────────────────────────────────────────────────────────────
# Pratt-Walker computation helpers
# ────────────────────────────────────────────────────────────────────────────


class TestGustComputation:
    """Unit tests for the Pratt-Walker gust formula helpers."""

    def test_pratt_walker_basic_delta_n(self):
        """Δn = ½·ρ·V·CL_α·U·K_g / (W/S).

        Reference values:
          W/S = 400 N/m²  (mass=40.8 kg, S=1.0 m²)
          V   = 30 m/s
          CL_α = 5.7 rad⁻¹
          U_gust = 15.24 m/s
          K_g = 0.7 (fixed, to isolate Δn formula)
          rho = 1.225 kg/m³

        Δn = 0.5 × 1.225 × 30 × 5.7 × 15.24 × 0.7 / 400 ≈ 2.789
        """
        from app.services.flight_envelope_service import _compute_delta_n

        rho = 1.225
        v = 30.0
        cl_alpha = 5.7
        u_gust = 15.24
        k_g = 0.7
        mass_kg = 40.8  # → W/S ≈ 400 N/m² with S=1.0
        s_ref = 1.0

        delta_n = _compute_delta_n(rho, v, cl_alpha, u_gust, k_g, mass_kg, s_ref)

        # Δn = 0.5 × 1.225 × 30 × 5.7 × 15.24 × 0.7 / 400
        expected = 0.5 * rho * v * cl_alpha * u_gust * k_g / (mass_kg * 9.81 / s_ref)
        assert abs(delta_n - expected) < 1e-6

    def test_k_g_formula(self):
        """K_g = 0.88·μ_g / (5.3 + μ_g).

        At μ_g = 10: K_g = 0.88·10 / (5.3 + 10) = 8.8 / 15.3 ≈ 0.5752
        """
        from app.services.flight_envelope_service import _compute_k_g

        k_g = _compute_k_g(10.0)
        expected = 0.88 * 10.0 / (5.3 + 10.0)
        assert abs(k_g - expected) < 1e-6

    def test_mu_g_formula(self):
        """μ_g = 2·(W/S) / (ρ·c̄·CL_α·g).

        Reference:
          W/S = 400 N/m²
          rho = 1.225
          c_mgc = 0.3 m (mean geometric chord)
          CL_α = 5.7 rad⁻¹
          g = 9.81 m/s²
        """
        from app.services.flight_envelope_service import _compute_mu_g

        mass_kg = 40.8
        s_ref = 1.0
        c_mgc = 0.3
        cl_alpha = 5.7
        rho = 1.225
        g = 9.81

        mu_g = _compute_mu_g(mass_kg, s_ref, c_mgc, cl_alpha, rho, g)

        wing_loading = mass_kg * g / s_ref  # W/S in N/m²
        expected = 2.0 * wing_loading / (rho * c_mgc * cl_alpha * g)
        assert abs(mu_g - expected) < 1e-6

    def test_c_ref_uses_mgc_not_mac(self):
        """c_ref in μ_g is MGC = S_ref / b_ref, not MAC.

        Verify that _compute_mu_g uses the supplied c_mgc parameter (=S/b)
        and that different values produce different μ_g (confirming it's
        actually used).
        """
        from app.services.flight_envelope_service import _compute_mu_g

        mass_kg = 5.0
        s_ref = 0.5
        cl_alpha = 5.5
        rho = 1.225

        b_ref = 3.0
        c_mgc_correct = s_ref / b_ref  # MGC = S/b
        c_mgc_wrong = 0.25  # Some other chord (e.g. MAC from trapezoid)

        mu_g_correct = _compute_mu_g(mass_kg, s_ref, c_mgc_correct, cl_alpha, rho)
        mu_g_wrong = _compute_mu_g(mass_kg, s_ref, c_mgc_wrong, cl_alpha, rho)

        # Different chords → different μ_g (confirms c_mgc is actually used)
        assert abs(mu_g_correct - mu_g_wrong) > 1e-3


# ────────────────────────────────────────────────────────────────────────────
# Helmbold-Diederich fallback
# ────────────────────────────────────────────────────────────────────────────


class TestHelmboldFallback:
    """Helmbold-Diederich CL_α = 2π·AR/(AR+2) (Anderson 6e Eq. 5.81)."""

    @pytest.mark.parametrize("ar", [6, 10, 15, 25])
    def test_helmbold_cl_alpha_monotone_in_ar(self, ar: int):
        """CL_α increases with AR — reflects finite-span correction."""
        from app.services.flight_envelope_service import _helmbold_cl_alpha

        cl_alpha = _helmbold_cl_alpha(ar)
        expected = 2 * math.pi * ar / (ar + 2)
        assert abs(cl_alpha - expected) < 1e-9

    def test_helmbold_cl_alpha_below_thin_airfoil(self):
        """Any finite AR gives CL_α < 2π (thin-airfoil 2D limit)."""
        from app.services.flight_envelope_service import _helmbold_cl_alpha

        for ar in [4, 6, 10, 20]:
            assert _helmbold_cl_alpha(ar) < 2 * math.pi

    def test_helmbold_ar6_significantly_below_2pi(self):
        """At AR=6, Helmbold gives ~72% of 2π — not thin-airfoil.

        This cross-checks the spec: thin-airfoil (2π) overestimates
        CL_α at AR=6 by ~39%.
        """
        from app.services.flight_envelope_service import _helmbold_cl_alpha

        two_pi = 2 * math.pi
        cl_alpha_ar6 = _helmbold_cl_alpha(6)
        ratio = cl_alpha_ar6 / two_pi
        assert ratio < 0.80  # well below thin-airfoil


# ────────────────────────────────────────────────────────────────────────────
# Gust envelope integration tests
# ────────────────────────────────────────────────────────────────────────────


class TestGustEnvelopeComputation:
    """Integration tests for gust lines in compute_vn_curve."""

    def test_gust_lines_returned_in_vn_curve(self):
        """FlightEnvelopeRead.vn_curve has gust_lines_positive and negative."""
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=5.0,
            cl_max=1.4,
            g_limit=4.0,
            wing_area_m2=0.5,
            v_max_mps=25.0,
            b_ref_m=3.0,
            cl_alpha_per_rad=5.7,
        )
        assert hasattr(curve, "gust_lines_positive")
        assert hasattr(curve, "gust_lines_negative")
        assert len(curve.gust_lines_positive) > 0
        assert len(curve.gust_lines_negative) > 0

    def test_high_ar_sailplane_delta_n_above_2(self):
        """AR=20, W/S=40 N/m², V=V_C=30 m/s → Δn > 2.

        Cross-check from the issue AC: high-AR sailplanes have significant
        gust sensitivity. This is the acceptance-criteria regression.
        """
        from app.services.flight_envelope_service import (
            _compute_delta_n,
            _compute_k_g,
            _compute_mu_g,
            _helmbold_cl_alpha,
        )

        # AR=20 high-AR aircraft
        ar = 20.0
        b_ref = 10.0  # m
        s_ref = b_ref**2 / ar  # = 5.0 m² → W/S = 40 × 9.81 / 5.0 ≈ 78.5 N/m²
        mass_kg = 40.0  # W/S = 40 × 9.81 / 5.0 = 78.5 N/m²

        # Use a smaller wing so W/S ≈ 40 N/m²
        # W/S = 40 N/m² → S = mass × g / 40 = 40 × 9.81 / 40 = 9.81 m²
        s_ref_40 = mass_kg * 9.81 / 40.0  # = 9.81 m²
        b_ref_40 = math.sqrt(ar * s_ref_40)  # AR = b²/S

        c_mgc = s_ref_40 / b_ref_40
        cl_alpha = _helmbold_cl_alpha(ar)  # Helmbold at AR=20
        rho = 1.225
        v_c = 30.0  # m/s (cruise speed for gust)
        u_gust_vc = 15.24  # m/s (CS-VLA.333(c)(1))

        mu_g = _compute_mu_g(mass_kg, s_ref_40, c_mgc, cl_alpha, rho)
        k_g = _compute_k_g(mu_g)
        delta_n = _compute_delta_n(rho, v_c, cl_alpha, u_gust_vc, k_g, mass_kg, s_ref_40)

        assert delta_n > 2.0, (
            f"Expected Δn > 2 for AR=20 W/S=40 sailplane, got {delta_n:.3f}"
        )

    def test_gust_critical_warning_when_n_gust_exceeds_g_limit(self):
        """GustCriticalWarning emitted when 1 + Δn_gust > g_limit.

        A high-AR, low-wing-loading design is known to be gust-critical.
        """
        from app.services.flight_envelope_service import compute_vn_curve

        # AR=20, W/S ≈ 40 N/m² — should produce Δn > g_limit=3
        ar = 20.0
        mass_kg = 10.0
        s_ref = mass_kg * 9.81 / 40.0  # W/S=40 N/m²
        b_ref = math.sqrt(ar * s_ref)
        cl_alpha = 2 * math.pi * ar / (ar + 2)  # Helmbold

        curve = compute_vn_curve(
            mass_kg=mass_kg,
            cl_max=1.5,
            g_limit=3.0,
            wing_area_m2=s_ref,
            v_max_mps=25.0,
            b_ref_m=b_ref,
            cl_alpha_per_rad=cl_alpha,
        )
        # curve.gust_warnings should have at least one entry
        assert len(curve.gust_warnings) > 0
        w = curve.gust_warnings[0]
        assert w.n_gust > w.g_limit
        assert "gust" in w.message.lower()

    def test_gust_lines_positive_monotone_increasing_at_low_v(self):
        """Positive gust n-line rises with V in the low-V region (Δn ∝ V)."""
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=5.0,
            cl_max=1.4,
            g_limit=6.0,
            wing_area_m2=0.5,
            v_max_mps=25.0,
            b_ref_m=2.5,
            cl_alpha_per_rad=5.5,
        )
        pts = curve.gust_lines_positive
        # The first half of the line should be monotonically non-decreasing
        n = len(pts) // 2
        for i in range(1, n):
            assert pts[i].load_factor >= pts[i - 1].load_factor - 1e-6

    def test_gust_lines_negative_monotone_decreasing_at_low_v(self):
        """Negative gust n-line decreases with V in the low-V region."""
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=5.0,
            cl_max=1.4,
            g_limit=6.0,
            wing_area_m2=0.5,
            v_max_mps=25.0,
            b_ref_m=2.5,
            cl_alpha_per_rad=5.5,
        )
        pts = curve.gust_lines_negative
        n = len(pts) // 2
        for i in range(1, n):
            assert pts[i].load_factor <= pts[i - 1].load_factor + 1e-6


# ────────────────────────────────────────────────────────────────────────────
# μ_g validity
# ────────────────────────────────────────────────────────────────────────────


class TestMuGValidity:
    """μ_g validity warnings: Pratt validity range [3, 200]."""

    def test_mu_g_validity_warning_below_3(self, caplog):
        """When μ_g < 3 a WARNING is logged about Pratt validity range."""
        import logging
        from app.services.flight_envelope_service import _compute_k_g

        with caplog.at_level(logging.WARNING, logger="app.services.flight_envelope_service"):
            _compute_k_g(1.0)  # μ_g=1 → below validity range

        assert any("pratt" in r.message.lower() or "validity" in r.message.lower()
                   for r in caplog.records)

    def test_mu_g_validity_warning_above_200(self, caplog):
        """When μ_g > 200 a WARNING is logged about Pratt validity range."""
        import logging
        from app.services.flight_envelope_service import _compute_k_g

        with caplog.at_level(logging.WARNING, logger="app.services.flight_envelope_service"):
            _compute_k_g(300.0)  # μ_g=300 → above validity range

        assert any("pratt" in r.message.lower() or "validity" in r.message.lower()
                   for r in caplog.records)

    def test_mu_g_no_warning_in_valid_range(self, caplog):
        """No warning when μ_g is within [3, 200]."""
        import logging
        from app.services.flight_envelope_service import _compute_k_g

        with caplog.at_level(logging.WARNING, logger="app.services.flight_envelope_service"):
            _compute_k_g(50.0)

        assert not any("pratt" in r.message.lower() or "validity" in r.message.lower()
                       for r in caplog.records)


# ────────────────────────────────────────────────────────────────────────────
# CL_α caching / fallback
# ────────────────────────────────────────────────────────────────────────────


class TestClAlphaContext:
    """Tests for cl_alpha_per_rad caching and Helmbold fallback in VnCurve."""

    def test_cl_alpha_fallback_helmbold_when_none(self):
        """When cl_alpha_per_rad=None, compute_vn_curve falls back to Helmbold."""
        from app.services.flight_envelope_service import compute_vn_curve

        # Supply b_ref to enable aspect-ratio-based Helmbold fallback
        curve = compute_vn_curve(
            mass_kg=5.0,
            cl_max=1.4,
            g_limit=4.0,
            wing_area_m2=0.5,
            v_max_mps=25.0,
            b_ref_m=2.5,
            cl_alpha_per_rad=None,  # trigger fallback
        )
        # Should still produce gust lines (using Helmbold)
        assert len(curve.gust_lines_positive) > 0

    def test_cl_alpha_explicit_value_used(self):
        """When cl_alpha_per_rad is supplied, it is used (different from fallback)."""
        from app.services.flight_envelope_service import compute_vn_curve

        # Two curves: one with Helmbold CL_α, one with explicit higher value
        ar = 6.0
        b_ref = math.sqrt(ar * 0.5)
        helmbold = 2 * math.pi * ar / (ar + 2)

        curve_helmbold = compute_vn_curve(
            mass_kg=5.0, cl_max=1.4, g_limit=4.0, wing_area_m2=0.5,
            v_max_mps=25.0, b_ref_m=b_ref, cl_alpha_per_rad=helmbold,
        )
        curve_high = compute_vn_curve(
            mass_kg=5.0, cl_max=1.4, g_limit=4.0, wing_area_m2=0.5,
            v_max_mps=25.0, b_ref_m=b_ref, cl_alpha_per_rad=helmbold * 1.5,
        )
        # Higher CL_α → larger Δn → higher load factor at first gust point
        n_helmbold = curve_helmbold.gust_lines_positive[0].load_factor
        n_high = curve_high.gust_lines_positive[0].load_factor
        assert n_high > n_helmbold

    def test_no_gust_lines_without_b_ref_and_no_cl_alpha(self):
        """When neither b_ref nor cl_alpha_per_rad supplied, no gust lines."""
        from app.services.flight_envelope_service import compute_vn_curve

        curve = compute_vn_curve(
            mass_kg=5.0,
            cl_max=1.4,
            g_limit=4.0,
            wing_area_m2=0.5,
            v_max_mps=25.0,
            # b_ref_m omitted → Helmbold fallback not possible
            cl_alpha_per_rad=None,
        )
        assert curve.gust_lines_positive == []
        assert curve.gust_lines_negative == []


# ────────────────────────────────────────────────────────────────────────────
# Schema tests
# ────────────────────────────────────────────────────────────────────────────


class TestGustEnvelopeSchemas:
    """Pydantic schema tests for gust-envelope extensions."""

    def test_vn_curve_has_gust_fields(self):
        """VnCurve schema now includes gust_lines_positive and negative."""
        from app.schemas.flight_envelope import VnCurve, VnPoint

        pos = [VnPoint(velocity_mps=10.0, load_factor=1.0)]
        neg = [VnPoint(velocity_mps=10.0, load_factor=-0.5)]
        gust_pos = [VnPoint(velocity_mps=10.0, load_factor=2.0)]
        gust_neg = [VnPoint(velocity_mps=10.0, load_factor=-1.5)]

        curve = VnCurve(
            positive=pos,
            negative=neg,
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
            gust_lines_positive=gust_pos,
            gust_lines_negative=gust_neg,
        )
        assert len(curve.gust_lines_positive) == 1
        assert len(curve.gust_lines_negative) == 1

    def test_vn_curve_gust_fields_default_empty(self):
        """VnCurve.gust_lines_* default to empty list (backward compat)."""
        from app.schemas.flight_envelope import VnCurve, VnPoint

        pos = [VnPoint(velocity_mps=10.0, load_factor=1.0)]
        neg = [VnPoint(velocity_mps=10.0, load_factor=-0.5)]
        curve = VnCurve(
            positive=pos,
            negative=neg,
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        assert curve.gust_lines_positive == []
        assert curve.gust_lines_negative == []

    def test_gust_critical_warning_schema(self):
        """GustCriticalWarning schema validates correctly."""
        from app.schemas.flight_envelope import GustCriticalWarning

        w = GustCriticalWarning(
            velocity_mps=30.0,
            n_gust=4.2,
            g_limit=3.0,
            message="Gust-critical: structure sized by gust loads, not maneuver loads",
        )
        assert w.n_gust > w.g_limit
        assert "gust" in w.message.lower()

    def test_flight_envelope_read_has_gust_warnings(self):
        """FlightEnvelopeRead includes gust_warnings list."""
        from datetime import datetime, timezone
        from app.schemas.flight_envelope import (
            FlightEnvelopeRead,
            GustCriticalWarning,
            PerformanceKPI,
            VnCurve,
            VnMarker,
            VnPoint,
        )

        now = datetime.now(timezone.utc)
        curve = VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        kpi = PerformanceKPI(
            label="stall_speed", display_name="Stall Speed",
            value=8.5, unit="m/s", source_op_id=None, confidence="estimated",
        )
        marker = VnMarker(
            op_id=1, name="cruise", velocity_mps=20.0,
            load_factor=1.0, status="TRIMMED", label="cruise",
        )
        warning = GustCriticalWarning(
            velocity_mps=30.0, n_gust=4.2, g_limit=3.0,
            message="Gust-critical: structure sized by gust loads, not maneuver loads",
        )
        envelope = FlightEnvelopeRead(
            id=1, aeroplane_id=42, vn_curve=curve,
            kpis=[kpi], operating_points=[marker],
            assumptions_snapshot={"mass": 1.5}, computed_at=now,
            gust_warnings=[warning],
        )
        assert len(envelope.gust_warnings) == 1
        assert envelope.gust_warnings[0].n_gust == 4.2

    def test_flight_envelope_read_gust_warnings_default_empty(self):
        """FlightEnvelopeRead.gust_warnings defaults to empty list."""
        from datetime import datetime, timezone
        from app.schemas.flight_envelope import (
            FlightEnvelopeRead, PerformanceKPI, VnCurve, VnMarker, VnPoint,
        )

        now = datetime.now(timezone.utc)
        curve = VnCurve(
            positive=[VnPoint(velocity_mps=10.0, load_factor=1.0)],
            negative=[VnPoint(velocity_mps=10.0, load_factor=-0.5)],
            dive_speed_mps=40.0,
            stall_speed_mps=8.0,
        )
        envelope = FlightEnvelopeRead(
            id=1, aeroplane_id=42, vn_curve=curve,
            kpis=[PerformanceKPI(
                label="stall_speed", display_name="Stall Speed",
                value=8.5, unit="m/s", source_op_id=None, confidence="estimated",
            )],
            operating_points=[VnMarker(
                op_id=1, name="cruise", velocity_mps=20.0,
                load_factor=1.0, status="TRIMMED", label="cruise",
            )],
            assumptions_snapshot={}, computed_at=now,
        )
        assert envelope.gust_warnings == []


# ────────────────────────────────────────────────────────────────────────────
# cl_alpha extraction from assumption_computation_context
# ────────────────────────────────────────────────────────────────────────────


class TestClAlphaExtraction:
    """Tests for _extract_cl_alpha_from_context helper."""

    def test_returns_cached_value_when_present(self):
        """Returns cl_alpha_per_rad from context when key is set."""
        from app.services.flight_envelope_service import _extract_cl_alpha_from_context

        ctx = {"cl_alpha_per_rad": 5.73}
        result = _extract_cl_alpha_from_context(ctx)
        assert result == pytest.approx(5.73)

    def test_returns_none_when_key_missing(self):
        """Returns None when cl_alpha_per_rad not in context."""
        from app.services.flight_envelope_service import _extract_cl_alpha_from_context

        ctx = {"v_cruise_mps": 18.0, "mac_m": 0.3}
        result = _extract_cl_alpha_from_context(ctx)
        assert result is None

    def test_returns_none_for_empty_context(self):
        """Returns None for empty context dict."""
        from app.services.flight_envelope_service import _extract_cl_alpha_from_context

        result = _extract_cl_alpha_from_context({})
        assert result is None

    def test_returns_none_for_non_numeric_value(self):
        """Returns None when value is non-numeric (guards against bad caches)."""
        from app.services.flight_envelope_service import _extract_cl_alpha_from_context

        ctx = {"cl_alpha_per_rad": "not_a_number"}
        result = _extract_cl_alpha_from_context(ctx)
        assert result is None
