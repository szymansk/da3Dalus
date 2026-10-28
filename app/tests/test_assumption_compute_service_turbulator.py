"""Fast mocked tests for assumption_compute_service turbulator helpers — gh-935.

Covers the lines NOT exercised by test_assumption_compute_service.py:
  - _extract_main_wing_turbulator_xtr (lines 2205-2241)
  - apply_turbulator_delta_to_cd0 guard branches (lines 2133-2168):
      recompute injection branch (turbulator enabled path calling compute_delta_cd0)

All tests are in the fast tier — no real AeroSandbox.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Tests: _extract_main_wing_turbulator_xtr
# ---------------------------------------------------------------------------


class TestExtractMainWingTurbulatorXtr:
    """_extract_main_wing_turbulator_xtr(aircraft) → (xtr_root, xtr_tip, enabled)."""

    def _make_aircraft(self, wings):
        return SimpleNamespace(wings=wings)

    def _make_wing_with_turbulator(
        self, chord=200.0, span=500.0, enabled=True, pos_root=0.4, pos_tip=0.6,
        with_turbulator=True, surface_type="main_wing",
    ):
        """Build a minimal ORM-like wing stub."""
        turb = None
        if with_turbulator:
            turb = SimpleNamespace(
                enabled=enabled,
                position_root=pos_root,
                position_tip=pos_tip,
            )
        xsec = SimpleNamespace(
            xyz_le=[0.0, 0.0, 0.0],
            chord=chord,
            turbulator=turb,
        )
        xsec_tip = SimpleNamespace(
            xyz_le=[0.0, span, 0.0],
            chord=chord * 0.6,
            turbulator=None,
        )
        return SimpleNamespace(x_secs=[xsec, xsec_tip], surface_type=surface_type)

    def test_no_wings_returns_none(self):
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        aircraft = self._make_aircraft([])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        assert xtr_root is None
        assert xtr_tip is None
        assert enabled is False

    def test_wing_without_turbulator_returns_none(self):
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        wing = self._make_wing_with_turbulator(with_turbulator=False)
        aircraft = self._make_aircraft([wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        assert xtr_root is None
        assert xtr_tip is None
        assert enabled is False

    def test_disabled_turbulator_returns_false(self):
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        wing = self._make_wing_with_turbulator(enabled=False, pos_root=0.4, pos_tip=0.6)
        aircraft = self._make_aircraft([wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        assert enabled is False
        assert xtr_root is None
        assert xtr_tip is None

    def test_enabled_turbulator_with_positions_returns_values(self):
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        wing = self._make_wing_with_turbulator(enabled=True, pos_root=0.35, pos_tip=0.55)
        aircraft = self._make_aircraft([wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        assert enabled is True
        assert xtr_root == pytest.approx(0.35, abs=1e-9)
        assert xtr_tip == pytest.approx(0.55, abs=1e-9)

    def test_selects_wing_by_surface_type_not_by_area_or_order(self):
        """Main wing is the wing with role main_wing, even if a tail is larger and listed first."""
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        # Huge tail wing listed FIRST, with its own turbulator at different values
        tail_wing = self._make_wing_with_turbulator(
            chord=900.0,
            span=2000.0,
            enabled=True,
            pos_root=0.7,
            pos_tip=0.8,
            surface_type="horizontal_tail",
        )
        # Small wing carrying the main_wing role
        main_wing = self._make_wing_with_turbulator(
            chord=80.0,
            span=200.0,
            enabled=True,
            pos_root=0.4,
            pos_tip=0.6,
            surface_type="main_wing",
        )
        aircraft = self._make_aircraft([tail_wing, main_wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)

        assert enabled is True
        assert xtr_root == pytest.approx(0.4, abs=1e-9)
        assert xtr_tip == pytest.approx(0.6, abs=1e-9)

    def test_turbulator_with_none_positions_returns_none(self):
        """Turbulator enabled but positions not set → (None, None, False) equivalent."""
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        turb = SimpleNamespace(enabled=True, position_root=None, position_tip=None)
        xsec = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0, turbulator=turb)
        xsec_tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0, turbulator=None)
        wing = SimpleNamespace(x_secs=[xsec, xsec_tip], surface_type="main_wing")
        aircraft = self._make_aircraft([wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        # positions are None → not returned
        assert xtr_root is None
        assert xtr_tip is None

    def test_no_wings_attribute_returns_none(self):
        """Aircraft without wings attribute → graceful (None, None, False)."""
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        aircraft = SimpleNamespace()  # no wings attr
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)
        assert xtr_root is None
        assert enabled is False


# ---------------------------------------------------------------------------
# Tests: apply_turbulator_delta_to_cd0 — additional branch coverage
# ---------------------------------------------------------------------------


class TestApplyTurbulatorDeltaToCd0Additional:
    """Additional branches in apply_turbulator_delta_to_cd0 not in test_turbulator_cd0_integration."""

    def test_s_ref_zero_returns_raw_cd0(self):
        """s_ref <= 0 → no sections can have valid area → raw_cd0 unchanged."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0
        from app.services.turbulator_optimizer_service import WingSectionData

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        raw_cd0 = 0.025
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=0.4,
            xtr_tip=0.6,
            s_ref=0.0,  # zero → compute_delta_cd0_from_turbulator_position returns 0
        )
        # delta_cd0 = 0 → adjusted = raw_cd0 + 0 = raw_cd0
        assert result == pytest.approx(raw_cd0, abs=1e-9)

    def test_exception_in_compute_delta_returns_raw_cd0(self, monkeypatch):
        """When compute_delta_cd0_from_turbulator_position raises, raw_cd0 returned."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0
        from app.services.turbulator_optimizer_service import WingSectionData

        def _explode(*a, **kw):
            raise RuntimeError("NeuralFoil catastrophic failure")

        monkeypatch.setattr(
            "app.services.turbulator_optimizer_service.compute_delta_cd0_from_turbulator_position",
            _explode,
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        raw_cd0 = 0.025
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=0.4,
            xtr_tip=0.6,
            s_ref=0.4,
        )
        assert result == pytest.approx(raw_cd0, abs=1e-9)

    def test_warnings_are_logged_not_raised(self, monkeypatch, caplog):
        """Warnings from compute_delta_cd0_from_turbulator_position are logged."""
        import logging

        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0
        from app.services.turbulator_optimizer_service import WingSectionData

        def _with_warnings(*a, **kw):
            return -0.002, ["Section y=0.1m: low confidence result"]

        monkeypatch.setattr(
            "app.services.turbulator_optimizer_service.compute_delta_cd0_from_turbulator_position",
            _with_warnings,
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        raw_cd0 = 0.025
        with caplog.at_level(logging.WARNING):
            result = apply_turbulator_delta_to_cd0(
                raw_cd0=raw_cd0,
                wing_sections=sections,
                xtr_root=0.4,
                xtr_tip=0.6,
                s_ref=0.4,
            )
        # The warning should have been logged
        assert any("low confidence" in rec.message.lower() or "turbulator" in rec.message.lower()
                   for rec in caplog.records)
        # Result should be adjusted
        assert result == pytest.approx(raw_cd0 - 0.002, abs=1e-9)

    def test_negative_adjusted_cd0_clamped_to_raw(self, monkeypatch):
        """A pathological ΔCD0 that would make cd0 ≤ 0 is clamped to raw_cd0."""
        from app.services.assumption_compute_service import apply_turbulator_delta_to_cd0
        from app.services.turbulator_optimizer_service import WingSectionData

        def _huge_negative(*a, **kw):
            return -999.0, []  # would make adjusted = raw - 999 → negative

        monkeypatch.setattr(
            "app.services.turbulator_optimizer_service.compute_delta_cd0_from_turbulator_position",
            _huge_negative,
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        raw_cd0 = 0.025
        result = apply_turbulator_delta_to_cd0(
            raw_cd0=raw_cd0,
            wing_sections=sections,
            xtr_root=0.4,
            xtr_tip=0.6,
            s_ref=0.4,
        )
        assert result == pytest.approx(raw_cd0, abs=1e-9)
        assert result > 0.0
