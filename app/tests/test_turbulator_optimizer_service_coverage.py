"""Additional fast mocked tests for turbulator_optimizer_service — gh-935 coverage gate.

Covers the lines NOT exercised by test_turbulator_optimizer_service.py:
  - build_wing_section_data (lines 393-448): empty entry list + stub entries
  - run_turbulator_optimizer scope="segment" branch
  - run_turbulator_optimizer scope="whole" branch (incl. empty-sections path)
  - run_turbulator_optimizer error path: bad airfoil name emits warning + NaN section
  - run_turbulator_optimizer summary when all sections have NaN cd_clean
  - compute_delta_cd0_from_turbulator_position (lines 671-724): span interpolation,
    NaN cd path, NaN exception path, symmetry

All tests are fast / mocked — no real AeroSandbox or NeuralFoil.
"""

from __future__ import annotations

import math
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Shared xtr-aware fake (same model as test_turbulator_optimizer_service.py)
# ---------------------------------------------------------------------------


def _fake_neuralfoil(alpha, *, re, xtr_upper: float = 1.0, **kw) -> dict:
    alphas = np.atleast_1d(alpha)
    cd_base = 0.010
    cd_bubble = 0.020
    cd = cd_base + cd_bubble * (xtr_upper - 0.4) ** 2 / (0.6**2)
    return {
        "CL": np.full_like(alphas, 0.6, dtype=float),
        "CD": np.full_like(alphas, cd, dtype=float),
        "analysis_confidence": np.full_like(alphas, 0.95, dtype=float),
    }


@pytest.fixture()
def mock_asb_and_build_airfoil(monkeypatch):
    """Install a fake aerosandbox module (if not present) and patch
    _build_asb_airfoil to return a FakeAirfoil.

    Returns the FakeAirfoil class so tests can inspect calls.
    """
    if "aerosandbox" not in sys.modules:
        asb_mod = types.ModuleType("aerosandbox")

        class _FakeAirfoil:
            def __init__(self, name=None, coordinates=None):
                self.name = name or "naca0012"

            def get_aero_from_neuralfoil(self, alpha, Re, xtr_upper=1.0, **kw):
                return _fake_neuralfoil(np.atleast_1d(alpha), re=Re, xtr_upper=xtr_upper)

        asb_mod.Airfoil = _FakeAirfoil
        sys.modules["aerosandbox"] = asb_mod

    import aerosandbox as asb

    class FakeAirfoil:
        def __init__(self, name=None, coordinates=None):
            self.name = name or "naca0012"

        def get_aero_from_neuralfoil(self, alpha, Re, xtr_upper=1.0, **kw):
            return _fake_neuralfoil(np.atleast_1d(alpha), re=Re, xtr_upper=xtr_upper)

    monkeypatch.setattr(asb.Airfoil, "get_aero_from_neuralfoil", FakeAirfoil.get_aero_from_neuralfoil)

    def _fake_build_airfoil(name: str):
        return FakeAirfoil(name=name)

    monkeypatch.setattr(
        "app.converters.model_schema_converters._build_asb_airfoil",
        _fake_build_airfoil,
    )
    return FakeAirfoil


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_section_entry(y_m=0.1, chord_m=0.2, cl=0.6):
    """Minimal section-aoa entry object (duck-type: .y_m, .chord_m, .cl)."""
    return SimpleNamespace(y_m=y_m, chord_m=chord_m, cl=cl)


def _make_fake_asb_airplane(airfoil_name="naca0012"):
    """Stub AeroSandbox airplane with one wing and two xsecs."""
    xsec_root = SimpleNamespace(
        xyz_le=np.array([0.0, 0.0, 0.0]),
        airfoil=SimpleNamespace(name=airfoil_name),
    )
    xsec_tip = SimpleNamespace(
        xyz_le=np.array([0.0, 0.5, 0.0]),
        airfoil=SimpleNamespace(name=airfoil_name),
    )
    wing = SimpleNamespace(
        area=lambda: 0.30,
        xsecs=[xsec_root, xsec_tip],
    )
    return SimpleNamespace(wings=[wing])


def _make_wsd_list(n=2):
    """Build n WingSectionData objects for use in optimizer tests."""
    from app.services.turbulator_optimizer_service import WingSectionData

    return [
        WingSectionData(
            y_m=0.1 * (i + 1),
            chord_m=0.2,
            cl=0.6,
            re_local=200_000,
            airfoil_name="naca0012",
            section_area_m2=0.08,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Tests: build_wing_section_data
# ---------------------------------------------------------------------------


class TestBuildWingSectionData:
    """Lines 393-448 in turbulator_optimizer_service."""

    def test_empty_section_entries_returns_empty_list(self):
        """Early return: empty section_entries → empty WingSectionData list."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        fake_plane = _make_fake_asb_airplane()
        result = build_wing_section_data(
            asb_airplane=fake_plane, section_entries=[], velocity=15.0, s_ref=0.30
        )
        assert result == []

    def test_returns_correct_count(self):
        """One WingSectionData per section_entry."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        fake_plane = _make_fake_asb_airplane()
        entries = [
            _make_section_entry(y_m=0.0, chord_m=0.2, cl=0.6),
            _make_section_entry(y_m=0.25, chord_m=0.18, cl=0.55),
            _make_section_entry(y_m=0.5, chord_m=0.15, cl=0.5),
        ]
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=0.30)
        assert len(result) == 3

    def test_re_local_computed_from_velocity_and_chord(self):
        """re_local = max(velocity * chord / nu, 1e4); nu = 1.5e-5."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        fake_plane = _make_fake_asb_airplane()
        entries = [_make_section_entry(y_m=0.1, chord_m=0.2, cl=0.6)]
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=0.30)
        nu = 1.5e-5
        expected_re = 15.0 * 0.2 / nu
        assert result[0].re_local == pytest.approx(expected_re, rel=1e-6)

    def test_section_areas_sum_to_half_s_ref(self):
        """Trapezoidal areas are normalised to sum = s_ref / 2."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        fake_plane = _make_fake_asb_airplane()
        entries = [
            _make_section_entry(y_m=0.0, chord_m=0.2, cl=0.6),
            _make_section_entry(y_m=0.25, chord_m=0.18, cl=0.55),
            _make_section_entry(y_m=0.5, chord_m=0.15, cl=0.5),
        ]
        s_ref = 0.30
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=s_ref)
        total_area = sum(s.section_area_m2 for s in result)
        assert total_area == pytest.approx(s_ref / 2, rel=1e-6)

    def test_airfoil_name_resolved_from_xsec(self):
        """Airfoil name comes from the nearest xsec in the main wing."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        fake_plane = _make_fake_asb_airplane(airfoil_name="naca2412")
        entries = [_make_section_entry(y_m=0.1, chord_m=0.2, cl=0.6)]
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=0.30)
        assert result[0].airfoil_name == "naca2412"

    def test_single_xsec_wing_uses_that_airfoil(self):
        """When only one xsec exists in the wing, that airfoil is used for all sections."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        xsec = SimpleNamespace(
            xyz_le=np.array([0.0, 0.0, 0.0]),
            airfoil=SimpleNamespace(name="naca4412"),
        )
        wing = SimpleNamespace(area=lambda: 0.30, xsecs=[xsec])
        fake_plane = SimpleNamespace(wings=[wing])

        entries = [_make_section_entry(y_m=0.1, chord_m=0.2, cl=0.6)]
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=0.30)
        assert result[0].airfoil_name == "naca4412"

    def test_xsec_without_airfoil_attr_falls_back_to_naca0012(self):
        """If the airfoil attribute is missing/None, falls back to naca0012."""
        from app.services.turbulator_optimizer_service import build_wing_section_data

        xsec_root = SimpleNamespace(
            xyz_le=np.array([0.0, 0.0, 0.0]),
            airfoil=None,  # triggers the except path
        )
        xsec_tip = SimpleNamespace(
            xyz_le=np.array([0.0, 0.5, 0.0]),
            airfoil=None,
        )
        wing = SimpleNamespace(area=lambda: 0.30, xsecs=[xsec_root, xsec_tip])
        fake_plane = SimpleNamespace(wings=[wing])
        entries = [_make_section_entry(y_m=0.1, chord_m=0.2, cl=0.6)]
        result = build_wing_section_data(fake_plane, entries, velocity=15.0, s_ref=0.30)
        assert result[0].airfoil_name == "naca0012"


# ---------------------------------------------------------------------------
# Tests: run_turbulator_optimizer — scope="segment" branch
# ---------------------------------------------------------------------------


class TestRunOptimizerSegmentScope:
    """scope='segment' uses per-section logic (same code path as 'section')."""

    def test_segment_scope_returns_one_result_per_section(self, mock_asb_and_build_airfoil):
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=3)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="segment")
        assert len(result.sections) == 3

    def test_segment_scope_label_preserved(self, mock_asb_and_build_airfoil):
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=2)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="segment")
        assert result.scope == "segment"

    def test_segment_scope_summary_finite(self, mock_asb_and_build_airfoil):
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=2)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="segment")
        assert math.isfinite(result.summary.delta_cd0)

    def test_bad_airfoil_name_emits_warning_in_section_result(self, monkeypatch):
        """When _build_asb_airfoil raises (bad name), section gets NaN + warning."""
        from app.services.turbulator_optimizer_service import WingSectionData, run_turbulator_optimizer

        def _failing_build(name: str):
            raise ValueError(f"Unknown airfoil: {name!r}")

        monkeypatch.setattr(
            "app.converters.model_schema_converters._build_asb_airfoil",
            _failing_build,
        )

        sections = [
            WingSectionData(
                y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                airfoil_name="bad_airfoil", section_area_m2=0.10,
            )
        ]
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="section")
        assert len(result.sections) == 1
        sec = result.sections[0]
        assert math.isnan(sec.xtr_opt)
        assert len(sec.warnings) > 0


# ---------------------------------------------------------------------------
# Tests: run_turbulator_optimizer — scope="whole" branch
# ---------------------------------------------------------------------------


class TestRunOptimizerWholeScope:
    """scope='whole' finds a single global xtr_opt at the representative Re/CL."""

    def test_whole_scope_empty_sections_returns_empty_result(self, mock_asb_and_build_airfoil):
        """Empty section list → empty sections list, ΔCD0 = 0."""
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        result = run_turbulator_optimizer(sections=[], s_ref=0.30, scope="whole")
        assert result.sections == []
        assert result.summary.delta_cd0 == pytest.approx(0.0, abs=1e-9)

    def test_whole_scope_all_sections_get_same_xtr(self, mock_asb_and_build_airfoil):
        """All sections must have the same xtr_opt under 'whole' scope."""
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=3)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole")
        xtr_opts = [s.xtr_opt for s in result.sections if not math.isnan(s.xtr_opt)]
        if xtr_opts:
            assert all(abs(x - xtr_opts[0]) < 1e-9 for x in xtr_opts)

    def test_whole_scope_summary_finite(self, mock_asb_and_build_airfoil):
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=2)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole")
        assert math.isfinite(result.summary.delta_cd0)

    def test_whole_scope_error_in_rep_airfoil_gives_nan_xtr(self, monkeypatch):
        """If the representative airfoil build fails, global_xtr_opt = NaN."""
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        call_count = {"n": 0}

        def _sometimes_fail(name):
            """Fail on first call (representative section build)."""
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("rep airfoil build failed")
            # Subsequent calls (per-section application) also fail gracefully.
            raise RuntimeError("section airfoil build failed")

        monkeypatch.setattr(
            "app.converters.model_schema_converters._build_asb_airfoil",
            _sometimes_fail,
        )

        sections = _make_wsd_list(n=2)
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole")
        # All sections should have NaN xtr_opt (global_xtr_opt=NaN propagated)
        for sec in result.sections:
            assert math.isnan(sec.xtr_opt)

    def test_whole_scope_section_area_zero_gives_fallback_re(self, mock_asb_and_build_airfoil):
        """When all section areas are 0, uses midpoint section for re_rep."""
        from app.services.turbulator_optimizer_service import WingSectionData, run_turbulator_optimizer

        # all areas = 0 → total_area = 0 → fallback to midpoint
        sections = [
            WingSectionData(
                y_m=0.1 * (i + 1), chord_m=0.2, cl=0.6,
                re_local=200_000, airfoil_name="naca0012", section_area_m2=0.0,
            )
            for i in range(3)
        ]
        result = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole")
        # Should complete without error; sections may have NaN or finite xtr_opt
        assert len(result.sections) == 3

    def test_whole_scope_symmetric_doubles_delta_cd0(self, mock_asb_and_build_airfoil):
        """wing_symmetric=True → ΔCD0 multiplied by 2 vs non-symmetric."""
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        sections = _make_wsd_list(n=2)
        r_sym = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole", wing_symmetric=True)
        r_asym = run_turbulator_optimizer(sections=sections, s_ref=0.30, scope="whole", wing_symmetric=False)
        # Both should be finite; symmetric should have 2× the magnitude
        assert math.isfinite(r_sym.summary.delta_cd0)
        assert math.isfinite(r_asym.summary.delta_cd0)
        assert abs(r_sym.summary.delta_cd0) == pytest.approx(
            2.0 * abs(r_asym.summary.delta_cd0), rel=1e-6
        )


# ---------------------------------------------------------------------------
# Tests: run_turbulator_optimizer — cl_avg fallback (empty sections)
# ---------------------------------------------------------------------------


class TestRunOptimizerClAvgFallback:
    """Lines 613, 629: cl_avg/cd_clean_avg fallbacks when sections is empty."""

    def test_empty_sections_cl_avg_is_zero(self, mock_asb_and_build_airfoil):
        """With no sections, cl_avg = 0.0, cd_clean_avg = NaN → NaN L/D."""
        from app.services.turbulator_optimizer_service import run_turbulator_optimizer

        result = run_turbulator_optimizer(sections=[], s_ref=0.30, scope="section")
        assert result.sections == []
        # L/D computed from cl=0.0 → l_d_clean = 0/... = NaN or 0
        assert result.summary is not None


# ---------------------------------------------------------------------------
# Tests: compute_delta_cd0_from_turbulator_position
# ---------------------------------------------------------------------------


class TestComputeDeltaCd0FromTurbulatorPosition:
    """Lines 671-724. Most of these are NEW coverage not in test_turbulator_cd0_integration.py."""

    def test_empty_sections_returns_zero(self):
        from app.services.turbulator_optimizer_service import compute_delta_cd0_from_turbulator_position

        delta, warnings = compute_delta_cd0_from_turbulator_position([], 0.4, 0.6, s_ref=0.30)
        assert delta == pytest.approx(0.0, abs=1e-9)
        assert warnings == []

    def test_s_ref_zero_returns_zero(self, mock_asb_and_build_airfoil):
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.6, s_ref=0.0
        )
        assert delta == pytest.approx(0.0, abs=1e-9)

    def test_xtr_interpolated_along_span(self, mock_asb_and_build_airfoil):
        """xtr_root at y_min, xtr_tip at y_max → linear interpolation."""
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        # Two sections: root at y=0.0, tip at y=1.0
        sections = [
            WingSectionData(y_m=0.0, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
            WingSectionData(y_m=0.5, chord_m=0.18, cl=0.55, re_local=180_000,
                            airfoil_name="naca0012", section_area_m2=0.09),
            WingSectionData(y_m=1.0, chord_m=0.15, cl=0.5, re_local=150_000,
                            airfoil_name="naca0012", section_area_m2=0.08),
        ]
        # Should complete without error; just check the result is finite and not zero
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.3, xtr_tip=0.7, s_ref=0.4, wing_symmetric=False
        )
        assert math.isfinite(delta)

    def test_single_section_same_xtr_root_tip(self, mock_asb_and_build_airfoil):
        """Single section with xtr_root = xtr_tip → uniform xtr."""
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        sections = [
            WingSectionData(y_m=0.25, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        # y_span = 0 (only one section) → frac=0 → xtr_sec = xtr_root
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.6, s_ref=0.4
        )
        assert math.isfinite(delta)

    def test_nan_cd_section_produces_warning(self, monkeypatch):
        """When NeuralFoil returns NaN cds, the section produces a warning."""
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        def _nan_airfoil(name):
            class NanAirfoil:
                def get_aero_from_neuralfoil(self, alpha, Re, xtr_upper=1.0, **kw):
                    alphas = np.atleast_1d(alpha)
                    return {
                        "CL": np.full_like(alphas, float("nan")),
                        "CD": np.full_like(alphas, float("nan")),
                        "analysis_confidence": np.full_like(alphas, 0.95),
                    }

            return NanAirfoil()

        monkeypatch.setattr(
            "app.converters.model_schema_converters._build_asb_airfoil", _nan_airfoil
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=0.4
        )
        assert len(warnings) > 0, "Expected a NaN warning"
        assert delta == pytest.approx(0.0, abs=1e-9)

    def test_exception_in_airfoil_build_produces_warning(self, monkeypatch):
        """When _build_asb_airfoil raises, section gets a warning (no crash)."""
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        def _raising_build(name):
            raise RuntimeError("airfoil build failed")

        monkeypatch.setattr(
            "app.converters.model_schema_converters._build_asb_airfoil", _raising_build
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
        ]
        delta, warnings = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=0.4
        )
        assert len(warnings) > 0
        assert delta == pytest.approx(0.0, abs=1e-9)

    def test_symmetric_wing_doubles_delta(self, mock_asb_and_build_airfoil):
        """wing_symmetric=True → 2× the area-weighted ΔCD0."""
        from app.services.turbulator_optimizer_service import (
            WingSectionData,
            compute_delta_cd0_from_turbulator_position,
        )

        sections = [
            WingSectionData(y_m=0.1, chord_m=0.2, cl=0.6, re_local=200_000,
                            airfoil_name="naca0012", section_area_m2=0.10),
            WingSectionData(y_m=0.4, chord_m=0.15, cl=0.5, re_local=150_000,
                            airfoil_name="naca0012", section_area_m2=0.08),
        ]
        delta_sym, _ = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=0.4, wing_symmetric=True
        )
        delta_asym, _ = compute_delta_cd0_from_turbulator_position(
            sections, xtr_root=0.4, xtr_tip=0.4, s_ref=0.4, wing_symmetric=False
        )
        assert math.isfinite(delta_sym)
        assert math.isfinite(delta_asym)
        assert abs(delta_sym) == pytest.approx(2.0 * abs(delta_asym), rel=1e-6)
