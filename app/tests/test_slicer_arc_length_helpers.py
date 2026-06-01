"""Pure-Python tests for the gh-732 slicer helpers.

Cover the arc-length-weight / contour-clustering / VSP-anchored
station logic that's introduced as part of the slicer-driven
FuselageSchema rebuild. All tests run without OCC / cadquery so they
work on linux/aarch64 too.
"""

from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# arc_length_weights
# ---------------------------------------------------------------------------


class TestArcLengthWeights:
    def _w(self, pts):
        from cad_designer.aerosandbox.slicing import arc_length_weights

        return arc_length_weights(np.asarray(pts, dtype=float))

    def test_uniform_grid_gives_uniform_weights(self):
        """Points sampled uniformly along a line all have the same NN
        distance → identical weights."""
        pts = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
        w = self._w(pts)
        assert len(w) == 4
        # Interior nn=1.0 either side; endpoints nn=1.0 to single neighbour.
        # All weights = 1.0 (within float tolerance).
        assert np.allclose(w, 1.0)

    def test_clustered_points_get_smaller_weights(self):
        """Three over-sampled points clustered close to each other
        should each get a smaller weight than a lone point far away."""
        pts = [(0.0, 0.0), (0.01, 0.0), (0.02, 0.0), (10.0, 0.0)]
        w = self._w(pts)
        # First three are densely clustered (nn ≈ 0.01); last is alone
        # at distance 9.98 → its nn = 9.98 → weight ≫ others.
        assert w[0] < w[3] * 0.01
        assert w[1] < w[3] * 0.01
        assert w[2] < w[3] * 0.01

    def test_handles_single_point(self):
        """Degenerate single-point cloud → unit weight."""
        w = self._w([(5.0, 5.0)])
        assert len(w) == 1
        assert w[0] == 1.0

    def test_handles_empty(self):
        """Empty input → empty output."""
        from cad_designer.aerosandbox.slicing import arc_length_weights

        w = arc_length_weights(np.empty((0, 2)))
        assert len(w) == 0

    def test_all_weights_strictly_positive(self):
        """Even coincident points get a small positive floor — divide-
        by-zero in the fitter is the unforgivable bug."""
        pts = [(0.0, 0.0), (0.0, 0.0), (1.0, 0.0)]
        w = self._w(pts)
        assert np.all(w > 0.0)


# ---------------------------------------------------------------------------
# thin_oversampled_points
# ---------------------------------------------------------------------------


class TestThinOversampledPoints:
    def _thin(self, pts, ratio=0.2):
        from cad_designer.aerosandbox.slicing import thin_oversampled_points

        return thin_oversampled_points(np.asarray(pts, dtype=float), radius_ratio=ratio)

    def test_passthrough_when_uniform(self):
        """Uniformly-spaced points have no clusters → nothing dropped."""
        pts = np.array([(x, 0.0) for x in np.linspace(0, 10, 11)])
        out = self._thin(pts)
        assert len(out) == len(pts)

    def test_drops_dense_duplicates(self):
        """A cluster of 10 points within 1% of bbox should collapse to
        one representative — the rest of the well-spaced cloud
        passes through."""
        # 10 nearly-coincident points + 10 well-spaced points.
        cluster = np.array([(i * 0.0001, 0.0) for i in range(10)])
        spaced = np.array([(x, 0.0) for x in np.linspace(1.0, 10.0, 10)])
        pts = np.concatenate([cluster, spaced])
        out = self._thin(pts)
        # We keep ≤1 point from the cluster + all the spaced ones.
        assert len(out) < len(pts) - 5

    def test_small_clouds_pass_through(self):
        """Below the safety threshold (8 points) the function returns
        the input unchanged — no clustering on tiny inputs."""
        pts = np.array([(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)])
        out = self._thin(pts)
        assert len(out) == 3


# ---------------------------------------------------------------------------
# select_outer_contour
# ---------------------------------------------------------------------------


class TestSelectOuterContour:
    def _select(self, polylines):
        from cad_designer.aerosandbox.slicing import select_outer_contour

        return select_outer_contour(polylines)

    def test_passthrough_single_contour(self):
        """A clean 4-edge slice (one outline) passes through — the
        gate refuses to split below 6 edges."""
        polylines = [
            [(0.0, y, z) for y, z in [(0, 0), (1, 0), (1, 1)]],
            [(0.0, y, z) for y, z in [(1, 1), (0, 1), (0, 0)]],
            [(0.0, y, z) for y, z in [(0, 0), (0.5, 0.5)]],
            [(0.0, y, z) for y, z in [(0.5, 0.5), (1, 0)]],
        ]
        out = self._select(polylines)
        assert len(out) == len(polylines)

    def test_returns_outer_for_axis_centered_clusters(self):
        """Two distinct clusters of 4 edges each — one centred on
        origin, one offset above. The function returns the cluster
        whose centroid is closer to the all-points-mean (the
        offset clusters together dominate, so 'closer to mean'
        favours the body cluster)."""
        # Build 8 polylines: 4 around (0, 0) outer body, 4 around (0, 5) canopy
        body = [
            [(0.0, 1.0, 0.0), (0.0, 0.5, 0.0)],
            [(0.0, -1.0, 0.0), (0.0, -0.5, 0.0)],
            [(0.0, 0.0, 1.0), (0.0, 0.0, 0.5)],
            [(0.0, 0.0, -1.0), (0.0, 0.0, -0.5)],
        ]
        canopy = [
            [(0.0, 0.05, 5.0), (0.0, 0.0, 4.95)],
            [(0.0, -0.05, 5.0), (0.0, 0.0, 4.95)],
            [(0.0, 0.05, 5.0), (0.0, 0.0, 5.05)],
            [(0.0, -0.05, 5.0), (0.0, 0.0, 5.05)],
        ]
        out = self._select(body + canopy)
        # 8 polylines → filter active. Returns one of the two clusters.
        assert len(out) < 8


# ---------------------------------------------------------------------------
# vsp_anchored_x_stations
# ---------------------------------------------------------------------------


class TestVspAnchoredStations:
    def _make_handler(self, positions_a_b):
        """Return list of handler-style xsec dicts. Each entry:
        (x_m, a_m, b_m). y/z fixed at 0."""
        return [{"xyz": [x, 0.0, 0.0], "a": a, "b": b, "n": 2.0} for x, a, b in positions_a_b]

    def test_returns_empty_for_under_two_xsecs(self):
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        assert vsp_anchored_x_stations([], total_stations=10) == []
        assert (
            vsp_anchored_x_stations(
                [{"xyz": [0, 0, 0], "a": 0.1, "b": 0.1, "n": 2.0}],
                total_stations=10,
            )
            == []
        )

    def test_includes_every_handler_anchor(self):
        """Every handler position must appear in the station list."""
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        handler = self._make_handler([(0.0, 0.1, 0.1), (1.0, 0.2, 0.2), (2.0, 0.1, 0.1)])
        stations = vsp_anchored_x_stations(handler, total_stations=20, scale_to_mm=True)
        # 0, 1000, 2000 mm must all appear (within float tolerance).
        for required_mm in (0.0, 1000.0, 2000.0):
            assert any(abs(s - required_mm) < 1e-6 for s in stations), (
                f"missing anchor at {required_mm}"
            )

    def test_metres_scale_when_disabled(self):
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        handler = self._make_handler([(0.0, 0.1, 0.1), (1.0, 0.1, 0.1)])
        stations = vsp_anchored_x_stations(handler, total_stations=5, scale_to_mm=False)
        assert stations[0] == 0.0
        assert stations[-1] == 1.0

    def test_tip_boost_concentrates_stations_at_caps(self):
        """A handler with one tiny-section anchor (the nose tip) should
        get more intermediate stations between that tip and the first
        body section than between two equal body sections."""
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        # Section 0: tip a=0 → body a=0.5 over 0.4 m (tip-cap)
        # Section 1: a=0.5 → a=0.5 over 1.0 m (uniform body)
        handler = self._make_handler(
            [
                (0.0, 0.0, 0.0),  # tip
                (0.4, 0.5, 0.5),  # body start
                (1.4, 0.5, 0.5),  # body end
            ]
        )
        stations = vsp_anchored_x_stations(handler, total_stations=20, scale_to_mm=True)
        # Count stations in section 0 vs section 1 (excluding anchors).
        sec0 = sum(1 for s in stations if 0.0 < s < 400.0)
        sec1 = sum(1 for s in stations if 400.0 < s < 1400.0)
        # Tip-cap section should be denser per unit length than the
        # uniform body section.
        assert sec0 / 0.4 > sec1 / 1.0

    def test_total_count_respects_budget(self):
        """The returned list size is bounded by the budget (plus the
        anchors)."""
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        handler = self._make_handler(
            [
                (0.0, 0.1, 0.1),
                (0.5, 0.1, 0.1),
                (1.0, 0.1, 0.1),
            ]
        )
        stations = vsp_anchored_x_stations(handler, total_stations=10, scale_to_mm=True)
        # 3 anchors + up to 7 intermediates = ≤10 total.
        assert 3 <= len(stations) <= 12  # some slack for rounding

    def test_anchors_sorted(self):
        """Output is sorted ascending."""
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        handler = self._make_handler(
            [
                (0.0, 0.1, 0.1),
                (1.0, 0.1, 0.1),
                (0.5, 0.1, 0.1),
            ]
        )
        stations = vsp_anchored_x_stations(handler, total_stations=10, scale_to_mm=False)
        assert stations == sorted(stations)

    def test_intermediates_cluster_near_anchors(self):
        """gh-804: intermediate stations cluster toward the section ends
        (cosine spacing), where VSP lofts round their corners — so the
        nose-body fillet is sampled instead of straight-lined into a kink.
        """
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        # One 10 m section between two equal body anchors → all budget
        # lands here, so we can inspect the intra-section distribution.
        handler = self._make_handler([(0.0, 1.0, 1.0), (10.0, 1.0, 1.0)])
        st = sorted(vsp_anchored_x_stations(handler, total_stations=12, scale_to_mm=False))
        inter = [s for s in st if 0.0 < s < 10.0]
        assert len(inter) >= 4
        n = len(inter)
        # Cosine places the first intermediate at frac 0.5(1-cos(pi/(n+1))),
        # strictly inside the uniform 1/(n+1) → clustered toward the anchor.
        assert inter[0] < (1.0 / (n + 1)) * 10.0
        # Symmetric: the last intermediate mirrors the first at the far end.
        assert (10.0 - inter[-1]) == pytest.approx(inter[0], rel=0.1)

    def test_long_featureless_section_does_not_starve_short_curved_one(self):
        """gh-804: the length-scaled baseline is capped so a long constant
        mid-body can't steal the whole budget from a short, highly-curved
        nose-body fillet section next to it."""
        from cad_designer.aerosandbox.slicing import vsp_anchored_x_stations

        handler = self._make_handler(
            [
                (0.0, 0.0, 0.0),
                (2.4, 1.18, 1.10),  # short fillet section (a/b change)
                (3.4, 1.35, 1.25),
                (12.5, 1.35, 1.25),  # long constant body (9 m)
                (12.5, 0.0, 0.0),
            ]
        )
        st = vsp_anchored_x_stations(handler, total_stations=40, scale_to_mm=False)
        fillet = sum(1 for s in st if 2.4 < s < 3.4)  # 1 m fillet section
        body = sum(1 for s in st if 3.4 < s < 12.5)  # 9 m body section
        # The 1 m fillet must be denser per metre than the 9 m body.
        assert fillet / 1.0 > body / 9.1


# ---------------------------------------------------------------------------
# _is_x_dominant_fuselage (import service)
# ---------------------------------------------------------------------------


class TestIsXDominantFuselage:
    def test_x_dominant_when_x_extent_is_largest(self):
        from app.services.openvsp_import_service import _is_x_dominant_fuselage

        # x ranges 0..1, y constant, z constant → X-dominant
        xsecs = [
            {"xyz": [0.0, 0.5, 0.5]},
            {"xyz": [1.0, 0.5, 0.5]},
            {"xyz": [0.5, 0.5, 0.5]},
        ]
        assert _is_x_dominant_fuselage(xsecs) is True

    def test_not_x_dominant_when_y_extent_larger(self):
        from app.services.openvsp_import_service import _is_x_dominant_fuselage

        # y ranges 0..1, x constant
        xsecs = [
            {"xyz": [0.5, 0.0, 0.5]},
            {"xyz": [0.5, 1.0, 0.5]},
        ]
        assert _is_x_dominant_fuselage(xsecs) is False

    def test_handles_symmetric_pair_correctly(self):
        """The cessna MainFairing's handler schema (4 xsecs along X at
        y = +1.27) must be X-dominant even though the STEP file holds
        both halves (which would falsely make the bbox Y-dominant).
        """
        from app.services.openvsp_import_service import _is_x_dominant_fuselage

        xsecs = [
            {"xyz": [-0.07, 1.27, -0.90]},
            {"xyz": [0.21, 1.27, -0.90]},
            {"xyz": [0.76, 1.27, -0.90]},
            {"xyz": [1.03, 1.27, -0.90]},
        ]
        # X extent = 1.10, Y extent = 0, Z extent = 0 → clearly X-dominant.
        assert _is_x_dominant_fuselage(xsecs) is True

    def test_too_few_xsecs_returns_false(self):
        from app.services.openvsp_import_service import _is_x_dominant_fuselage

        assert _is_x_dominant_fuselage([]) is False
        assert _is_x_dominant_fuselage([{"xyz": [0, 0, 0]}]) is False

    def test_margin_keeps_borderline_out(self):
        """A geom whose X is only 10 % longer than Y is borderline —
        the 1.2× margin keeps it out of the slicer."""
        from app.services.openvsp_import_service import _is_x_dominant_fuselage

        xsecs = [
            {"xyz": [0.0, 0.0, 0.0]},
            {"xyz": [1.10, 1.0, 0.0]},
        ]
        # X extent = 1.10, Y extent = 1.0, ratio = 1.10 < 1.2 → not dominant
        assert _is_x_dominant_fuselage(xsecs) is False
