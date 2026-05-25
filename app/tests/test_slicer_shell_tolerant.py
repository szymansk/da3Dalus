"""Tests for the gh-727 Shell-tolerant slicer helpers.

Covers ``extract_xz_profile``, ``adaptive_x_stations``, and
``slice_at_x`` — the three new public helpers introduced for the
OpenVSP-import pipeline. Solid-path quality tests remain in
``test_fuselage_slice_quality.py``.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

pytest.importorskip("cadquery")
pytest.importorskip("aerosandbox")

import cadquery as cq

from cad_designer.aerosandbox.slicing import (
    _curvature_density,
    _ensure_sliceable_shape,
    adaptive_x_stations,
    extract_xz_profile,
    slice_at_x,
)


# ---------------------------------------------------------------------------
# adaptive_x_stations — pure-Python logic, no OCC dependency
# ---------------------------------------------------------------------------


class TestAdaptiveXStations:
    def test_uniform_profile_gives_uniform_stations(self):
        # A flat-top, flat-bottom box has zero curvature → equidistant.
        top = [(x, 1.0) for x in np.linspace(0.0, 10.0, 21)]
        bot = [(x, -1.0) for x in np.linspace(0.0, 10.0, 21)]
        stations = adaptive_x_stations(top, bot, n_stations=11, curvature_weight=0.7)
        assert len(stations) == 11
        diffs = np.diff(stations)
        # All gaps roughly equal (within 5% of mean).
        assert (diffs.max() - diffs.min()) / diffs.mean() < 0.05

    def test_localised_bump_clusters_stations_there(self):
        # Top profile: flat on [0, 4], sharp bump at x=5, flat on [6, 10].
        top = []
        for x in np.linspace(0.0, 10.0, 101):
            z = 1.0 + 2.0 * math.exp(-((x - 5.0) ** 2) / 0.2)
            top.append((float(x), float(z)))
        bot = [(x, -1.0) for x in np.linspace(0.0, 10.0, 101)]
        stations = adaptive_x_stations(top, bot, n_stations=20, curvature_weight=0.9)
        # At least half the stations should land within ±2 of the bump.
        in_bump = sum(1 for s in stations if 3.0 < s < 7.0)
        assert in_bump >= 10

    def test_zero_curvature_weight_is_pure_uniform(self):
        top = []
        for x in np.linspace(0.0, 10.0, 101):
            z = 1.0 + 2.0 * math.exp(-((x - 5.0) ** 2) / 0.2)
            top.append((float(x), float(z)))
        bot = [(x, -1.0) for x in np.linspace(0.0, 10.0, 101)]
        stations = adaptive_x_stations(top, bot, n_stations=11, curvature_weight=0.0)
        diffs = np.diff(stations)
        # Uniform within 5%.
        assert (diffs.max() - diffs.min()) / diffs.mean() < 0.05

    def test_includes_x_bounds(self):
        top = [(x, 0.0) for x in np.linspace(0.0, 10.0, 21)]
        stations = adaptive_x_stations(top, [], n_stations=5)
        assert stations[0] == pytest.approx(0.0, abs=1e-9)
        assert stations[-1] == pytest.approx(10.0, abs=1e-9)

    def test_requires_minimum_stations(self):
        with pytest.raises(ValueError, match="n_stations"):
            adaptive_x_stations([(0, 0), (1, 0)], [], n_stations=1)

    def test_requires_at_least_one_outline(self):
        with pytest.raises(ValueError, match="outline"):
            adaptive_x_stations([], [], n_stations=5)

    def test_falls_back_to_uniform_with_no_curvature_samples(self):
        # Outline too short for curvature → silently uniform.
        stations = adaptive_x_stations([(0, 0), (10, 0)], [], n_stations=5)
        assert len(stations) == 5
        assert stations[0] == pytest.approx(0.0)
        assert stations[-1] == pytest.approx(10.0)
        diffs = np.diff(stations)
        assert (diffs.max() - diffs.min()) < 1e-6


# ---------------------------------------------------------------------------
# _curvature_density — pure numpy
# ---------------------------------------------------------------------------


class TestCurvatureDensity:
    def test_straight_line_has_zero_curvature(self):
        outline = [(float(x), 2.0 * float(x) + 1.0) for x in range(10)]
        xs, dz2 = _curvature_density(outline)
        assert len(dz2) == 8
        assert np.allclose(dz2, 0.0, atol=1e-9)

    def test_parabola_has_constant_curvature(self):
        # z = x²  → d²z/dx² = 2 everywhere
        outline = [(float(x), float(x) ** 2) for x in range(20)]
        _, dz2 = _curvature_density(outline)
        # All ≈ 2 within finite-difference noise.
        assert np.allclose(dz2, 2.0, atol=0.01)

    def test_too_short_returns_empty(self):
        xs, dz2 = _curvature_density([(0, 0), (1, 1)])
        assert len(xs) == 0
        assert len(dz2) == 0


# ---------------------------------------------------------------------------
# _ensure_sliceable_shape — Solid + Shell-only inputs
# ---------------------------------------------------------------------------


class TestEnsureSliceableShape:
    def test_returns_solid_when_solid_present(self):
        # A simple box has a Solid.
        wp = cq.Workplane("XY").box(10.0, 5.0, 2.0)
        shape = _ensure_sliceable_shape(wp)
        # Solid is non-empty.
        assert shape is not None

    def test_raises_on_empty_model(self):
        wp = cq.Workplane("XY")
        with pytest.raises(ValueError, match="neither solids nor faces"):
            _ensure_sliceable_shape(wp)


# ---------------------------------------------------------------------------
# slice_at_x + extract_xz_profile — synthetic Solid + Shell
# ---------------------------------------------------------------------------


class TestSliceAtX:
    @pytest.fixture
    def box_shape(self):
        # Box of size 10 × 4 × 2 centred at origin → x ∈ [-5, +5].
        wp = cq.Workplane("XY").box(10.0, 4.0, 2.0)
        return _ensure_sliceable_shape(wp)

    def test_box_section_has_outline_edges(self, box_shape):
        polylines = slice_at_x(box_shape, 0.0, points_per_edge=8)
        assert polylines
        # All points lie on the X = 0 plane (within float tolerance).
        for poly in polylines:
            for pt in poly:
                assert abs(pt[0]) < 1e-6

    def test_box_section_bounding_box_matches(self, box_shape):
        # At x=0 the box outline must span the full Y/Z dimensions.
        polylines = slice_at_x(box_shape, 0.0, points_per_edge=16)
        all_y = [pt[1] for poly in polylines for pt in poly]
        all_z = [pt[2] for poly in polylines for pt in poly]
        assert max(all_y) - min(all_y) == pytest.approx(4.0, abs=1e-3)
        assert max(all_z) - min(all_z) == pytest.approx(2.0, abs=1e-3)

    def test_points_per_edge_clamped(self, box_shape):
        # Even an absurd value (1 million) must still produce
        # bounded-size output. The clamp caps at 4096.
        polylines = slice_at_x(box_shape, 0.0, points_per_edge=10_000_000)
        for poly in polylines:
            assert len(poly) <= 4096


class TestExtractXzProfile:
    def test_box_profile_is_rectangle(self):
        wp = cq.Workplane("XY").box(10.0, 4.0, 2.0)
        shape = _ensure_sliceable_shape(wp)
        top, bot = extract_xz_profile(shape)
        assert top and bot
        # Top envelope is the +z edge, bottom is the -z edge.
        top_zs = [z for _, z in top]
        bot_zs = [z for _, z in bot]
        assert all(z == pytest.approx(1.0, abs=1e-2) for z in top_zs)
        assert all(z == pytest.approx(-1.0, abs=1e-2) for z in bot_zs)
        # Outlines span the full X range.
        all_x = [x for x, _ in top] + [x for x, _ in bot]
        assert min(all_x) == pytest.approx(-5.0, abs=0.5)
        assert max(all_x) == pytest.approx(5.0, abs=0.5)

    def test_outline_is_sorted_by_x(self):
        wp = cq.Workplane("XY").box(10.0, 4.0, 2.0)
        shape = _ensure_sliceable_shape(wp)
        top, bot = extract_xz_profile(shape)
        top_xs = [x for x, _ in top]
        bot_xs = [x for x, _ in bot]
        assert top_xs == sorted(top_xs)
        assert bot_xs == sorted(bot_xs)

    def test_degenerate_no_x_extent_returns_empty(self, monkeypatch):
        # Patch _section_outline_edges to return a single-point cloud.
        from cad_designer.aerosandbox import slicing as mod

        class _FakeEdge:
            def positionAt(self, _t):
                from types import SimpleNamespace
                return SimpleNamespace(x=0.0, y=0.0, z=0.0)

        monkeypatch.setattr(mod, "_section_outline_edges", lambda *a, **k: [_FakeEdge()])
        top, bot = extract_xz_profile(None)
        assert top == []
        assert bot == []
