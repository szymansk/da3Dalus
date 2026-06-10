"""TDD tests for turbulator mandatory AeroBuildup integration — gh-935 Part D.

Verifies that when an aircraft's main wing has an ENABLED turbulator with a
set position, the turbulator's ΔCD0 is ADDED to the computed cd0 in the
recompute path.

Strategy
--------
All tests are in the fast tier: the AeroBuildup / NeuralFoil boundary is
monkeypatched with a deterministic stub. The test architecture:
1. build_turbulator_wing_sections_for_aircraft() — new service function
2. integrate_turbulator_delta_into_cd0() — applies ΔCD0 on top of raw cd0

The monkeypatch uses the xtr-aware fake from test_turbulator_optimizer_service:
  xtr=1.0 → cd=0.030 (natural transition)
  xtr=0.1 → cd=0.015 (tripped; note: outside our grid so it's the boundary value)

Tests:
- No turbulator → ΔCD0 = 0, cd0 unchanged
- Enabled turbulator at xtr=0.5 → ΔCD0 < 0, cd0 reduced
- Disabled turbulator → ΔCD0 = 0, cd0 unchanged
- NaN δcd from section → logged warning, not a silent crash
"""

from __future__ import annotations

import math

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# xtr-aware fake (same as test_turbulator_optimizer_service.py)
# ---------------------------------------------------------------------------


def _fake_neuralfoil_result_xtr(alpha: np.ndarray, *, xtr_upper: float = 1.0, **kw) -> dict:
    alphas = np.atleast_1d(alpha)
    cd_base = 0.010
    cd_bubble = 0.020
    cd_at_xtr = cd_base + cd_bubble * (xtr_upper - 0.4) ** 2 / (0.6**2)
    return {
        "CL": np.full_like(alphas, 0.6, dtype=float),
        "CD": np.full_like(alphas, cd_at_xtr, dtype=float),
        "analysis_confidence": np.full_like(alphas, 0.95, dtype=float),
    }


@pytest.fixture()
def mock_neuralfoil_xtr(monkeypatch):
    """Patch asb.Airfoil.get_aero_from_neuralfoil with the xtr-aware fake."""
    import sys
    import types

    if "aerosandbox" not in sys.modules:
        asb_mod = types.ModuleType("aerosandbox")

        class FakeAirfoil:
            def __init__(self, name=None, coordinates=None):
                self.name = name or "naca0012"
                self.coordinates = coordinates

            def get_aero_from_neuralfoil(self, alpha, Re, xtr_upper=1.0, **kw):
                return _fake_neuralfoil_result_xtr(np.atleast_1d(alpha), xtr_upper=xtr_upper)

        asb_mod.Airfoil = FakeAirfoil
        sys.modules["aerosandbox"] = asb_mod

    import aerosandbox as asb

    def _fake(self, alpha, Re, xtr_upper=1.0, **kw):
        return _fake_neuralfoil_result_xtr(np.atleast_1d(alpha), xtr_upper=xtr_upper)

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", _fake)
    return asb


# ---------------------------------------------------------------------------
# Helpers: minimal WingSectionData lists
# ---------------------------------------------------------------------------


def _make_sections(xtr_root: float = 0.4, xtr_tip: float = 0.4):
    """Two-section stub for integration tests."""
    from app.services.turbulator_optimizer_service import WingSectionData

    return [
        WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                        airfoil_name="naca0012", section_area_m2=0.10),
        WingSectionData(y_m=0.3, chord_m=0.15, cl=0.5, re_local=150_000,
                        airfoil_name="naca0012", section_area_m2=0.08),
    ]


# ---------------------------------------------------------------------------
# compute_delta_cd0_from_turbulator_position (the Part D helper)
# ---------------------------------------------------------------------------


class TestComputeDeltaCd0FromTurbulatorPosition:
    def test_no_sections_returns_zero(self, mock_neuralfoil_xtr):
        from app.services.turbulator_optimizer_service import (
            compute_delta_cd0_from_turbulator_position,
        )

        delta, warnings = compute_delta_cd0_from_turbulator_position([], 0.4, 0.4, s_ref=0.4)
        assert delta == 0.0
        assert warnings == []

    def test_natural_transition_xtr1_gives_zero_delta(self, mock_neuralfoil_xtr):
        """At xtr=1.0 (natural transition), the tripped cd = clean cd → ΔCD0 = 0."""
        from app.services.turbulator_optimizer_service import (
            compute_delta_cd0_from_turbulator_position,
        )

        sections = _make_sections()
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=1.0, xtr_tip=1.0, s_ref=0.4
        )
        assert delta == pytest.approx(0.0, abs=1e-9)

    def test_tripped_xtr_reduces_cd0(self, mock_neuralfoil_xtr):
        """At xtr=0.4, tripped cd < clean cd (bubble killed) → negative ΔCD0."""
        from app.services.turbulator_optimizer_service import (
            compute_delta_cd0_from_turbulator_position,
        )

        sections = _make_sections()
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=0.4
        )
        assert delta < 0.0, f"Expected negative ΔCD0 (turbulator kills bubble), got {delta}"

    def test_delta_is_area_weighted(self, mock_neuralfoil_xtr):
        """ΔCD0 = Σ (cd_trip - cd_clean) * S_i / S_ref; verify numerics."""
        from app.services.turbulator_optimizer_service import (
            _cd_at_cl_xtr,
            compute_delta_cd0_from_turbulator_position,
        )
        import aerosandbox as asb

        sections = _make_sections()
        s_ref = 0.4
        # xtr=0.4 for both root and tip → same xtr everywhere

        delta, _ = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=s_ref
        )

        # Compute expected manually for section 0
        af = asb.Airfoil(name="naca0012")
        cd_clean_0 = _cd_at_cl_xtr(af, 0.6, 200_000, xtr_upper=1.0)
        cd_trip_0 = _cd_at_cl_xtr(af, 0.6, 200_000, xtr_upper=0.4)
        cd_clean_1 = _cd_at_cl_xtr(af, 0.5, 150_000, xtr_upper=1.0)
        cd_trip_1 = _cd_at_cl_xtr(af, 0.5, 150_000, xtr_upper=0.4)
        expected = ((cd_trip_0 - cd_clean_0) * 0.10 + (cd_trip_1 - cd_clean_1) * 0.08) / s_ref
        assert delta == pytest.approx(expected, rel=1e-5)


# ---------------------------------------------------------------------------
# apply_turbulator_delta_to_cd0 (the injection function used in recompute_assumptions)
# ---------------------------------------------------------------------------


class TestApplyTurbulatorDeltaToRawCd0:
    """Tests for the function that modifies the raw cd0 computed by AeroBuildup."""

    def test_no_turbulator_cd0_unchanged(self, mock_neuralfoil_xtr):
        """Wing with no turbulator → ΔCD0 = 0 → cd0 returned unchanged."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0

        raw_cd0 = 0.030
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=[],
            xtr_root=None,
            xtr_tip=None,
            s_ref=0.4,
        )
        assert result == pytest.approx(raw_cd0, abs=1e-12)

    def test_disabled_turbulator_cd0_unchanged(self, mock_neuralfoil_xtr):
        """Disabled turbulator (enabled=False) → ΔCD0 = 0 → cd0 unchanged."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0

        sections = _make_sections()
        raw_cd0 = 0.030
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=None,  # None signals disabled/absent
            xtr_tip=None,
            s_ref=0.4,
        )
        assert result == pytest.approx(raw_cd0, abs=1e-12)

    def test_enabled_turbulator_modifies_cd0(self, mock_neuralfoil_xtr):
        """Enabled turbulator at xtr=0.4 → ΔCD0 applied → cd0 changes."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0

        sections = _make_sections()
        raw_cd0 = 0.030
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=0.4,
            xtr_tip=0.4,
            s_ref=0.4,
        )
        # xtr=0.4 kills bubble → cd_tripped < cd_clean → ΔCD0 < 0 → result < raw_cd0
        assert result < raw_cd0

    def test_cd0_never_goes_negative(self, mock_neuralfoil_xtr, monkeypatch):
        """Even with a pathological ΔCD0, the returned cd0 must stay positive."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0
        from app.services import turbulator_optimizer_service as tos

        sections = _make_sections()

        # Monkeypatch to return a huge negative delta
        original = tos.compute_delta_cd0_from_turbulator_position

        def _huge_negative(*a, **kw):
            return -999.0, []

        monkeypatch.setattr(tos, "compute_delta_cd0_from_turbulator_position", _huge_negative)

        raw_cd0 = 0.030
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=0.4,
            xtr_tip=0.4,
            s_ref=0.4,
        )
        assert result > 0.0, f"cd0 must stay positive, got {result}"
