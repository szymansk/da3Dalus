"""gh-1022: fast-tier tests for the spar-sizing thickness wire-in.

All tests run on the CI fast tier (no cadquery, no aerosandbox). The
``SectionGeometry`` boundary is mocked so synthetic ``SectionPoint``s with known
thickness flow through ``section_thickness`` → ``_get_tc_by_y_for_surface`` →
``compute_spar_sizing``. We assert:

  * real built thickness replaces the blanket 0.12 fallback (outer_mm / tc_ratio
    reflect the queried thickness, center_z_mm is surfaced);
  * the documented 0.12 fallback STILL fires when the geometry is unavailable
    (SectionGeometryUnavailableError) or a station yields thickness ≤ 0;
  * the y(m) → y_span(0..1) mapping uses the wing half-span.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest


@dataclass
class _FakePoint:
    """Stand-in for cad_designer SectionPoint (mm, wing-local frame)."""

    y_span: float
    x_c: float
    thickness: float
    top_z: float
    bottom_z: float
    center_z: float


class _FakeGeometry:
    """Mock SectionGeometry: thickness/center_z are deterministic in y_span.

    half_span = 2000 mm (two 1000 mm segments). Thickness tapers linearly from
    root (200 mm) to tip (50 mm); center_z rises with span (dihedral proxy).
    Records the y_span values queried so the mapping can be asserted.
    """

    def __init__(self) -> None:
        self._segment_lengths = [1000.0, 1000.0]  # half-span 2000 mm
        self.queried_y_spans: list[float] = []

    def at_max_thickness(self, y_span: float) -> _FakePoint:
        self.queried_y_spans.append(y_span)
        thickness = 200.0 - 150.0 * y_span  # 200 mm @ root → 50 mm @ tip
        center_z = 100.0 * y_span  # rises outboard
        return _FakePoint(
            y_span=y_span,
            x_c=0.3,
            thickness=thickness,
            top_z=center_z + thickness / 2.0,
            bottom_z=center_z - thickness / 2.0,
            center_z=center_z,
        )


def _make_material_specs() -> dict:
    return {"density_kg_m3": 1600.0, "allowable_bending_stress_mpa": 500.0}


def _patch_section_geometry(monkeypatch, geometry):
    """Patch the SectionGeometry build so no real CAD runs on the fast tier."""
    import app.services.section_thickness as st

    monkeypatch.setattr(st, "_build_section_geometry", lambda *a, **k: geometry)


# ---------------------------------------------------------------------------
# section_thickness.build_thickness_maps_for_surface
# ---------------------------------------------------------------------------


class TestBuildThicknessMaps:
    def test_real_thickness_and_center_z(self, monkeypatch):
        from app.services.section_thickness import build_thickness_maps_for_surface

        geo = _FakeGeometry()
        _patch_section_geometry(monkeypatch, geo)

        # Stations in metres; root=0, tip=2.0 (half-span 2.0 m)
        thickness_by_y, center_z_by_y = build_thickness_maps_for_surface(
            db=object(),
            aeroplane_id=1,
            surface_name="main_wing",
            station_ys_m=[2.0, 1.0, 0.0],
        )

        # y_span mapping: y_m / half_span_m (2.0) → 1.0, 0.5, 0.0
        assert geo.queried_y_spans == pytest.approx([1.0, 0.5, 0.0])
        # Thickness from the synthetic taper
        assert thickness_by_y[0.0] == pytest.approx(200.0)
        assert thickness_by_y[1.0] == pytest.approx(125.0)
        assert thickness_by_y[2.0] == pytest.approx(50.0)
        # Root deeper than tip
        assert thickness_by_y[0.0] > thickness_by_y[2.0]
        # center_z surfaced
        assert center_z_by_y[0.0] == pytest.approx(0.0)
        assert center_z_by_y[2.0] == pytest.approx(100.0)

    def test_empty_stations_returns_empty(self):
        from app.services.section_thickness import build_thickness_maps_for_surface

        tc, cz = build_thickness_maps_for_surface(
            db=object(), aeroplane_id=1, surface_name="w", station_ys_m=[]
        )
        assert tc == {}
        assert cz == {}

    def test_unavailable_geometry_returns_empty(self, monkeypatch):
        from app.services.section_thickness import build_thickness_maps_for_surface

        _patch_section_geometry(monkeypatch, None)  # build failed/unavailable
        tc, cz = build_thickness_maps_for_surface(
            db=object(), aeroplane_id=1, surface_name="w", station_ys_m=[0.0, 1.0]
        )
        assert tc == {}
        assert cz == {}

    def test_degenerate_thickness_station_omitted(self, monkeypatch):
        """A station whose section has thickness ≤ 0 is dropped (→ fallback)."""
        from app.services.section_thickness import build_thickness_maps_for_surface

        class _ZeroAtTip(_FakeGeometry):
            def at_max_thickness(self, y_span: float) -> _FakePoint:
                pt = super().at_max_thickness(y_span)
                if y_span >= 0.99:  # tip → degenerate
                    return _FakePoint(y_span, 0.3, 0.0, 0.0, 0.0, 0.0)
                return pt

        _patch_section_geometry(monkeypatch, _ZeroAtTip())
        tc, cz = build_thickness_maps_for_surface(
            db=object(), aeroplane_id=1, surface_name="w", station_ys_m=[2.0, 0.0]
        )
        assert 2.0 not in tc  # degenerate tip dropped
        assert 0.0 in tc

    def test_zero_half_span_returns_empty(self, monkeypatch):
        from app.services.section_thickness import build_thickness_maps_for_surface

        geo = _FakeGeometry()
        geo._segment_lengths = [0.0, 0.0]
        _patch_section_geometry(monkeypatch, geo)
        tc, cz = build_thickness_maps_for_surface(
            db=object(), aeroplane_id=1, surface_name="w", station_ys_m=[0.0]
        )
        assert tc == {}
        assert cz == {}


# ---------------------------------------------------------------------------
# _build_section_geometry resolution / graceful degradation
# ---------------------------------------------------------------------------


class TestBuildSectionGeometryResolution:
    def test_aeroplane_not_found_returns_none(self):
        from app.services.section_thickness import _build_section_geometry

        db = SimpleNamespace(
            query=lambda *a, **k: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: None)
            )
        )
        assert _build_section_geometry(db, 99, "main_wing") is None

    def test_wing_not_found_returns_none(self):
        from app.services.section_thickness import _build_section_geometry

        aeroplane = SimpleNamespace(wings=[SimpleNamespace(name="other_wing")])
        db = SimpleNamespace(
            query=lambda *a, **k: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: aeroplane)
            )
        )
        assert _build_section_geometry(db, 1, "main_wing") is None

    def _db_with_wing(self, wing_name="main_wing"):
        aeroplane = SimpleNamespace(wings=[SimpleNamespace(name=wing_name)])
        return SimpleNamespace(
            query=lambda *a, **k: SimpleNamespace(
                filter=lambda *a, **k: SimpleNamespace(first=lambda: aeroplane)
            )
        )

    def test_conversion_failure_returns_none(self, monkeypatch):
        from app.services import section_thickness as st

        def _boom(*a, **k):
            raise ValueError("bad geometry")

        monkeypatch.setattr(
            "app.converters.model_schema_converters.wing_model_to_wing_config", _boom
        )
        assert st._build_section_geometry(self._db_with_wing(), 1, "main_wing") is None

    def test_section_geometry_unavailable_returns_none(self, monkeypatch):
        """cadquery-unavailable path: SectionGeometryUnavailableError → None."""
        from app.services import section_thickness as st
        from cad_designer.airplane.geometry.section_geometry import (
            SectionGeometryUnavailableError,
        )

        monkeypatch.setattr(
            "app.converters.model_schema_converters.wing_model_to_wing_config",
            lambda *a, **k: object(),
        )

        def _unavailable(*a, **k):
            raise SectionGeometryUnavailableError("cadquery missing")

        monkeypatch.setattr(
            "cad_designer.airplane.geometry.section_geometry.SectionGeometry", _unavailable
        )
        assert st._build_section_geometry(self._db_with_wing(), 1, "main_wing") is None

    def test_build_success_returns_geometry(self, monkeypatch):
        """Happy path resolution: returns the (stubbed) SectionGeometry instance."""
        from app.services import section_thickness as st

        sentinel = object()
        monkeypatch.setattr(
            "app.converters.model_schema_converters.wing_model_to_wing_config",
            lambda *a, **k: object(),
        )
        monkeypatch.setattr(
            "cad_designer.airplane.geometry.section_geometry.SectionGeometry",
            lambda *a, **k: sentinel,
        )
        assert st._build_section_geometry(self._db_with_wing(), 1, "main_wing") is sentinel


class TestHalfSpan:
    def test_no_segment_lengths_returns_zero(self):
        from app.services.section_thickness import _half_span_mm

        assert _half_span_mm(SimpleNamespace()) == 0.0
        assert _half_span_mm(SimpleNamespace(_segment_lengths=[])) == 0.0

    def test_sums_segment_lengths(self):
        from app.services.section_thickness import _half_span_mm

        assert _half_span_mm(SimpleNamespace(_segment_lengths=[100.0, 250.0])) == 350.0


# ---------------------------------------------------------------------------
# analysis_service._get_tc_by_y_for_surface — thickness → t/c conversion
# ---------------------------------------------------------------------------


class TestGetTcByYForSurface:
    def _surface(self):
        return SimpleNamespace(surface_name="main_wing")

    def test_thickness_converted_to_tc_against_station_chord(self, monkeypatch):
        import app.services.analysis_service as svc

        # Mock the geometry boundary: thickness_by_y / center_z_by_y in mm.
        monkeypatch.setattr(
            "app.services.section_thickness.build_thickness_maps_for_surface",
            lambda **k: ({0.0: 200.0, 1.0: 125.0}, {0.0: 0.0, 1.0: 50.0}),
        )

        stations = [
            {"y_m": 1.0, "chord_m": 0.5, "bending_moment_Nm": 100.0},  # chord 500 mm
            {"y_m": 0.0, "chord_m": 1.0, "bending_moment_Nm": 200.0},  # chord 1000 mm
        ]
        tc_by_y, center_z_by_y = svc._get_tc_by_y_for_surface(
            db=object(), aeroplane_id=1, surface=self._surface(), stations=stations
        )
        # t/c = thickness_mm / chord_mm
        assert tc_by_y[0.0] == pytest.approx(200.0 / 1000.0)  # 0.20
        assert tc_by_y[1.0] == pytest.approx(125.0 / 500.0)  # 0.25
        assert center_z_by_y[1.0] == pytest.approx(50.0)

    def test_empty_geometry_yields_empty_maps(self, monkeypatch):
        import app.services.analysis_service as svc

        monkeypatch.setattr(
            "app.services.section_thickness.build_thickness_maps_for_surface",
            lambda **k: ({}, {}),
        )
        stations = [{"y_m": 0.0, "chord_m": 1.0, "bending_moment_Nm": 100.0}]
        tc, cz = svc._get_tc_by_y_for_surface(
            db=object(), aeroplane_id=1, surface=self._surface(), stations=stations
        )
        assert tc == {}
        assert cz == {}

    def test_zero_chord_station_skipped(self, monkeypatch):
        import app.services.analysis_service as svc

        monkeypatch.setattr(
            "app.services.section_thickness.build_thickness_maps_for_surface",
            lambda **k: ({0.0: 200.0}, {0.0: 0.0}),
        )
        stations = [{"y_m": 0.0, "chord_m": 0.0, "bending_moment_Nm": 100.0}]
        tc, cz = svc._get_tc_by_y_for_surface(
            db=object(), aeroplane_id=1, surface=self._surface(), stations=stations
        )
        assert tc == {}  # chord 0 → skipped, fallback will fire


# ---------------------------------------------------------------------------
# End-to-end through compute_spar_sizing: real thickness vs 0.12 fallback
# ---------------------------------------------------------------------------


class TestWireInThroughComputeSparSizing:
    def test_real_thickness_replaces_fallback(self):
        """t/c from geometry → profile_thickness == built thickness, not 0.12·c."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rectangular", packing_factor=0.8)
        stations = [{"y_m": 0.0, "chord_m": 1.0, "bending_moment_Nm": 500.0}]
        # Built thickness 200 mm on a 1000 mm chord → t/c = 0.20 (≠ 0.12)
        tc_by_y = {0.0: 0.20}
        center_z_by_y = {0.0: 5.0}

        result = compute_spar_sizing(
            stations=stations,
            tc_by_y=tc_by_y,
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
            center_z_by_y=center_z_by_y,
        )
        s0 = result.stations[0]
        assert s0.tc_fallback is False
        assert s0.tc_ratio == pytest.approx(0.20)
        assert s0.profile_thickness_mm == pytest.approx(200.0)  # real built thickness
        assert s0.outer_mm == pytest.approx(200.0 * 0.8)  # thickness · packing
        assert s0.center_z_mm == pytest.approx(5.0)  # spar-placement ref surfaced
        assert result.tc_fallback_warning is None

    def test_fallback_still_fires_without_geometry(self):
        """No geometry → 0.12 fallback + warning preserved."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rectangular", packing_factor=0.8)
        stations = [{"y_m": 0.49, "chord_m": 1.0, "bending_moment_Nm": 500.0}]

        result = compute_spar_sizing(
            stations=stations,
            tc_by_y={},  # geometry unavailable
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
            center_z_by_y={},
        )
        s0 = result.stations[0]
        assert s0.tc_fallback is True
        assert s0.tc_ratio == pytest.approx(0.12)
        assert s0.center_z_mm is None
        assert result.tc_fallback_warning is not None
        assert "0.12" in result.tc_fallback_warning

    def test_root_deeper_than_tip_tracks_taper(self):
        """A tapered wing: root spar outer dim > tip spar outer dim."""
        from app.services.spar_sizing import compute_spar_sizing
        from app.schemas.spar_sizing import SparSizingParams

        params = SparSizingParams(material_id=1, shape="rectangular", packing_factor=0.8)
        stations = [
            {"y_m": 2.0, "chord_m": 0.4, "bending_moment_Nm": 50.0},  # tip
            {"y_m": 0.0, "chord_m": 1.0, "bending_moment_Nm": 500.0},  # root
        ]
        # Real built thickness: 50 mm at tip, 200 mm at root → t/c 0.125, 0.20
        tc_by_y = {2.0: 50.0 / 400.0, 0.0: 200.0 / 1000.0}

        result = compute_spar_sizing(
            stations=stations,
            tc_by_y=tc_by_y,
            material_specs=_make_material_specs(),
            material_name="CF",
            params=params,
            g_limit=3.0,
            g_limit_fallback=False,
            surface_name="main_wing",
        )
        tip, root = result.stations[0], result.stations[1]
        assert root.outer_mm > tip.outer_mm  # spar outer dim tracks the taper
        assert root.profile_thickness_mm == pytest.approx(200.0)
        assert tip.profile_thickness_mm == pytest.approx(50.0)
