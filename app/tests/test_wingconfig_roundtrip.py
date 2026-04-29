"""Roundtrip integrity tests: WingConfig → ASB → WingConfig.

Every wing save goes through this conversion path. If any parameter
is corrupted during the roundtrip, the analysis results will be wrong.
These tests ensure that the bridge between Construction (WingConfig/mm)
and Analysis (ASB/meters) is lossless.

Relates to GH #158.
"""

import os

import pytest

asb = pytest.importorskip("aerosandbox")
pytest.importorskip("cadquery")

from app.schemas.wing import Wing, Segment, Airfoil  # noqa: E402
from app.services.create_wing_configuration import create_wing_configuration  # noqa: E402
from app.converters.model_schema_converters import (  # noqa: E402
    wing_config_to_asb_wing_schema,
    asb_wing_schema_to_wing_config,
)

AIRFOIL = "naca0015"
AIRFOIL_ALT = "naca2412"


def _roundtrip(wing_data: Wing):
    """WingConfig schema → WingConfiguration → ASB schema → WingConfiguration."""
    wc = create_wing_configuration(wing_data)
    asb_schema = wing_config_to_asb_wing_schema(wc, "test", scale=0.001)
    wc2 = asb_wing_schema_to_wing_config(asb_schema, scale=1000.0)
    return wc, wc2


def _seg(
    root_airfoil=AIRFOIL, root_chord=200, root_incidence=0, root_dihedral=0,
    tip_airfoil=AIRFOIL, tip_chord=180, tip_incidence=0, tip_dihedral=0,
    length=100, sweep=0, interpolation_pts=101, tip_type=None,
    wing_segment_type=None, trailing_edge_device=None,
) -> Segment:
    return Segment(
        root_airfoil=Airfoil(
            airfoil=root_airfoil, chord=root_chord,
            dihedral_as_rotation_in_degrees=root_dihedral,
            incidence=root_incidence,
        ),
        tip_airfoil=Airfoil(
            airfoil=tip_airfoil, chord=tip_chord,
            dihedral_as_rotation_in_degrees=tip_dihedral,
            incidence=tip_incidence,
        ),
        length=length, sweep=sweep,
        number_interpolation_points=interpolation_pts,
        tip_type=tip_type,
        wing_segment_type=wing_segment_type,
        trailing_edge_device=trailing_edge_device,
    )


def _wing(*segments: Segment) -> Wing:
    return Wing(nose_pnt=[0, 0, 0], symmetric=True, segments=list(segments))


def _assert_airfoil_match(
    original, roundtripped, label,
    tol_chord=0.05, tol_angle=0.01, is_terminal_tip=False,
):
    """Assert that airfoil parameters survive the roundtrip within tolerance.

    Terminal tip dihedral is inherently lossy: the ASB model stores only
    xyz_le positions, and the last cross-section has no successor segment
    to derive a dihedral direction from. WingConfiguration.from_asb sets
    cum_d[n-1] = cum_d[n-2], making the terminal delta always 0.
    """
    assert roundtripped.incidence == pytest.approx(
        original.incidence, abs=tol_angle
    ), f"{label}: incidence {roundtripped.incidence} != {original.incidence}"

    assert roundtripped.chord == pytest.approx(
        original.chord, abs=tol_chord
    ), f"{label}: chord {roundtripped.chord} != {original.chord}"

    if not is_terminal_tip:
        assert roundtripped.dihedral_as_rotation_in_degrees == pytest.approx(
            original.dihedral_as_rotation_in_degrees, abs=0.1
        ), f"{label}: dihedral {roundtripped.dihedral_as_rotation_in_degrees} != {original.dihedral_as_rotation_in_degrees}"


def _assert_segment_match(orig_seg, rt_seg, seg_idx, *, total_segments=None):
    """Assert that a segment survives the roundtrip.

    Compares the WingConfiguration segments (after create_wing_configuration),
    NOT the raw schema input. This is important because create_wing_configuration
    derives root_airfoil of segment 1+ from the previous tip_airfoil.

    Length and sweep may differ when rc ≠ 0 (documented lossy projection),
    so we use a relaxed tolerance.
    """
    is_last = total_segments is not None and seg_idx == total_segments - 1

    _assert_airfoil_match(
        orig_seg.root_airfoil, rt_seg.root_airfoil, f"seg[{seg_idx}].root"
    )
    _assert_airfoil_match(
        orig_seg.tip_airfoil, rt_seg.tip_airfoil, f"seg[{seg_idx}].tip",
        is_terminal_tip=is_last,
    )
    # Length/sweep tolerance is relaxed because rc projection changes these
    assert rt_seg.length == pytest.approx(
        orig_seg.length, abs=1.0
    ), f"seg[{seg_idx}].length: {rt_seg.length} != {orig_seg.length}"
    assert rt_seg.sweep == pytest.approx(
        orig_seg.sweep, abs=1.0
    ), f"seg[{seg_idx}].sweep: {rt_seg.sweep} != {orig_seg.sweep}"


# ═══════════════════════════════════════════════════════════════════
# Basic roundtrip tests
# ═══════════════════════════════════════════════════════════════════


class TestBasicRoundtrip:
    """Flat wings, zero angles — sanity check."""

    def test_single_segment_flat(self):
        wing = _wing(_seg())
        wc, wc2 = _roundtrip(wing)
        assert len(wc2.segments) == 1
        _assert_segment_match(wing.segments[0], wc2.segments[0], 0, total_segments=1)

    def test_two_segments_flat(self):
        wing = _wing(
            _seg(root_chord=200, tip_chord=180, length=100),
            _seg(root_chord=180, tip_chord=160, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        assert len(wc2.segments) == 2
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)

    def test_four_segments_flat(self):
        wing = _wing(
            _seg(root_chord=200, tip_chord=180, length=50, sweep=3),
            _seg(root_chord=180, tip_chord=160, length=200, sweep=5),
            _seg(root_chord=160, tip_chord=120, length=200, sweep=8),
            _seg(root_chord=120, tip_chord=60, length=100, sweep=12),
        )
        wc, wc2 = _roundtrip(wing)
        assert len(wc2.segments) == 4
        for i in range(4):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=4)


# ═══════════════════════════════════════════════════════════════════
# Incidence / twist roundtrip
# ═══════════════════════════════════════════════════════════════════


class TestIncidenceRoundtrip:
    """Incidence (twist) is the most fragile parameter in the conversion."""

    def test_constant_incidence(self):
        """All airfoils at 2° — no twist gradient."""
        wing = _wing(
            _seg(root_incidence=2, tip_incidence=2, length=100),
            _seg(root_incidence=2, tip_incidence=2, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)

    def test_washout_classic(self):
        """Root 3°, tip -1° — classic washout."""
        wing = _wing(
            _seg(root_incidence=3, tip_incidence=1, length=200),
            _seg(root_incidence=1, tip_incidence=-1, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)

    def test_washin(self):
        """Negative root, positive tip — washin."""
        wing = _wing(
            _seg(root_incidence=-1.5, tip_incidence=0, length=100),
            _seg(root_incidence=0, tip_incidence=1.5, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)

    def test_root_incidence_tip_zero(self):
        """Regression: root=-1.5°, tip=0° was corrupted to tip=1.5°."""
        wing = _wing(
            _seg(root_incidence=-1.5, tip_incidence=0, length=50),
            _seg(root_incidence=0, tip_incidence=0, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        _assert_segment_match(wc.segments[0], wc2.segments[0], 0, total_segments=2)
        _assert_segment_match(wc.segments[1], wc2.segments[1], 1, total_segments=2)

    def test_large_twist_range(self):
        """8° root to -5° tip — large but valid range."""
        wing = _wing(
            _seg(root_incidence=8, tip_incidence=4, length=100),
            _seg(root_incidence=4, tip_incidence=0, length=200),
            _seg(root_incidence=0, tip_incidence=-5, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=3)

    def test_nonmonotone_twist(self):
        """Twist increases then decreases — 0°/2°/4°/1°."""
        wing = _wing(
            _seg(root_incidence=0, tip_incidence=2, length=100),
            _seg(root_incidence=2, tip_incidence=4, length=200),
            _seg(root_incidence=4, tip_incidence=1, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=3)

    def test_all_segments_different_incidence(self):
        """Each segment has unique root/tip incidence."""
        wing = _wing(
            _seg(root_incidence=3, tip_incidence=2, length=50),
            _seg(root_incidence=2, tip_incidence=0, length=200),
            _seg(root_incidence=0, tip_incidence=-2, length=200),
            _seg(root_incidence=-2, tip_incidence=-4, length=100),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(4):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=4)


# ═══════════════════════════════════════════════════════════════════
# Dihedral roundtrip
# ═══════════════════════════════════════════════════════════════════


class TestDihedralRoundtrip:

    def test_constant_dihedral(self):
        wing = _wing(
            _seg(root_dihedral=3, tip_dihedral=3, length=200),
            _seg(root_dihedral=3, tip_dihedral=3, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)

    def test_dihedral_only_root_segment(self):
        wing = _wing(
            _seg(root_dihedral=2, length=50),
            _seg(length=200),
            _seg(length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=3)

    def test_negative_dihedral_anhedral(self):
        """Anhedral: negative dihedral on a segment."""
        wing = _wing(
            _seg(root_dihedral=-3, tip_dihedral=-3, length=100),
            _seg(root_dihedral=-3, tip_dihedral=-3, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=2)


# ═══════════════════════════════════════════════════════════════════
# Combined: incidence + dihedral + sweep
# ═══════════════════════════════════════════════════════════════════


class TestCombinedRoundtrip:

    def test_washin_with_dihedral_and_sweep(self):
        """Incidence, dihedral, sweep all non-zero — realistic case."""
        wing = _wing(
            _seg(
                root_incidence=-1.5, tip_incidence=1, root_dihedral=3,
                length=50, sweep=5, root_chord=200, tip_chord=180,
            ),
            _seg(
                root_incidence=1, tip_incidence=0,
                length=200, sweep=8, root_chord=180, tip_chord=140,
            ),
            _seg(
                root_incidence=0, tip_incidence=-1,
                length=200, sweep=12, root_chord=140, tip_chord=80,
            ),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=3)

    def test_trapez_wing_full(self):
        """Classic trapezoid wing — 4 segments, taper, washout, dihedral."""
        wing = _wing(
            _seg(
                root_airfoil="naca2424", root_chord=200, root_incidence=2,
                tip_airfoil="naca2424", tip_chord=180, tip_incidence=1.5,
                root_dihedral=2, length=50, sweep=3,
            ),
            _seg(
                root_airfoil="naca2424", root_chord=180, root_incidence=1.5,
                tip_airfoil="naca2424", tip_chord=160, tip_incidence=1,
                length=200, sweep=5,
            ),
            _seg(
                root_airfoil="naca2424", root_chord=160, root_incidence=1,
                tip_airfoil="naca2424", tip_chord=120, tip_incidence=0,
                length=200, sweep=8,
            ),
            _seg(
                root_airfoil="naca2424", root_chord=120, root_incidence=0,
                tip_airfoil="naca2424", tip_chord=60, tip_incidence=-1,
                length=100, sweep=12,
            ),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(4):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i, total_segments=4)


# ═══════════════════════════════════════════════════════════════════
# Airfoil name roundtrip
# ═══════════════════════════════════════════════════════════════════


class TestAirfoilNameRoundtrip:

    def test_airfoil_name_preserved(self):
        wing = _wing(
            _seg(root_airfoil="naca2412", tip_airfoil="naca0015"),
        )
        wc, wc2 = _roundtrip(wing)
        assert "naca2412" in wc2.segments[0].root_airfoil.airfoil.lower()
        assert "naca0015" in wc2.segments[0].tip_airfoil.airfoil.lower()

    def test_different_airfoils_per_segment(self):
        wing = _wing(
            _seg(root_airfoil="naca0015", tip_airfoil="naca2412"),
            _seg(root_airfoil="naca2412", tip_airfoil="naca0015"),
        )
        wc, wc2 = _roundtrip(wing)
        assert "naca2412" in wc2.segments[0].tip_airfoil.airfoil.lower()
        assert "naca0015" in wc2.segments[1].tip_airfoil.airfoil.lower()


# ═══════════════════════════════════════════════════════════════════
# wing_segment_type roundtrip (gh-351)
# ═══════════════════════════════════════════════════════════════════


class TestWingSegmentTypeRoundtrip:

    def test_wing_segment_type_auto_assigned(self):
        """wing_segment_type is set by the CAD layer and survives roundtrip."""
        wing = _wing(
            _seg(root_chord=200, tip_chord=180, length=50),
            _seg(root_chord=180, tip_chord=140, length=200),
            _seg(root_chord=140, tip_chord=80, length=200, tip_type="flat"),
        )
        _, wc2 = _roundtrip(wing)
        assert wc2.segments[0].wing_segment_type == "root"
        assert wc2.segments[1].wing_segment_type == "segment"
        assert wc2.segments[2].wing_segment_type == "tip"

    def test_wing_segment_type_schema_field_exists(self):
        """Segment schema includes wing_segment_type for API serialization."""
        seg = Segment(
            root_airfoil=Airfoil(airfoil=AIRFOIL, chord=200),
            tip_airfoil=Airfoil(airfoil=AIRFOIL, chord=180),
            length=100, sweep=0,
            wing_segment_type="root",
        )
        data = seg.model_dump()
        assert data["wing_segment_type"] == "root"

    def test_wing_segment_type_defaults_none(self):
        """Segment schema defaults wing_segment_type to None."""
        seg = Segment(
            root_airfoil=Airfoil(airfoil=AIRFOIL, chord=200),
            tip_airfoil=Airfoil(airfoil=AIRFOIL, chord=180),
            length=100, sweep=0,
        )
        assert seg.wing_segment_type is None


# ═══════════════════════════════════════════════════════════════════
# Segment count roundtrip
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# TED propagation — control surfaces must not leak to adjacent segments
# ═══════════════════════════════════════════════════════════════════

from app.schemas.wing import TrailingEdgeDevice  # noqa: E402


class TestTedPropagation:
    """Verify that TED on one segment does not propagate to neighbours.

    Regression test for a bug where the ASB x_sec index is off-by-one
    relative to the WingConfiguration segment index, causing
    _build_segment_details to merge a previous segment's control_surface
    into the current segment's TED.
    """

    def test_ted_does_not_spread_to_adjacent_segments(self):
        """Only segment 1 has a TED; segments 0 and 2 must stay clean."""
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(
                root_chord=280, tip_chord=250, length=400,
                trailing_edge_device=TrailingEdgeDevice(
                    name="aileron", rel_chord_root=0.75, rel_chord_tip=0.75,
                    symmetric=False,
                ),
            ),
            _seg(root_chord=250, tip_chord=200, length=300),
        )

        wc = create_wing_configuration(wing_data)
        asb_schema = wing_config_to_asb_wing_schema(wc, "test", scale=0.001)

        for i, x_sec in enumerate(asb_schema.x_secs):
            if i == 1:
                assert x_sec.trailing_edge_device is not None, (
                    f"x_sec[{i}] (segment 1 root) should have TED"
                )
            else:
                assert x_sec.trailing_edge_device is None, (
                    f"x_sec[{i}] should NOT have TED — TED leaked from segment 1"
                )

    def test_control_surface_only_on_segments_with_ted(self):
        """control_surface must only appear on x_secs whose segment has a TED.

        The ASB x_sec at index i≥1 carries the previous segment's
        control_surface, but storing it would cause WingModel.from_dict
        to recreate a phantom TED via _merge_ted_with_control_surface.
        Only segment-owned TED data is stored.
        """
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(
                root_chord=280, tip_chord=250, length=400,
                trailing_edge_device=TrailingEdgeDevice(
                    name="aileron", rel_chord_root=0.75, rel_chord_tip=0.75,
                    symmetric=False,
                ),
            ),
            _seg(root_chord=250, tip_chord=200, length=300),
        )

        wc = create_wing_configuration(wing_data)
        asb_schema = wing_config_to_asb_wing_schema(wc, "test", scale=0.001)

        # x_sec[1] = segment 1 (has TED) → must have cs
        assert asb_schema.x_secs[1].control_surface is not None
        assert asb_schema.x_secs[1].control_surface.name == "aileron"
        # All other x_secs: no cs (segment has no TED)
        assert asb_schema.x_secs[0].control_surface is None
        assert asb_schema.x_secs[2].control_surface is None
        assert asb_schema.x_secs[3].control_surface is None

    def test_ted_survives_full_roundtrip_on_wingconfig(self):
        """Converter roundtrip: only the TED-bearing segment has a TED in WingConfig."""
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(
                root_chord=280, tip_chord=250, length=400,
                trailing_edge_device=TrailingEdgeDevice(
                    name="aileron", rel_chord_root=0.75, rel_chord_tip=0.75,
                    symmetric=False,
                ),
            ),
            _seg(root_chord=250, tip_chord=200, length=300),
        )

        _, wc2 = _roundtrip(wing_data)

        assert wc2.segments[0].trailing_edge_device is None
        assert wc2.segments[1].trailing_edge_device is not None
        ted = wc2.segments[1].trailing_edge_device
        assert ted.name == "aileron"
        assert ted.rel_chord_root == pytest.approx(0.75)
        assert ted.rel_chord_tip == pytest.approx(0.75)
        assert ted.symmetric is False
        assert wc2.segments[2].trailing_edge_device is None

    def test_ted_on_first_segment(self):
        """Boundary: TED on segment 0 must not leak forward."""
        wing_data = _wing(
            _seg(
                root_chord=300, tip_chord=280, length=500,
                trailing_edge_device=TrailingEdgeDevice(
                    name="flap", rel_chord_root=0.7, rel_chord_tip=0.7,
                ),
            ),
            _seg(root_chord=280, tip_chord=250, length=400),
            _seg(root_chord=250, tip_chord=200, length=300),
        )

        _, wc2 = _roundtrip(wing_data)
        assert wc2.segments[0].trailing_edge_device is not None
        assert wc2.segments[0].trailing_edge_device.name == "flap"
        assert wc2.segments[1].trailing_edge_device is None
        assert wc2.segments[2].trailing_edge_device is None

    def test_ted_on_last_segment(self):
        """Boundary: TED on last segment must not leak backward."""
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(root_chord=280, tip_chord=250, length=400),
            _seg(
                root_chord=250, tip_chord=200, length=300,
                trailing_edge_device=TrailingEdgeDevice(
                    name="elevator", rel_chord_root=0.8, rel_chord_tip=0.8,
                ),
            ),
        )

        _, wc2 = _roundtrip(wing_data)
        assert wc2.segments[0].trailing_edge_device is None
        assert wc2.segments[1].trailing_edge_device is None
        assert wc2.segments[2].trailing_edge_device is not None
        assert wc2.segments[2].trailing_edge_device.name == "elevator"

    def test_multiple_non_adjacent_teds(self):
        """TEDs on segments 0 and 2 (non-adjacent) must not spread to 1 or 3."""
        wing_data = _wing(
            _seg(
                root_chord=300, tip_chord=280, length=500,
                trailing_edge_device=TrailingEdgeDevice(
                    name="flap", rel_chord_root=0.7, rel_chord_tip=0.7,
                ),
            ),
            _seg(root_chord=280, tip_chord=250, length=400),
            _seg(
                root_chord=250, tip_chord=220, length=300,
                trailing_edge_device=TrailingEdgeDevice(
                    name="aileron", rel_chord_root=0.8, rel_chord_tip=0.8,
                ),
            ),
            _seg(root_chord=220, tip_chord=200, length=200),
        )

        _, wc2 = _roundtrip(wing_data)
        assert wc2.segments[0].trailing_edge_device is not None
        assert wc2.segments[0].trailing_edge_device.name == "flap"
        assert wc2.segments[1].trailing_edge_device is None
        assert wc2.segments[2].trailing_edge_device is not None
        assert wc2.segments[2].trailing_edge_device.name == "aileron"
        assert wc2.segments[3].trailing_edge_device is None

    def test_adjacent_teds_do_not_cross_contaminate(self):
        """Adjacent TED-bearing segments must each retain their own TED."""
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(
                root_chord=280, tip_chord=250, length=400,
                trailing_edge_device=TrailingEdgeDevice(
                    name="flap", rel_chord_root=0.7, rel_chord_tip=0.7,
                ),
            ),
            _seg(
                root_chord=250, tip_chord=220, length=300,
                trailing_edge_device=TrailingEdgeDevice(
                    name="aileron", rel_chord_root=0.8, rel_chord_tip=0.8,
                ),
            ),
            _seg(root_chord=220, tip_chord=200, length=200),
        )

        _, wc2 = _roundtrip(wing_data)
        assert wc2.segments[0].trailing_edge_device is None
        assert wc2.segments[1].trailing_edge_device.name == "flap"
        assert wc2.segments[1].trailing_edge_device.rel_chord_root == pytest.approx(0.7)
        assert wc2.segments[2].trailing_edge_device.name == "aileron"
        assert wc2.segments[2].trailing_edge_device.rel_chord_root == pytest.approx(0.8)
        assert wc2.segments[3].trailing_edge_device is None

    def test_ted_stable_over_repeated_saves(self):
        """Repeated roundtrips must not grow TEDs onto new segments."""
        ted = TrailingEdgeDevice(
            name="aileron", rel_chord_root=0.8, rel_chord_tip=0.8,
            symmetric=True,
        )
        wing_data = _wing(
            _seg(root_chord=300, tip_chord=280, length=500),
            _seg(root_chord=280, tip_chord=250, length=400),
            _seg(
                root_chord=250, tip_chord=220, length=300,
                trailing_edge_device=ted,
            ),
            _seg(root_chord=220, tip_chord=200, length=200),
        )

        wc = create_wing_configuration(wing_data)
        for cycle in range(5):
            asb_schema = wing_config_to_asb_wing_schema(wc, "test", scale=0.001)
            ted_count = sum(
                1 for x in asb_schema.x_secs if x.trailing_edge_device is not None
            )
            assert ted_count == 1, (
                f"Cycle {cycle}: expected 1 TED, found {ted_count} — "
                "TED propagated to adjacent segments"
            )
            wc = asb_wing_schema_to_wing_config(asb_schema, scale=1000.0)


# ═══════════════════════════════════════════════════════════════════
# Drift test — repeated roundtrip stability measure
# ═══════════════════════════════════════════════════════════════════


class TestRoundtripDrift:
    """Measures how much parameters drift when the roundtrip is applied
    repeatedly. This is a stability/quality metric — even if a single
    roundtrip has small errors, repeated application must not diverge."""

    ITERATIONS = 10

    @staticmethod
    def _multi_roundtrip(wing_data: Wing, n: int):
        """Apply the roundtrip n times, return per-iteration snapshots."""
        from app.converters.model_schema_converters import (
            wing_config_to_asb_wing_schema as to_asb,
            asb_wing_schema_to_wing_config as from_asb,
        )
        wc = create_wing_configuration(wing_data)
        snapshots = []

        for _ in range(n):
            asb_schema = to_asb(wc, "test", scale=0.001)
            wc = from_asb(asb_schema, scale=1000.0)
            snapshot = []
            for seg in wc.segments:
                snapshot.append({
                    "root_incidence": seg.root_airfoil.incidence,
                    "tip_incidence": seg.tip_airfoil.incidence,
                    "root_chord": seg.root_airfoil.chord,
                    "tip_chord": seg.tip_airfoil.chord,
                    "root_dihedral": seg.root_airfoil.dihedral_as_rotation_in_degrees,
                    "length": seg.length,
                    "sweep": seg.sweep,
                })
            snapshots.append(snapshot)
        return snapshots

    def test_drift_realistic_6_segment_wing(self):
        """6-segment wing with mixed angles — measures drift over 10 iterations.

        This wing has: varying incidence (washout), dihedral on root,
        sweep on all segments, long spans for maximum lever arm.
        """
        wing = _wing(
            _seg(root_chord=250, tip_chord=230, root_incidence=4, tip_incidence=3,
                 root_dihedral=3, length=80, sweep=5),
            _seg(root_chord=230, tip_chord=200, root_incidence=3, tip_incidence=2,
                 length=400, sweep=10),
            _seg(root_chord=200, tip_chord=170, root_incidence=2, tip_incidence=1,
                 length=500, sweep=15),
            _seg(root_chord=170, tip_chord=130, root_incidence=1, tip_incidence=0,
                 length=500, sweep=20),
            _seg(root_chord=130, tip_chord=90, root_incidence=0, tip_incidence=-1,
                 length=400, sweep=15),
            _seg(root_chord=90, tip_chord=50, root_incidence=-1, tip_incidence=-3,
                 length=200, sweep=10),
        )

        snapshots = self._multi_roundtrip(wing, self.ITERATIONS)

        # Compare first and last iteration — drift should be zero
        first = snapshots[0]
        last = snapshots[-1]

        max_incidence_drift = 0.0
        max_chord_drift = 0.0
        max_length_drift = 0.0

        for seg_idx in range(len(first)):
            for key in ["root_incidence", "tip_incidence"]:
                drift = abs(last[seg_idx][key] - first[seg_idx][key])
                max_incidence_drift = max(max_incidence_drift, drift)
            for key in ["root_chord", "tip_chord"]:
                drift = abs(last[seg_idx][key] - first[seg_idx][key])
                max_chord_drift = max(max_chord_drift, drift)
            drift = abs(last[seg_idx]["length"] - first[seg_idx]["length"])
            max_length_drift = max(max_length_drift, drift)

        # Report drift values for visibility
        print(f"\n{'='*60}")
        print(f"DRIFT after {self.ITERATIONS} roundtrips (6-segment wing):")
        print(f"  max incidence drift: {max_incidence_drift:.6f}°")
        print(f"  max chord drift:     {max_chord_drift:.6f} mm")
        print(f"  max length drift:    {max_length_drift:.6f} mm")
        print(f"{'='*60}")

        # After fix: drift must be zero (idempotent conversion)
        assert max_incidence_drift < 0.01, (
            f"Incidence drifted by {max_incidence_drift:.4f}° over "
            f"{self.ITERATIONS} iterations — conversion is not stable"
        )
        assert max_chord_drift < 0.01, (
            f"Chord drifted by {max_chord_drift:.4f} mm over "
            f"{self.ITERATIONS} iterations"
        )
        # Length may drift slightly due to rc projection (rc=0.25 → rc=0).
        # The first roundtrip changes the representation, subsequent roundtrips
        # should be near-idempotent. 0.5mm over 10 iterations is acceptable.
        assert max_length_drift < 0.5, (
            f"Length drifted by {max_length_drift:.4f} mm over "
            f"{self.ITERATIONS} iterations"
        )

    def test_drift_asymmetric_twist_4_segments(self):
        """4 segments with non-monotone twist pattern and long lever arms."""
        wing = _wing(
            _seg(root_chord=300, tip_chord=260, root_incidence=-2, tip_incidence=3,
                 root_dihedral=5, length=150, sweep=8),
            _seg(root_chord=260, tip_chord=200, root_incidence=3, tip_incidence=-1,
                 length=600, sweep=12),
            _seg(root_chord=200, tip_chord=140, root_incidence=-1, tip_incidence=4,
                 length=600, sweep=18),
            _seg(root_chord=140, tip_chord=60, root_incidence=4, tip_incidence=-3,
                 length=300, sweep=25),
        )

        snapshots = self._multi_roundtrip(wing, self.ITERATIONS)
        first = snapshots[0]
        last = snapshots[-1]

        max_drift = 0.0
        for seg_idx in range(len(first)):
            for key in ["root_incidence", "tip_incidence"]:
                drift = abs(last[seg_idx][key] - first[seg_idx][key])
                max_drift = max(max_drift, drift)

        print(f"\n{'='*60}")
        print(f"DRIFT after {self.ITERATIONS} roundtrips (asymmetric twist):")
        print(f"  max incidence drift: {max_drift:.6f}°")
        print(f"{'='*60}")

        # Print per-iteration drift for diagnostics
        for i, snap in enumerate(snapshots):
            incidences = [f"{s['root_incidence']:.3f}/{s['tip_incidence']:.3f}" for s in snap]
            print(f"  iter {i+1}: {' | '.join(incidences)}")

        assert max_drift < 0.01, (
            f"Incidence drifted by {max_drift:.4f}° — conversion diverges"
        )


class TestSegmentCountRoundtrip:

    def test_one_segment(self):
        _, wc2 = _roundtrip(_wing(_seg()))
        assert len(wc2.segments) == 1

    def test_three_segments(self):
        _, wc2 = _roundtrip(_wing(_seg(), _seg(), _seg()))
        assert len(wc2.segments) == 3

    def test_four_segments(self):
        _, wc2 = _roundtrip(_wing(_seg(), _seg(), _seg(), _seg()))
        assert len(wc2.segments) == 4
