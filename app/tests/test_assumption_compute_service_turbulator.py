"""Fast mocked tests for assumption_compute_service turbulator helpers — gh-935.

Covers the lines NOT exercised by test_assumption_compute_service.py:
  - _wing_orm_planform_area (lines 2171-2202)
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
# Tests: _wing_orm_planform_area
# ---------------------------------------------------------------------------


class TestWingOrmPlanformArea:
    """_wing_orm_planform_area(wing) — trapezoidal half-span area from ORM xsecs."""

    def _make_wing(self, xsecs):
        return SimpleNamespace(x_secs=xsecs)

    def test_no_xsecs_returns_zero(self):
        from app.services.assumption_compute_service import _wing_orm_planform_area

        wing = self._make_wing([])
        assert _wing_orm_planform_area(wing) == pytest.approx(0.0, abs=1e-9)

    def test_one_xsec_returns_zero(self):
        """Fewer than two xsecs → degenerate wing → 0.0."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        xsec = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        wing = self._make_wing([xsec])
        assert _wing_orm_planform_area(wing) == pytest.approx(0.0, abs=1e-9)

    def test_two_xsecs_rectangular_wing(self):
        """Two xsecs with chord=200mm spanning 500mm → area = 200*500 = 100_000 mm²."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        root = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=200.0)
        wing = self._make_wing([root, tip])
        area = _wing_orm_planform_area(wing)
        assert area == pytest.approx(100_000.0, rel=1e-6)

    def test_two_xsecs_tapered_wing(self):
        """Tapered wing: chord_root=200, chord_tip=100, span=500 → area = (200+100)/2*500."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        root = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0)
        wing = self._make_wing([root, tip])
        area = _wing_orm_planform_area(wing)
        expected = 0.5 * (200.0 + 100.0) * 500.0  # trapezoidal integration
        assert area == pytest.approx(expected, rel=1e-6)

    def test_xsecs_sorted_by_y(self):
        """xsecs unsorted by y should produce the same result as sorted."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0)
        root = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        # tip listed before root — function should sort internally
        wing = self._make_wing([tip, root])
        area = _wing_orm_planform_area(wing)
        expected = 0.5 * (200.0 + 100.0) * 500.0
        assert area == pytest.approx(expected, rel=1e-6)

    def test_xsec_with_none_xyz_le_is_skipped(self):
        """xsec with xyz_le=None should be skipped gracefully."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        good = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        bad_xy = SimpleNamespace(xyz_le=None, chord=200.0)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0)
        wing = self._make_wing([good, bad_xy, tip])
        # bad_xy skipped → only good + tip → trapezoidal
        area = _wing_orm_planform_area(wing)
        expected = 0.5 * (200.0 + 100.0) * 500.0
        assert area == pytest.approx(expected, rel=1e-6)

    def test_xsec_with_none_chord_is_skipped(self):
        """xsec with chord=None should be skipped gracefully."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        root = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0)
        no_chord = SimpleNamespace(xyz_le=[0.0, 250.0, 0.0], chord=None)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0)
        wing = self._make_wing([root, no_chord, tip])
        area = _wing_orm_planform_area(wing)
        expected = 0.5 * (200.0 + 100.0) * 500.0
        assert area == pytest.approx(expected, rel=1e-6)

    def test_no_x_secs_attribute_returns_zero(self):
        """Wing without x_secs attribute → graceful 0.0."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        wing = SimpleNamespace()  # no x_secs attr
        assert _wing_orm_planform_area(wing) == pytest.approx(0.0, abs=1e-9)

    def test_all_valid_xsecs_filtered_out_returns_zero(self):
        """When xyz_le/chord filtering leaves fewer than 2 valid pts → 0.0."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        # Both xsecs have None chord → filtered out → len(pts) < 2 → return 0
        root = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=None)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=None)
        wing = self._make_wing([root, tip])
        assert _wing_orm_planform_area(wing) == pytest.approx(0.0, abs=1e-9)

    def test_xyz_le_type_error_xsec_is_skipped(self):
        """An xyz_le that raises TypeError on indexing is skipped gracefully."""
        from app.services.assumption_compute_service import _wing_orm_planform_area

        class BadIndexable:
            def __getitem__(self, idx):
                raise TypeError("bad xyz_le type")

            def __len__(self):
                return 1

        # root with bad xyz_le; tip is valid — only one valid point → return 0
        root = SimpleNamespace(xyz_le=BadIndexable(), chord=200.0)
        tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0)
        wing = self._make_wing([root, tip])
        # root skipped (TypeError) → only tip in pts → len(pts)=1 < 2 → 0.0
        area = _wing_orm_planform_area(wing)
        assert area == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Tests: _extract_main_wing_turbulator_xtr
# ---------------------------------------------------------------------------


class TestExtractMainWingTurbulatorXtr:
    """_extract_main_wing_turbulator_xtr(aircraft) → (xtr_root, xtr_tip, enabled)."""

    def _make_aircraft(self, wings):
        return SimpleNamespace(wings=wings)

    def _make_wing_with_turbulator(
        self, chord=200.0, span=500.0, enabled=True, pos_root=0.4, pos_tip=0.6,
        with_turbulator=True,
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
        return SimpleNamespace(x_secs=[xsec, xsec_tip])

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

    def test_selects_largest_wing_by_planform_area(self):
        """Main wing is chosen by largest planform area (not xsec count)."""
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        # Large main wing with turbulator at 0.4/0.6
        main_wing = self._make_wing_with_turbulator(
            chord=300.0, span=800.0, enabled=True, pos_root=0.4, pos_tip=0.6
        )
        # Small tail wing also with a turbulator at different values
        tail_wing = self._make_wing_with_turbulator(
            chord=80.0, span=200.0, enabled=True, pos_root=0.7, pos_tip=0.8
        )
        aircraft = self._make_aircraft([main_wing, tail_wing])
        xtr_root, xtr_tip, enabled = _extract_main_wing_turbulator_xtr(aircraft)

        assert enabled is True
        # Should pick xtr from MAIN wing (larger area)
        assert xtr_root == pytest.approx(0.4, abs=1e-9)
        assert xtr_tip == pytest.approx(0.6, abs=1e-9)

    def test_turbulator_with_none_positions_returns_none(self):
        """Turbulator enabled but positions not set → (None, None, False) equivalent."""
        from app.services.assumption_compute_service import _extract_main_wing_turbulator_xtr

        turb = SimpleNamespace(enabled=True, position_root=None, position_tip=None)
        xsec = SimpleNamespace(xyz_le=[0.0, 0.0, 0.0], chord=200.0, turbulator=turb)
        xsec_tip = SimpleNamespace(xyz_le=[0.0, 500.0, 0.0], chord=100.0, turbulator=None)
        wing = SimpleNamespace(x_secs=[xsec, xsec_tip])
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
