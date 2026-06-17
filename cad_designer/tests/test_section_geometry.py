"""Tests for the cad_designer SectionGeometry primitive (gh-1020).

Two tiers:

* **fast** — pure helper math (y/span -> segment mapping, outline -> top/bottom
  sampling) that does NOT build any CAD. These run on the CI fast tier (no
  cadquery) and protect the coverage gate.
* **slow / requires_cadquery** — build the real lofted solid and slice it.
  Asserts the built geometry matches the airfoil (root thickness ~= t/c * chord),
  monotonic taper, and that twist/dihedral move the section as expected.
"""

from __future__ import annotations

import numpy as np
import pytest

from cad_designer.airplane.geometry.section_geometry import (
    SectionGeometry,
    SectionGeometryUnavailableError,
    SectionPoint,
    _outline_to_top_bottom,
    _y_span_to_segment,
)
from cad_designer.aerosandbox.wing_roundtrip_cases import (
    configurator_wing,
    single_segment_flat,
    single_segment_with_dihedral,
    single_segment_with_twist,
    single_segment_with_twist_and_dihedral,
)


# ---------------------------------------------------------------------------
# Fast: pure y/span -> segment mapping
# ---------------------------------------------------------------------------


class TestYSpanToSegment:
    def test_single_segment_root(self):
        idx, rel = _y_span_to_segment(0.0, [500.0])
        assert idx == 0
        assert rel == pytest.approx(0.0)

    def test_single_segment_tip(self):
        idx, rel = _y_span_to_segment(1.0, [500.0])
        assert idx == 0
        assert rel == pytest.approx(1.0)

    def test_single_segment_mid(self):
        idx, rel = _y_span_to_segment(0.5, [500.0])
        assert idx == 0
        assert rel == pytest.approx(0.5)

    def test_two_segments_boundary(self):
        # equal-length segments: y_span=0.5 is the seam, resolves to end of seg 0
        idx, rel = _y_span_to_segment(0.5, [500.0, 500.0])
        assert idx == 0
        assert rel == pytest.approx(1.0)

    def test_two_segments_into_second(self):
        idx, rel = _y_span_to_segment(0.75, [500.0, 500.0])
        assert idx == 1
        assert rel == pytest.approx(0.5)

    def test_unequal_segments(self):
        # lengths 300 + 700 = 1000; y_span 0.5 -> 500mm -> seg 1 at (500-300)/700
        idx, rel = _y_span_to_segment(0.5, [300.0, 700.0])
        assert idx == 1
        assert rel == pytest.approx(200.0 / 700.0)

    def test_clamps_below_zero(self):
        idx, rel = _y_span_to_segment(-0.1, [500.0])
        assert idx == 0
        assert rel == pytest.approx(0.0)

    def test_clamps_above_one(self):
        idx, rel = _y_span_to_segment(1.5, [500.0, 500.0])
        assert idx == 1
        assert rel == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Fast: outline -> top/bottom sampling
# ---------------------------------------------------------------------------


class TestOutlineToTopBottom:
    def _diamond_outline(self):
        """A symmetric diamond cross-section in the section's (chord_u, z) plane.

        chord runs 0..100, top/bottom peak at chord 50: top +20, bottom -20.
        Returns a list of (chord_u, z) polyline points around the loop.
        """
        return [
            (0.0, 0.0),
            (50.0, 20.0),
            (100.0, 0.0),
            (50.0, -20.0),
            (0.0, 0.0),
        ]

    def test_top_bottom_at_mid(self):
        outline = self._diamond_outline()
        top, bottom = _outline_to_top_bottom(outline, x_c=0.5, chord_len=100.0)
        assert top == pytest.approx(20.0, abs=1e-6)
        assert bottom == pytest.approx(-20.0, abs=1e-6)

    def test_thickness_zero_at_le(self):
        outline = self._diamond_outline()
        top, bottom = _outline_to_top_bottom(outline, x_c=0.0, chord_len=100.0)
        assert top == pytest.approx(0.0, abs=1e-6)
        assert bottom == pytest.approx(0.0, abs=1e-6)

    def test_quarter_chord(self):
        outline = self._diamond_outline()
        top, bottom = _outline_to_top_bottom(outline, x_c=0.25, chord_len=100.0)
        # linear ramp from 0 (chord 0) to 20 (chord 50): at chord 25 -> 10
        assert top == pytest.approx(10.0, abs=1e-6)
        assert bottom == pytest.approx(-10.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Slow / requires_cadquery: real build + slice
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_cadquery
class TestSectionGeometryRealBuild:
    def test_flat_root_thickness_matches_airfoil(self):
        """NACA0010 (t/c=0.10), chord 200mm -> max thickness ~= 20mm."""
        sg = SectionGeometry(single_segment_flat())
        pt = sg.at_max_thickness(0.05)  # near root
        assert pt.thickness == pytest.approx(20.0, rel=0.12)
        # symmetric airfoil, no dihedral/twist -> centre near z=0
        assert pt.center_z == pytest.approx(0.0, abs=2.0)

    def test_flat_thickness_constant_along_span(self):
        sg = SectionGeometry(single_segment_flat())
        root = sg.at_max_thickness(0.1)
        tip = sg.at_max_thickness(0.9)
        # untapered -> thickness roughly constant
        assert tip.thickness == pytest.approx(root.thickness, rel=0.12)

    def test_taper_reduces_thickness(self):
        """twist+dihedral case tapers 200 -> 150 chord; tip thinner than root."""
        sg = SectionGeometry(single_segment_with_twist_and_dihedral())
        root = sg.at_max_thickness(0.05)
        tip = sg.at_max_thickness(0.95)
        assert tip.thickness < root.thickness

    def test_dihedral_lifts_center_z(self):
        """+5 deg dihedral -> tip section centre is raised vs root."""
        sg = SectionGeometry(single_segment_with_dihedral())
        root = sg.at_max_thickness(0.05)
        tip = sg.at_max_thickness(0.95)
        assert tip.center_z > root.center_z + 5.0

    def test_at_returns_section_point(self):
        sg = SectionGeometry(single_segment_flat())
        pt = sg.at(0.5, 0.3)
        assert isinstance(pt, SectionPoint)
        assert pt.thickness > 0
        assert pt.top_z > pt.bottom_z
        assert pt.center_z == pytest.approx((pt.top_z + pt.bottom_z) / 2.0)

    def test_sample_slices_each_y_once(self):
        sg = SectionGeometry(single_segment_flat())
        pts = sg.sample([0.25, 0.75], [0.2, 0.3, 0.4])
        assert len(pts) == 6  # 2 y * 3 x
        for p in pts:
            assert p.thickness > 0

    def test_per_segment_grid(self):
        sg = SectionGeometry(configurator_wing())
        grid = sg.per_segment(n_span=3, n_chord=4)
        assert set(grid.keys()) == {0, 1, 2}
        for pts in grid.values():
            assert len(pts) == 12  # 3 * 4

    def test_twist_tilts_section(self):
        """-10 deg tip twist tilts the section: top_z at LE differs from TE."""
        sg = SectionGeometry(single_segment_with_twist())
        le = sg.at(0.95, 0.05)
        te = sg.at(0.95, 0.95)
        # with washout the LE rises relative to the TE (or vice-versa) -> centres differ
        assert abs(le.center_z - te.center_z) > 1.0


# ---------------------------------------------------------------------------
# Fast: platform guard (cadquery unavailable)
# ---------------------------------------------------------------------------


class TestPlatformGuard:
    def test_unavailable_raises_typed_error(self, monkeypatch):
        import cad_designer.airplane.geometry.section_geometry as mod

        monkeypatch.setattr(mod, "_HAS_CADQUERY", False)
        with pytest.raises(SectionGeometryUnavailableError):
            SectionGeometry(single_segment_flat())
