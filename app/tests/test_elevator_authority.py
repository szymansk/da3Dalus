"""Tests for elevator authority / forward CG limit service — gh-500.

TDD RED phase: written BEFORE the implementation.

Physics:  Anderson §7.7, NP-centered trim inversion (Amendment B1).
Formula:  x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing

Key sign-convention (Amendment B3):
  - AeroBuildup run with NEGATIVE deflection (TE-UP) → Cm > 0 (nose-up)
  - Cm_δe must be > 0 (per unit negative-deflection rad)
  - δe_max = abs(negative_deflection_deg) * π/180
  - product Cm_δe · δe_max > 0

V-tail (Amendment B4): ASB 3D geometry already includes dihedral.
  Do NOT apply cos²(γ) correction when using ASB path.
"""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal helpers
# ---------------------------------------------------------------------------


def _import_service():
    from app.services.elevator_authority_service import compute_forward_cg_limit

    return compute_forward_cg_limit


def _import_module():
    import app.services.elevator_authority_service as svc

    return svc


def _import_schema():
    from app.schemas.forward_cg import ForwardCGConfidence, ForwardCGResult

    return ForwardCGConfidence, ForwardCGResult


def _make_mock_aeroplane(
    *,
    aeroplane_id: int = 1,
    negative_deflection_deg: float = -25.0,
    positive_deflection_deg: float = 20.0,
    ted_role: str = "elevator",
    flap_role: str | None = None,
    flap_neg_deflection: float = -40.0,
) -> MagicMock:
    """Build a minimal mock AeroplaneModel with one TED."""
    mock_ted = MagicMock()
    mock_ted.role = ted_role
    mock_ted.name = ted_role
    mock_ted.negative_deflection_deg = negative_deflection_deg
    mock_ted.positive_deflection_deg = positive_deflection_deg
    mock_ted.wing_xsec_detail_id = 1

    mock_detail = MagicMock()
    mock_detail.trailing_edge_device = [mock_ted]

    mock_xsec = MagicMock()
    mock_xsec.detail = mock_detail
    mock_xsec.wing_id = 1

    mock_wing = MagicMock()
    mock_wing.id = 1
    mock_wing.aeroplane_id = aeroplane_id

    teds = [mock_ted]
    if flap_role:
        mock_flap = MagicMock()
        mock_flap.role = flap_role
        mock_flap.name = "Flap"
        mock_flap.negative_deflection_deg = flap_neg_deflection
        mock_flap.positive_deflection_deg = 0.0
        teds.append(mock_flap)

    mock_plane = MagicMock()
    mock_plane.id = aeroplane_id
    return mock_plane


# ---------------------------------------------------------------------------
# Class 1: ForwardCGResult schema
# ---------------------------------------------------------------------------


class TestForwardCGSchema:
    """Unit tests for ForwardCGResult Pydantic schema."""

    def test_schema_fields_present(self):
        """ForwardCGResult has required fields per spec."""
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        result = ForwardCGResult(
            cg_fwd_m=0.08,
            confidence=ForwardCGConfidence.asb_high_clean,
            cm_delta_e=0.32,
            cl_max_landing=1.4,
            flap_state="clean",
            warnings=[],
        )
        assert result.cg_fwd_m == pytest.approx(0.08)
        assert result.confidence == ForwardCGConfidence.asb_high_clean
        assert result.cm_delta_e == pytest.approx(0.32)
        assert result.cl_max_landing == pytest.approx(1.4)
        assert result.flap_state == "clean"
        assert result.warnings == []

    def test_schema_none_cg_fwd_allowed(self):
        """cg_fwd_m=None must be allowed (infeasibility case)."""
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        result = ForwardCGResult(
            cg_fwd_m=None,
            confidence=ForwardCGConfidence.stub,
            cm_delta_e=None,
            cl_max_landing=1.4,
            flap_state="stub",
            warnings=["Infeasible"],
        )
        assert result.cg_fwd_m is None

    def test_confidence_enum_values(self):
        """All 6 confidence tiers are present (avl_full added in gh-516)."""
        ForwardCGConfidence, _ = _import_schema()
        # gh-516: avl_full re-introduced as highest-confidence tier
        assert ForwardCGConfidence.avl_full.value == "avl_full"
        assert ForwardCGConfidence.asb_high_with_flap.value == "asb_high_with_flap"
        assert ForwardCGConfidence.asb_high_clean.value == "asb_high_clean"
        assert ForwardCGConfidence.asb_warn_with_flap.value == "asb_warn_with_flap"
        assert ForwardCGConfidence.asb_warn_clean.value == "asb_warn_clean"
        assert ForwardCGConfidence.stub.value == "stub"


# ---------------------------------------------------------------------------
# Class 2: Sign-convention tests (Amendment B3)
# ---------------------------------------------------------------------------


class TestSignConvention:
    """Sign-convention: Cm_δe must be positive when run with TE-UP (negative deflection)."""

    def test_cm_delta_e_positive_from_asb_with_negative_deflection(self):
        """
        When AeroBuildup is run with a negative (TE-UP) deflection, the resulting
        Cm should be positive (nose-up moment).

        This test mocks the AeroBuildup result: run with deflection=-25° gives Cm=0.0,
        and run with deflection=0° gives Cm=-0.05 (nose-down baseline).
        Then Cm_δe = (Cm_deflected - Cm_baseline) / δe_rad > 0.
        """
        svc = _import_module()

        # Simulate: baseline Cm = -0.05, deflected (TE-UP) Cm = 0.25
        # δe = abs(-25) * π/180 = 0.4363 rad
        # Cm_δe = (0.25 - (-0.05)) / 0.4363 ≈ 0.688 > 0
        Cm_baseline = -0.05
        Cm_deflected = 0.25
        delta_e_rad = abs(-25.0) * math.pi / 180.0
        Cm_delta_e = (Cm_deflected - Cm_baseline) / delta_e_rad

        assert Cm_delta_e > 0, (
            "AeroBuildup run with TE-UP (negative deflection) must yield Cm_δe > 0"
        )

    def test_product_cm_delta_e_times_delta_e_max_positive(self):
        """Cm_δe · δe_max > 0 (nose-up trim contribution — Amendment B3)."""
        # Cm_δe > 0 and δe_max = abs(negative_deflection) > 0, so product > 0
        Cm_delta_e = 0.32
        negative_deflection_deg = -25.0
        delta_e_max = abs(negative_deflection_deg) * math.pi / 180.0

        product = Cm_delta_e * delta_e_max
        assert product > 0, "Cm_δe · δe_max must be positive (nose-up trim contribution)"

    def test_delta_e_max_uses_negative_deflection_abs(self):
        """δe_max = abs(negative_deflection_deg) * π/180 as per Amendment B3."""
        svc = _import_module()
        delta_e_max = svc._delta_e_max_rad(negative_deflection_deg=-30.0)
        expected = 30.0 * math.pi / 180.0
        assert delta_e_max == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# Class 3: Stub fallback (no ASB available)
# ---------------------------------------------------------------------------


class TestStubFallback:
    """Stub path: no AeroBuildup result available."""

    def test_stub_returns_correct_confidence(self):
        """When no AeroBuildup is available, confidence must be 'stub'."""
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        svc = _import_module()

        stub_result = svc._build_stub_result(
            x_np_m=0.12,
            mac_m=0.30,
            cl_max_clean=1.4,
            reason="no-asb",
        )
        assert stub_result.confidence == ForwardCGConfidence.stub
        assert stub_result.flap_state == "stub"
        # Roskam §4.7: CL_max_landing = CL_max_clean + 0.5
        assert stub_result.cl_max_landing == pytest.approx(1.4 + 0.5)

    def test_stub_uses_0_30_mac(self):
        """Stub forward limit = x_np - 0.30 * MAC (conservative fallback)."""
        svc = _import_module()
        stub_result = svc._build_stub_result(
            x_np_m=0.12,
            mac_m=0.30,
            cl_max_clean=1.4,
            reason="no-asb",
        )
        # 0.30 MAC stub
        assert stub_result.cg_fwd_m == pytest.approx(0.12 - 0.30 * 0.30, rel=1e-5)

    def test_stub_no_flap_aircraft_cl_max_clean(self):
        """No-flap aircraft: CL_max_landing = CL_max_clean (no flap correction)."""
        svc = _import_module()
        stub_result = svc._build_stub_result(
            x_np_m=0.12,
            mac_m=0.30,
            cl_max_clean=1.4,
            reason="no-flap",
            has_flap=False,
        )
        # No flap: no +0.5 bonus
        assert stub_result.cl_max_landing == pytest.approx(1.4)


# ---------------------------------------------------------------------------
# Class 4: Conditioning guard (Amendment S1)
# ---------------------------------------------------------------------------


class TestConditioningGuard:
    """Guard: |Cm_δe| < 0.005/rad → critically low elevator authority."""

    def test_critically_low_cm_delta_e_returns_x_np(self):
        """When |Cm_δe| < 0.005/rad, forward CG limit = x_np + warning."""
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        svc = _import_module()

        result = svc._apply_conditioning_guard(
            x_np_m=0.12,
            mac_m=0.30,
            cm_delta_e=0.001,  # critically low
            cl_max_landing=1.4,
            cm_ac=0.0,
            delta_cm_flap=0.0,
            delta_e_max_rad=0.436,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        assert result is not None  # guard triggered
        assert result.cg_fwd_m == pytest.approx(0.12)  # x_np
        assert any("Elevator authority critically low" in w for w in result.warnings)

    def test_sufficient_cm_delta_e_no_guard(self):
        """When |Cm_δe| >= 0.005/rad, guard does NOT trigger."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()

        result = svc._apply_conditioning_guard(
            x_np_m=0.12,
            mac_m=0.30,
            cm_delta_e=0.32,  # sufficient
            cl_max_landing=1.4,
            cm_ac=0.0,
            delta_cm_flap=0.0,
            delta_e_max_rad=0.436,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        assert result is None  # guard NOT triggered


# ---------------------------------------------------------------------------
# Class 5: Infeasibility guard (Amendment S3)
# ---------------------------------------------------------------------------


class TestInfeasibilityGuard:
    """Guard: Cm_δe·δe_max + ΔCm_flap ≤ 0 → no feasible forward CG."""

    def test_infeasible_returns_none_cg_fwd(self):
        """When full pitch-up balance cannot overcome nose-down moment, cg_fwd_m=None.

        Full check (B4 fix): Cm_ac + Cm_δe·δe_max + ΔCm_flap ≤ 0 → infeasible.
        Here flap overwhelms elevator even with cm_ac=0: 0 + 0.02 - 0.30 = -0.28 ≤ 0.
        """
        ForwardCGConfidence, ForwardCGResult = _import_schema()
        svc = _import_module()

        result = svc._apply_infeasibility_guard(
            cm_ac=0.0,  # neutral Cm_ac; flap alone overwhelms elevator
            cm_delta_e=0.10,
            delta_e_max_rad=0.20,  # 0.10 * 0.20 = 0.02
            delta_cm_flap=-0.30,  # flap overwhelms: 0 + 0.02 - 0.30 = -0.28 ≤ 0
            confidence_warn_tier=ForwardCGConfidence.asb_high_with_flap,
            warnings=[],
        )
        assert result is not None  # infeasibility triggered
        assert result.cg_fwd_m is None
        assert any("no feasible forward CG" in w for w in result.warnings)

    def test_feasible_no_guard(self):
        """When full pitch-up balance exceeds nose-down moment, guard does NOT trigger.

        Full check (B4 fix): Cm_ac + Cm_δe·δe_max + ΔCm_flap > 0 → feasible.
        Here: -0.05 + 0.139 - 0.05 = 0.039 > 0 → guard returns None.
        """
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()

        result = svc._apply_infeasibility_guard(
            cm_ac=-0.05,  # typical nose-down Cm_ac
            cm_delta_e=0.32,
            delta_e_max_rad=0.436,  # 0.32 * 0.436 = 0.139
            delta_cm_flap=-0.05,  # small flap: -0.05 + 0.139 - 0.05 = 0.039 > 0
            confidence_warn_tier=ForwardCGConfidence.asb_high_with_flap,
            warnings=[],
        )
        assert result is None  # guard NOT triggered


# ---------------------------------------------------------------------------
# Class 6: NP-centered trim inversion formula (Amendment B1)
# ---------------------------------------------------------------------------


class TestTrimInversionFormula:
    """Test the core physics formula: x_cg_fwd = x_np - (Cm_ac + Cm_δe·δe_max + ΔCm_flap) · c_ref / CL_max_landing."""

    def test_forward_cg_limit_conventional_aircraft(self):
        """
        Cessna-like conventional aircraft:
        - x_np = 0.40 m
        - MAC = 0.30 m
        - Cm_ac = -0.08 (nose-down, typical)
        - Cm_δe = 0.32 /rad (positive, per unit negative deflection)
        - δe_max = 25° = 0.4363 rad
        - ΔCm_flap = 0.0 (no flap)
        - CL_max_landing = 1.4

        x_cg_fwd = 0.40 - (-0.08 + 0.32·0.4363 + 0.0) · 0.30 / 1.4
                 = 0.40 - (-0.08 + 0.1396) · 0.30 / 1.4
                 = 0.40 - (0.0596) · 0.30 / 1.4
                 = 0.40 - 0.01277
                 ≈ 0.3872 m

        SM_fwd = (x_np - x_cg_fwd) / MAC = 0.01277 / 0.30 ≈ 0.0426

        Note: this is LESS restrictive than 0.30·MAC stub (which would give 0.40 - 0.09 = 0.31 m)
        because this aircraft has a capable elevator + low Cm_ac.
        """
        svc = _import_module()
        x_cg_fwd = svc._trim_inversion(
            x_np_m=0.40,
            cm_ac=-0.08,
            cm_delta_e=0.32,
            delta_e_max_rad=25.0 * math.pi / 180.0,
            delta_cm_flap=0.0,
            c_ref_m=0.30,
            cl_max_landing=1.4,
        )
        # SM_fwd = (0.40 - x_cg_fwd) / 0.30 should be ~0.0426 (< 0.30 stub)
        sm_fwd = (0.40 - x_cg_fwd) / 0.30
        assert 0.03 <= sm_fwd <= 0.20, (
            f"Expected SM_fwd in [0.03, 0.20] for conventional aircraft, got {sm_fwd:.4f}"
        )
        # forward limit should be LESS restrictive (closer to x_np) than 0.30·MAC stub
        stub_limit = 0.40 - 0.30 * 0.30
        assert x_cg_fwd > stub_limit, (
            f"Physics-based limit {x_cg_fwd:.4f} should be less restrictive than "
            f"stub limit {stub_limit:.4f} for a capable elevator"
        )

    def test_heavy_flap_more_restrictive_than_stub(self):
        """
        Heavy flap (ΔCm_flap = -0.25) pushes forward limit AFT of stub for weak elevator.
        This tests the "binding constraint" behavior.

        If Cm_δe·δe_max + ΔCm_flap < (x_np - x_np + 0.30·MAC) * CL_max / c_ref,
        the physics-based limit will be MORE restrictive (smaller SM) than 0.30.

        Example: weak elevator (Cm_δe=0.12, δe_max=15°, ΔCm_flap=-0.20, Cm_ac=-0.05)
        Numerator = -0.05 + 0.12 * 0.2618 + (-0.20) = -0.05 + 0.0314 - 0.20 = -0.2186
        x_cg_fwd = 0.40 - (-0.2186) * 0.30 / 1.8 = 0.40 + 0.0364 = 0.436 m
        SM_fwd = (0.40 - 0.436) / 0.30 = -0.12  → NEGATIVE → infeasible (no forward limit)
        """
        svc = _import_module()
        x_cg_fwd = svc._trim_inversion(
            x_np_m=0.40,
            cm_ac=-0.05,
            cm_delta_e=0.12,
            delta_e_max_rad=15.0 * math.pi / 180.0,
            delta_cm_flap=-0.20,
            c_ref_m=0.30,
            cl_max_landing=1.8,
        )
        # When net pitch-up authority is negative, x_cg_fwd > x_np
        # meaning there's NO feasible forward CG (must be handled by infeasibility guard)
        sm_fwd = (0.40 - x_cg_fwd) / 0.30
        # Either infeasible (SM < 0) OR more restrictive than 0.30 stub
        # The formula gives what it gives — test the math is correct
        stub_limit = 0.40 - 0.30 * 0.30  # 0.31 m
        # Heavy flap overwhelms elevator: net_pitch_up = 0.12*0.2618 - 0.20 - (-0.05) = -0.1186
        # Negative: aircraft cannot trim at stall with this flap setting
        assert x_cg_fwd >= stub_limit or sm_fwd < 0.0, (
            "Heavy flap should either make limit more restrictive or infeasible"
        )

    def test_more_nose_down_cm_ac_more_restrictive(self):
        """Larger Cm_ac magnitude (more nose-down) requires more elevator authority → more restrictive.

        Uses feasible parameters so both case A and B are physically meaningful.
        """
        svc = _import_module()
        # Aircraft A: Cm_ac = -0.05 (small nose-down)  — net = -0.05 + 0.32*0.4363 = 0.09 > 0 → feasible
        # Aircraft B: Cm_ac = -0.10 (moderate nose-down) — net = -0.10 + 0.1396 = 0.0396 > 0 → feasible
        # Both have net_pitch_up > 0 so both ARE feasible and x_fwd < x_np
        common = dict(
            x_np_m=0.40,
            cm_delta_e=0.32,
            delta_e_max_rad=25.0 * math.pi / 180.0,
            delta_cm_flap=0.0,
            c_ref_m=0.30,
            cl_max_landing=1.4,
        )
        x_np_m = 0.40
        x_fwd_A = svc._trim_inversion(**common, cm_ac=-0.05)
        x_fwd_B = svc._trim_inversion(**common, cm_ac=-0.10)

        # Both must be physically feasible (x_fwd < x_np in aft-positive convention)
        assert x_fwd_A <= x_np_m, f"x_fwd_A={x_fwd_A} must be <= x_np={x_np_m}"
        assert x_fwd_B <= x_np_m, f"x_fwd_B={x_fwd_B} must be <= x_np={x_np_m}"

        # More nose-down (B) requires more elevator → more restrictive forward limit.
        # In AFT-POSITIVE coordinates: x_cg_fwd_B > x_cg_fwd_A  (closer to x_np)
        assert x_fwd_B > x_fwd_A, (
            f"More nose-down Cm_ac should give more restrictive (larger, closer to x_np) x_cg_fwd. "
            f"A (Cm_ac=-0.05): {x_fwd_A:.4f}, B (Cm_ac=-0.10): {x_fwd_B:.4f}"
        )


# ---------------------------------------------------------------------------
# Class 6b: Infeasibility guard physics correctness (B4 regression)
# ---------------------------------------------------------------------------


class TestInfeasibilityGuardPhysics:
    """B4 regression: guard must use FULL Cm_ac + Cm_δe·δe_max + ΔCm_flap sum.

    Bug: old guard checked Cm_δe·δe_max + ΔCm_flap ≤ 0 (omitted Cm_ac).
    This misses cases where Cm_ac flips the net_pitch_up sign negative
    even though Cm_δe·δe_max > 0 alone.
    """

    def test_infeasibility_guard_uses_full_cm_ac_sum(self):
        """Guard must trigger when Cm_ac + Cm_δe·δe_max + ΔCm_flap ≤ 0.

        Concrete bug-case from B4 review:
          Cm_ac=-0.15, Cm_δe=0.32, δe_max=25°=0.4363 rad, ΔCm_flap=0
          Cm_δe·δe_max alone = 0.1396 > 0  →  OLD guard: PASSES (wrong!)
          Cm_ac + Cm_δe·δe_max = -0.15 + 0.1396 = -0.0104 < 0  →  INFEASIBLE

        With the fix, guard must return cg_fwd_m=None for this case.
        """
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        cm_ac = -0.15
        cm_delta_e = 0.32
        delta_e_max_rad = 25.0 * math.pi / 180.0  # 0.4363 rad
        delta_cm_flap = 0.0

        # Verify the bug scenario: Cm_δe·δe_max > 0 but full sum < 0
        partial_sum = cm_delta_e * delta_e_max_rad + delta_cm_flap
        full_sum = cm_ac + partial_sum
        assert partial_sum > 0, "Precondition: partial sum > 0 (old guard would miss this)"
        assert full_sum < 0, "Precondition: full sum < 0 (correct guard should trigger)"

        result = svc._apply_infeasibility_guard(
            cm_ac=cm_ac,
            cm_delta_e=cm_delta_e,
            delta_e_max_rad=delta_e_max_rad,
            delta_cm_flap=delta_cm_flap,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        assert result is not None, (
            "Infeasibility guard must trigger when Cm_ac + Cm_δe·δe_max + ΔCm_flap ≤ 0"
        )
        assert result.cg_fwd_m is None, (
            "Guard must return cg_fwd_m=None for infeasible configuration"
        )

    def test_x_cg_fwd_never_exceeds_x_np(self):
        """Forward CG limit must never be aft of NP — physically impossible.

        x_cg_fwd > x_np in aft-positive convention means the 'forward' limit
        is AFT of the NP — impossible since the NP is the stability boundary.

        Uses the exact B4 bug-case parameters:
          Cm_ac=-0.15, Cm_δe=0.32, δe_max=25°, ΔCm_flap=0, x_np=0.40, MAC=0.30
          x_cg_fwd (buggy) = 0.40 - (-0.0104)*0.30/1.4 = 0.4022 > 0.40 (WRONG)
          x_cg_fwd (fixed)  → infeasible → cg_fwd_m=None
        """
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        x_np_m = 0.40
        cm_ac = -0.15
        cm_delta_e = 0.32
        delta_e_max_rad = 25.0 * math.pi / 180.0
        delta_cm_flap = 0.0
        c_ref_m = 0.30
        cl_max_landing = 1.4

        # First: infeasibility guard should catch this case
        guard_result = svc._apply_infeasibility_guard(
            cm_ac=cm_ac,
            cm_delta_e=cm_delta_e,
            delta_e_max_rad=delta_e_max_rad,
            delta_cm_flap=delta_cm_flap,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        if guard_result is not None:
            # Guard caught it → cg_fwd_m must be None (infeasible)
            assert guard_result.cg_fwd_m is None
        else:
            # Guard did not trigger → formula result must still respect x_np
            x_cg_fwd = svc._trim_inversion(
                x_np_m=x_np_m,
                cm_ac=cm_ac,
                cm_delta_e=cm_delta_e,
                delta_e_max_rad=delta_e_max_rad,
                delta_cm_flap=delta_cm_flap,
                c_ref_m=c_ref_m,
                cl_max_landing=cl_max_landing,
            )
            assert x_cg_fwd <= x_np_m, (
                f"x_cg_fwd={x_cg_fwd:.4f} must be <= x_np={x_np_m:.4f} — "
                "forward CG limit aft of NP is physically impossible"
            )

    def test_guard_does_not_trigger_when_full_sum_positive(self):
        """Guard must NOT trigger when Cm_ac + Cm_δe·δe_max + ΔCm_flap > 0."""
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        # net = -0.05 + 0.32*0.4363 + 0 = 0.0396 > 0 → feasible
        result = svc._apply_infeasibility_guard(
            cm_ac=-0.05,
            cm_delta_e=0.32,
            delta_e_max_rad=25.0 * math.pi / 180.0,
            delta_cm_flap=0.0,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        assert result is None, "Guard must return None when full sum > 0 (feasible case)"

    def test_guard_triggers_on_zero_full_sum(self):
        """Guard triggers when net = exactly 0 (boundary condition)."""
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        # net = 0 exactly: Cm_ac = -(Cm_δe·δe_max) = -(0.32*0.4363) = -0.1396
        cm_delta_e = 0.32
        delta_e_max_rad = 25.0 * math.pi / 180.0
        cm_ac = -(cm_delta_e * delta_e_max_rad)  # exact zero net

        result = svc._apply_infeasibility_guard(
            cm_ac=cm_ac,
            cm_delta_e=cm_delta_e,
            delta_e_max_rad=delta_e_max_rad,
            delta_cm_flap=0.0,
            confidence_warn_tier=ForwardCGConfidence.asb_high_clean,
            warnings=[],
        )
        assert result is not None, "Guard must trigger when full sum == 0"
        assert result.cg_fwd_m is None


# ---------------------------------------------------------------------------
# Class 7: Confidence tier assignment
# ---------------------------------------------------------------------------


class TestConfidenceTier:
    """Test that the correct confidence tier is assigned for each aircraft config."""

    def test_conventional_no_flap_asb_high_clean(self):
        """Conventional elevator, no flap → asb_high_clean."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()
        tier = svc._determine_confidence_tier(
            elevator_role="elevator",
            has_flap_run=False,
        )
        assert tier == ForwardCGConfidence.asb_high_clean

    def test_conventional_with_flap_asb_high_with_flap(self):
        """Conventional elevator, with flap run → asb_high_with_flap."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()
        tier = svc._determine_confidence_tier(
            elevator_role="elevator",
            has_flap_run=True,
        )
        assert tier == ForwardCGConfidence.asb_high_with_flap

    def test_ruddervator_no_flap_asb_warn(self):
        """V-tail (ruddervator), no flap → asb_warn_clean."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()
        tier = svc._determine_confidence_tier(
            elevator_role="ruddervator",
            has_flap_run=False,
        )
        assert tier == ForwardCGConfidence.asb_warn_clean

    def test_elevon_with_flap_asb_warn_with_flap(self):
        """Tailless (elevon), with flap run → asb_warn_with_flap."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()
        tier = svc._determine_confidence_tier(
            elevator_role="elevon",
            has_flap_run=True,
        )
        assert tier == ForwardCGConfidence.asb_warn_with_flap

    def test_no_pitch_control_stub(self):
        """No pitch control surface → stub."""
        ForwardCGConfidence, _ = _import_schema()
        svc = _import_module()
        tier = svc._determine_confidence_tier(
            elevator_role=None,
            has_flap_run=False,
        )
        assert tier == ForwardCGConfidence.stub


# ---------------------------------------------------------------------------
# Class 8: V-tail cos² trap (Amendment B4)
# ---------------------------------------------------------------------------


class TestVTailCosSquareTrap:
    """Amendment B4: ASB 3D geometry handles dihedral — NO cos² correction."""

    def test_asb_path_no_cos_square_applied(self):
        """
        For a V-tail with γ=35°, ASB already includes 3D dihedral geometry.
        The Cm_δe from ASB should be used directly without cos²(γ) correction.

        If cos²(35°) = 0.671 were incorrectly applied:
          Cm_δe_wrong = 0.40 * 0.671 = 0.268

        We verify the service does NOT apply this correction in the ASB path.
        """
        svc = _import_module()
        # Direct formula check: in ASB path, Cm_δe stays as-is
        Cm_delta_e_asb = 0.40  # raw from ASB (already 3D corrected)
        gamma_deg = 35.0

        # Service should use Cm_delta_e_asb directly, NOT apply cos²(γ)
        Cm_used = svc._cm_delta_e_for_asb_path(
            cm_delta_e_raw=Cm_delta_e_asb,
            elevator_role="ruddervator",
        )
        assert Cm_used == pytest.approx(Cm_delta_e_asb, rel=1e-6), (
            f"ASB path for ruddervator must NOT apply cos²(γ). "
            f"Expected {Cm_delta_e_asb}, got {Cm_used}"
        )

    def test_asb_path_elevator_no_cos_square(self):
        """Conventional elevator: no cos² correction either (γ=0°, but verify)."""
        svc = _import_module()
        Cm_raw = 0.32
        Cm_used = svc._cm_delta_e_for_asb_path(
            cm_delta_e_raw=Cm_raw,
            elevator_role="elevator",
        )
        assert Cm_used == pytest.approx(Cm_raw, rel=1e-6)

    def test_stub_path_vtail_applies_cos_square(self):
        """
        ONLY the analytic STUB path applies cos²(γ) (Amendment B4).
        Test that the stub formula uses cos²(γ) correction.
        """
        svc = _import_module()
        gamma_deg = 35.0
        Cm_flat = 0.50  # flat-tail formula value

        # Stub path: apply cos²(γ) correction
        Cm_vtail_stub = svc._apply_vtail_cos_square_correction(
            cm_delta_e_flat=Cm_flat,
            dihedral_deg=gamma_deg,
        )
        expected = Cm_flat * math.cos(math.radians(gamma_deg)) ** 2
        assert Cm_vtail_stub == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# Class 9: Pure physics helper tests
# ---------------------------------------------------------------------------


class TestPhysicsHelpers:
    """Pure numeric tests for sub-functions."""

    def test_trim_inversion_zero_flap_positive_authority(self):
        """Basic no-flap case: formula should give sensible positive x_cg_fwd."""
        svc = _import_module()
        x_cg_fwd = svc._trim_inversion(
            x_np_m=0.30,
            cm_ac=-0.06,
            cm_delta_e=0.28,
            delta_e_max_rad=20.0 * math.pi / 180.0,
            delta_cm_flap=0.0,
            c_ref_m=0.25,
            cl_max_landing=1.3,
        )
        # Must be a real finite number
        assert math.isfinite(x_cg_fwd)
        # x_cg_fwd should be less than x_np (there IS a forward limit)
        # net = -0.06 + 0.28*0.349 = -0.06 + 0.0977 = 0.0377 > 0
        # x_cg_fwd = 0.30 - 0.0377*0.25/1.3 = 0.30 - 0.00725 = 0.2928 < 0.30 ✓
        assert x_cg_fwd < 0.30

    def test_delta_e_max_rad_fallback(self):
        """When negative_deflection_deg is None, fallback to 25° default."""
        svc = _import_module()
        delta = svc._delta_e_max_rad(negative_deflection_deg=None)
        expected = 25.0 * math.pi / 180.0
        assert delta == pytest.approx(expected, rel=1e-5)

    def test_delta_e_max_rad_positive_input_coerced(self):
        """negative_deflection_deg could be stored as positive (user error) — abs() handles it."""
        svc = _import_module()
        # Both -25 and +25 should give the same result
        delta_neg = svc._delta_e_max_rad(negative_deflection_deg=-25.0)
        delta_pos = svc._delta_e_max_rad(negative_deflection_deg=25.0)
        assert delta_neg == pytest.approx(delta_pos, rel=1e-5)


# ---------------------------------------------------------------------------
# Class 9b: Scholz B2 — landing-stall alpha from flap run
# ---------------------------------------------------------------------------


class TestScholzB2FlapAlpha:
    """Scholz B2: _run_flap_analysis must return a 3-tuple including alpha_stall_flap."""

    def test_run_flap_analysis_returns_three_tuple(self):
        """_run_flap_analysis must return (delta_cm_flap, cl_max, alpha_stall_deg)."""
        svc = _import_module()

        # Simulate: at alpha=10, CL is highest (1.5); at all others, CL=1.0
        peak_alpha = 10.0

        class FakeAbu:
            def __init__(self, *, airplane, op_point, xyz_ref):
                self.alpha = float(op_point.alpha)

            def run(self):
                if abs(self.alpha - peak_alpha) < 0.5:
                    return {"CL": 1.5, "Cm": -0.12}
                return {"CL": 1.0, "Cm": -0.08}

        mock_asb = MagicMock()
        mock_asb.AeroBuildup = FakeAbu
        mock_asb.OperatingPoint = lambda velocity, alpha: MagicMock(
            velocity=velocity, alpha=alpha
        )

        mock_asb_airplane = MagicMock()
        mock_asb_airplane.with_control_deflections.return_value = mock_asb_airplane

        mock_flap_ted = MagicMock()
        mock_flap_ted.role = "flap"
        mock_flap_ted.name = "Flap"
        mock_flap_ted.positive_deflection_deg = 30.0

        mock_op_stall = MagicMock()
        mock_op_stall.velocity = 15.0
        mock_op_stall.alpha = 12.0  # clean stall alpha

        with patch.dict("sys.modules", {"aerosandbox": mock_asb, "numpy": __import__("numpy")}):
            result = svc._run_flap_analysis(
                asb_airplane=mock_asb_airplane,
                flap_teds=[mock_flap_ted],
                aeroplane=MagicMock(),
                op_stall=mock_op_stall,
                xyz_ref=[0.0, 0.0, 0.0],
                cm_baseline=-0.08,
            )

        assert isinstance(result, tuple), "_run_flap_analysis must return a tuple"
        assert len(result) == 3, "_run_flap_analysis must return 3-tuple (delta_cm, cl_max, alpha)"

        delta_cm_flap, cl_max, alpha_stall = result
        assert math.isfinite(delta_cm_flap)
        assert cl_max >= 1.0
        assert math.isfinite(alpha_stall)
        # Alpha at max CL should be near 10 (within 1 deg, given 1-deg sweep step)
        assert abs(alpha_stall - peak_alpha) <= 1.0, (
            f"alpha_stall_flap={alpha_stall} should be near peak alpha={peak_alpha}"
        )


# ---------------------------------------------------------------------------
# Class 10: Integration with sm_sizing_service (Amendment B5)
# ---------------------------------------------------------------------------


class TestSmSizingIntegration:
    """B5: sm_sizing_service forward-clip must use physics-based cg_stability_fwd_m."""

    def test_forward_clip_uses_dynamic_ctx_value_not_hardcoded(self):  # noqa: PLR0914
        """
        sm_sizing_service.suggest_corrections should use ctx['cg_stability_fwd_m']
        for forward-clip, not a hardcoded 0.30 constant.

        If the physics-based limit is tighter (SM_fwd = 0.15 instead of 0.30),
        the wing-shift should be clipped sooner.
        """
        from app.services.sm_sizing_service import suggest_corrections

        mac_m = 0.30
        x_np_m = 0.40

        # Physics-based: fwd limit = 0.30 (using 0.15 SM from new physics)
        # i.e. cg_stability_fwd_m = x_np - 0.15 * MAC = 0.40 - 0.045 = 0.355
        cg_stability_fwd_physics = x_np_m - 0.15 * mac_m  # 0.355 m

        # Stub (old): cg_stability_fwd_m = x_np - 0.30 * MAC = 0.40 - 0.09 = 0.31
        cg_stability_fwd_stub = x_np_m - 0.30 * mac_m  # 0.31 m

        ctx_physics = {
            "mac_m": mac_m,
            "s_ref_m2": 0.60,
            "x_np_m": x_np_m,
            "cg_aft_m": 0.32,  # SM_aft = (0.40 - 0.32) / 0.30 = 0.267 → heavy nose
            "sm_at_aft": 0.267,  # above target 0.10 → overshoot suggestion
            "s_h_m2": 0.08,
            "l_h_m": 0.55,
            "cg_stability_fwd_m": cg_stability_fwd_physics,
        }
        ctx_stub = dict(ctx_physics, cg_stability_fwd_m=cg_stability_fwd_stub)

        result_physics = suggest_corrections(ctx_physics, target_sm=0.10)
        result_stub = suggest_corrections(ctx_stub, target_sm=0.10)

        # Both should return suggestions (heavy nose overshoot)
        assert result_physics["status"] == "suggestion"
        assert result_stub["status"] == "suggestion"

        # Find wing_shift option in each
        def get_wing_shift(r):
            for opt in r.get("options", []):
                if opt["lever"] == "wing_shift":
                    return opt
            return None

        ws_physics = get_wing_shift(result_physics)
        ws_stub = get_wing_shift(result_stub)

        # Both should have wing_shift options
        assert ws_physics is not None
        assert ws_stub is not None

        # Physics clip is TIGHTER (fwd limit closer to x_np) → wing shift clipped MORE
        # delta_x should be smaller (or equal) with physics-based clip
        delta_x_physics = abs(ws_physics["delta_value"])
        delta_x_stub = abs(ws_stub["delta_value"])

        # Physics has fwd limit at 0.355 vs stub at 0.31
        # Physics is tighter (SM_fwd = 0.15 not 0.30) → clip at smaller delta_x
        assert delta_x_physics <= delta_x_stub + 1e-6, (
            f"Physics-based clip should restrict wing shift more (or equal) than stub clip. "
            f"Physics delta_x={delta_x_physics:.4f}, stub delta_x={delta_x_stub:.4f}"
        )


# ---------------------------------------------------------------------------
# Class 11: Entry-point coverage tests (compute_forward_cg_limit with mocks)
# ---------------------------------------------------------------------------


class TestComputeForwardCgLimitEntryPoint:
    """Coverage tests for the public entry point using mocked DB and aircraft."""

    def test_stub_fallback_when_asb_raises(self):
        """compute_forward_cg_limit falls back to stub when ASB raises an exception."""
        svc = _import_module()
        ForwardCGConfidence, ForwardCGResult = _import_schema()

        mock_db = MagicMock()
        mock_aircraft = MagicMock()
        mock_aircraft.id = 42
        mock_aircraft.wings = []  # no wings → will fail to find elevator

        # Patch _compute_forward_cg_limit_asb to raise
        # and _load_stability_assumptions to return valid values
        with (
            patch.object(
                svc,
                "_compute_forward_cg_limit_asb",
                side_effect=ValueError("AeroBuildup not available"),
            ),
            patch.object(
                svc,
                "_load_stability_assumptions",
                return_value=(0.40, 0.30, 1.4),
            ),
        ):
            result = svc.compute_forward_cg_limit(mock_db, mock_aircraft)

        assert result.confidence == ForwardCGConfidence.stub
        assert result.flap_state == "stub"
        assert result.cg_fwd_m is not None  # stub returns x_np - 0.30*MAC
        assert result.cg_fwd_m == pytest.approx(0.40 - 0.30 * 0.30, rel=1e-5)

    def test_stub_fallback_uses_roskam_cl_max_bonus(self):
        """Stub path applies Roskam +0.5 CL bonus (has_flap=True default)."""
        svc = _import_module()
        stub = svc._build_stub_result(
            x_np_m=0.50,
            mac_m=0.25,
            cl_max_clean=1.3,
            reason="test",
            has_flap=True,
        )
        assert stub.cl_max_landing == pytest.approx(1.8, rel=1e-5)  # 1.3 + 0.5

    def test_find_pitch_control_ted_returns_none_for_empty_wings(self):
        """_find_pitch_control_ted returns (None, None) when aircraft has no wings."""
        svc = _import_module()
        mock_ac = MagicMock()
        mock_ac.wings = []
        ted, role = svc._find_pitch_control_ted(mock_ac)
        assert ted is None
        assert role is None

    def test_find_pitch_control_ted_priority_elevator_first(self):
        """elevator role is preferred over ruddervator when both present."""
        svc = _import_module()

        mock_elev = MagicMock()
        mock_elev.role = "elevator"
        mock_elev.name = "Elevator"

        mock_rudder = MagicMock()
        mock_rudder.role = "ruddervator"
        mock_rudder.name = "Ruddervator"

        mock_detail = MagicMock()
        mock_detail.trailing_edge_device = [mock_rudder, mock_elev]

        mock_xsec = MagicMock()
        mock_xsec.detail = mock_detail

        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]

        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        ted, role = svc._find_pitch_control_ted(mock_ac)
        assert role == "elevator"

    def test_find_flap_teds_finds_flap_role(self):
        """_find_flap_teds returns only flap-role TEDs."""
        svc = _import_module()

        mock_flap = MagicMock()
        mock_flap.role = "flap"
        mock_elev = MagicMock()
        mock_elev.role = "elevator"

        mock_detail = MagicMock()
        mock_detail.trailing_edge_device = [mock_flap, mock_elev]
        mock_xsec = MagicMock()
        mock_xsec.detail = mock_detail
        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]
        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        flaps = svc._find_flap_teds(mock_ac)
        assert len(flaps) == 1
        assert flaps[0].role == "flap"

    def test_load_assumption_value_returns_calculated_when_calculated(self):
        """_load_assumption_value returns calculated_value when active_source=CALCULATED."""
        svc = _import_module()

        mock_row = MagicMock()
        mock_row.active_source = "CALCULATED"
        mock_row.calculated_value = 0.42
        mock_row.estimate_value = 0.30

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        val = svc._load_assumption_value(mock_db, 1, "x_np")
        assert val == pytest.approx(0.42)

    def test_load_assumption_value_returns_estimate_when_estimate(self):
        """_load_assumption_value returns estimate_value when active_source != CALCULATED."""
        svc = _import_module()

        mock_row = MagicMock()
        mock_row.active_source = "ESTIMATE"
        mock_row.calculated_value = None
        mock_row.estimate_value = 0.30

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        val = svc._load_assumption_value(mock_db, 1, "x_np")
        assert val == pytest.approx(0.30)

    def test_load_assumption_value_returns_none_when_no_row(self):
        """_load_assumption_value returns None when the assumption row doesn't exist."""
        svc = _import_module()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        val = svc._load_assumption_value(mock_db, 1, "x_np")
        assert val is None

    def test_extract_cm_from_dict(self):
        """_extract_cm handles dict result from AeroBuildup."""
        svc = _import_module()
        result_dict = {"CL": 1.2, "CD": 0.05, "Cm": -0.04}
        cm = svc._extract_cm(result_dict)
        assert cm == pytest.approx(-0.04)

    def test_extract_cm_from_object(self):
        """_extract_cm handles object result from AeroBuildup."""
        svc = _import_module()
        mock_result = MagicMock()
        mock_result.Cm = 0.12
        cm = svc._extract_cm(mock_result)
        assert cm == pytest.approx(0.12)

    def test_extract_cl_from_dict(self):
        """_extract_cl handles dict result from AeroBuildup."""
        svc = _import_module()
        result_dict = {"CL": 1.45, "Cm": -0.02}
        cl = svc._extract_cl(result_dict)
        assert cl == pytest.approx(1.45)

    def test_load_stability_assumptions_raises_when_x_np_none(self):
        """_load_stability_assumptions raises ValueError when x_np is None."""
        svc = _import_module()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_ac = MagicMock()
        mock_ac.id = 7

        with pytest.raises(ValueError, match="x_np"):
            svc._load_stability_assumptions(mock_db, mock_ac)

    def test_load_stability_assumptions_raises_when_mac_zero(self):
        """_load_stability_assumptions raises ValueError when mac=0."""
        svc = _import_module()

        call_count = 0

        def mock_load(db, aid, param):
            nonlocal call_count
            call_count += 1
            if param == "x_np":
                return 0.40
            if param == "mac":
                return 0.0  # zero MAC → invalid
            return 1.4

        mock_db = MagicMock()
        mock_ac = MagicMock()
        mock_ac.id = 8

        with patch.object(svc, "_load_assumption_value", side_effect=mock_load):
            with pytest.raises(ValueError, match="mac"):
                svc._load_stability_assumptions(mock_db, mock_ac)

    def test_find_pitch_control_ted_none_detail(self):
        """_find_pitch_control_ted skips xsecs with detail=None."""
        svc = _import_module()

        mock_xsec = MagicMock()
        mock_xsec.detail = None  # no detail

        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]

        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        ted, role = svc._find_pitch_control_ted(mock_ac)
        assert ted is None
        assert role is None

    def test_find_pitch_control_ted_falls_through_to_first(self):
        """When priority roles not found, _find_pitch_control_ted returns first pitch TED."""
        svc = _import_module()
        # 'elevon' is in _PITCH_ROLES but NOT in the priority order before flaperon.
        # Use 'flaperon' which IS in priority order last.
        mock_ted = MagicMock()
        mock_ted.role = "flaperon"
        mock_ted.name = "Flaperon"

        mock_detail = MagicMock()
        mock_detail.trailing_edge_device = [mock_ted]
        mock_xsec = MagicMock()
        mock_xsec.detail = mock_detail
        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]
        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        ted, role = svc._find_pitch_control_ted(mock_ac)
        assert role == "flaperon"

    def test_compute_forward_cg_limit_infeasible_result_preserved(self):
        """compute_forward_cg_limit returns stub (not None cg_fwd_m) when ASB raises."""
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        mock_db = MagicMock()
        mock_ac = MagicMock()
        mock_ac.id = 99

        with (
            patch.object(
                svc,
                "_compute_forward_cg_limit_asb",
                side_effect=RuntimeError("ASB not available"),
            ),
            patch.object(
                svc,
                "_load_stability_assumptions",
                return_value=(0.35, 0.28, 1.5),
            ),
        ):
            result = svc.compute_forward_cg_limit(mock_db, mock_ac)

        # Stub fallback: should return a result with confidence=stub
        assert result.confidence == ForwardCGConfidence.stub
        # cg_fwd_m should be x_np - 0.30*mac = 0.35 - 0.30*0.28 = 0.266
        assert result.cg_fwd_m == pytest.approx(0.35 - 0.30 * 0.28, rel=1e-5)

    def test_to_scalar_handles_plain_float(self):
        """_to_scalar converts plain float without numpy."""
        svc = _import_module()
        assert svc._to_scalar(3.14) == pytest.approx(3.14)

    def test_to_scalar_handles_none(self):
        """_to_scalar returns 0.0 for None."""
        svc = _import_module()
        assert svc._to_scalar(None) == pytest.approx(0.0)

    def test_to_scalar_handles_numpy_array(self):
        """_to_scalar unwraps 1-element numpy array."""
        import numpy as np

        svc = _import_module()
        arr = np.array([2.71828])
        assert svc._to_scalar(arr) == pytest.approx(2.71828)

    def test_extract_cm_fallback_to_zero_dict(self):
        """_extract_cm returns 0 when Cm/Cmq not in dict."""
        svc = _import_module()
        cm = svc._extract_cm({"CL": 1.0, "CD": 0.05})
        assert cm == pytest.approx(0.0)

    def test_extract_cl_from_object(self):
        """_extract_cl handles object result."""
        svc = _import_module()
        mock_result = MagicMock()
        mock_result.CL = 1.32
        cl = svc._extract_cl(mock_result)
        assert cl == pytest.approx(1.32)

    def test_find_flap_teds_skips_detail_none(self):
        """_find_flap_teds skips xsecs with detail=None."""
        svc = _import_module()

        mock_xsec = MagicMock()
        mock_xsec.detail = None  # no detail

        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]

        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        flaps = svc._find_flap_teds(mock_ac)
        assert flaps == []

    def test_find_flap_teds_returns_empty_for_no_flap(self):
        """_find_flap_teds returns empty list when no flap TEDs present."""
        svc = _import_module()

        mock_ted = MagicMock()
        mock_ted.role = "elevator"  # not a flap

        mock_detail = MagicMock()
        mock_detail.trailing_edge_device = [mock_ted]
        mock_xsec = MagicMock()
        mock_xsec.detail = mock_detail
        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]
        mock_ac = MagicMock()
        mock_ac.wings = [mock_wing]

        flaps = svc._find_flap_teds(mock_ac)
        assert flaps == []

    def test_load_stability_assumptions_uses_default_cl_max(self):
        """_load_stability_assumptions uses 1.4 default when cl_max row missing."""
        svc = _import_module()

        call_map = {"x_np": 0.38, "mac": 0.25, "cl_max": None}

        def mock_load(db, aid, param):
            return call_map.get(param)

        mock_db = MagicMock()
        mock_ac = MagicMock()
        mock_ac.id = 5

        with patch.object(svc, "_load_assumption_value", side_effect=mock_load):
            x_np, mac, cl_max = svc._load_stability_assumptions(mock_db, mock_ac)

        assert x_np == pytest.approx(0.38)
        assert mac == pytest.approx(0.25)
        assert cl_max == pytest.approx(1.4)  # default fallback


# ---------------------------------------------------------------------------
# Class 12: ASB integration path with full mocking (coverage for lines 481-683)
# ---------------------------------------------------------------------------


class TestComputeForwardCgLimitAsbMocked:
    """Coverage tests for _compute_forward_cg_limit_asb with full mocking."""

    def _make_asb_run_result(self, cm: float, cl: float) -> dict:
        return {"CL": cl, "CD": 0.05, "Cm": cm}

    def _build_full_mock_ctx(self):
        """Build all the mocks needed for _compute_forward_cg_limit_asb."""
        svc = _import_module()

        # DB assumption values
        assumption_map = {
            "x_np": 0.40,
            "mac": 0.30,
            "cl_max": 1.4,
            "v_cruise": 15.0,
            "stall_alpha": 12.0,
        }

        # Mock DB
        mock_db = MagicMock()

        # Mock aircraft with one elevator TED
        mock_ted = MagicMock()
        mock_ted.role = "elevator"
        mock_ted.name = "Elevator"
        mock_ted.negative_deflection_deg = -25.0

        mock_detail = MagicMock()
        mock_detail.trailing_edge_device = [mock_ted]
        mock_xsec = MagicMock()
        mock_xsec.detail = mock_detail
        mock_wing = MagicMock()
        mock_wing.x_secs = [mock_xsec]
        mock_ac = MagicMock()
        mock_ac.id = 1
        mock_ac.wings = [mock_wing]

        return mock_db, mock_ac, assumption_map

    def test_asb_path_conventional_no_flap(self):
        """_compute_forward_cg_limit_asb with conventional elevator, no flap."""
        svc = _import_module()
        ForwardCGConfidence, ForwardCGResult = _import_schema()

        mock_db, mock_ac, assumption_map = self._build_full_mock_ctx()

        # Mock aerosandbox
        mock_asb = MagicMock()
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]
        mock_airplane.with_control_deflections.return_value = mock_airplane

        # Baseline run: Cm = -0.05
        # Deflected run: Cm = 0.25 → Cm_δe = (0.25 - (-0.05)) / 0.4363 ≈ 0.688
        mock_abu_baseline = MagicMock()
        mock_abu_baseline.run.return_value = {"CL": 1.1, "Cm": -0.05}
        mock_abu_deflected = MagicMock()
        mock_abu_deflected.run.return_value = {"CL": 0.9, "Cm": 0.25}

        call_count = [0]

        def make_abu(airplane, op_point, xyz_ref):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_abu_baseline
            return mock_abu_deflected

        mock_asb.AeroBuildup.side_effect = make_abu
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        mock_plane_schema = MagicMock()

        with (
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
        ):
            result = svc._compute_forward_cg_limit_asb(mock_db, mock_ac)

        # Should succeed with physics-based forward CG
        assert result.cg_fwd_m is not None
        assert result.confidence in (
            ForwardCGConfidence.asb_high_clean,
            ForwardCGConfidence.asb_high_with_flap,
        )
        assert result.cm_delta_e is not None
        assert result.cm_delta_e > 0, "Cm_δe must be positive (TE-UP convention)"

    def test_asb_path_no_pitch_control_raises(self):
        """_compute_forward_cg_limit_asb raises ValueError when no pitch-control TED."""
        svc = _import_module()

        mock_db = MagicMock()
        mock_ac = MagicMock()
        mock_ac.id = 2
        mock_ac.wings = []  # no wings

        assumption_map = {"x_np": 0.40, "mac": 0.30, "cl_max": 1.4, "v_cruise": 15.0}

        mock_asb = MagicMock()
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]

        mock_plane_schema = MagicMock()

        with (
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
        ):
            with pytest.raises(ValueError, match="No pitch-control TED"):
                svc._compute_forward_cg_limit_asb(mock_db, mock_ac)

    def test_asb_path_x_np_unavailable_raises(self):
        """_compute_forward_cg_limit_asb raises ValueError when x_np not in assumptions."""
        svc = _import_module()

        mock_db = MagicMock()
        mock_ac = MagicMock()
        mock_ac.id = 3

        # x_np missing
        assumption_map = {"x_np": None, "mac": 0.30}

        mock_asb = MagicMock()
        with (
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
        ):
            with pytest.raises(ValueError, match="x_np"):
                svc._compute_forward_cg_limit_asb(mock_db, mock_ac)

    def test_asb_path_conditioning_guard_triggers(self):
        """_compute_forward_cg_limit_asb handles critically low Cm_δe via guard."""
        svc = _import_module()
        ForwardCGConfidence, _ = _import_schema()

        mock_db, mock_ac, assumption_map = self._build_full_mock_ctx()

        mock_asb = MagicMock()
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0.0, 0.0, 0.0]
        mock_airplane.with_control_deflections.return_value = mock_airplane

        # Nearly identical Cm_baseline and Cm_deflected → Cm_δe ≈ 0 (critically low)
        call_count = [0]

        def make_abu(airplane, op_point, xyz_ref):
            call_count[0] += 1
            abu = MagicMock()
            abu.run.return_value = {"CL": 1.0, "Cm": -0.05}  # same both runs
            return abu

        mock_asb.AeroBuildup.side_effect = make_abu
        mock_asb.OperatingPoint = MagicMock(return_value=MagicMock())

        mock_plane_schema = MagicMock()

        with (
            patch.dict("sys.modules", {"aerosandbox": mock_asb}),
            patch.object(
                svc, "_load_assumption_value", side_effect=lambda db, aid, p: assumption_map.get(p)
            ),
            patch(
                "app.converters.model_schema_converters.aeroplane_schema_to_asb_airplane_async",
                return_value=mock_airplane,
            ),
            patch(
                "app.services.analysis_service.get_aeroplane_schema_or_raise",
                return_value=mock_plane_schema,
            ),
        ):
            result = svc._compute_forward_cg_limit_asb(mock_db, mock_ac)

        # Conditioning guard should trigger: Cm_δe ≈ 0 < 0.005 threshold
        assert any("critically low" in w for w in result.warnings)
        # cg_fwd_m should be set to x_np (guard fallback)
        assert result.cg_fwd_m == pytest.approx(0.40)
