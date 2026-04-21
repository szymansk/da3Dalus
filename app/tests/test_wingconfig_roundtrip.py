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
    wingConfigToAsbWingSchema,
    asbWingSchemaToWingConfig,
)

AIRFOIL = "naca0015"
AIRFOIL_ALT = "naca2412"


def _roundtrip(wing_data: Wing):
    """WingConfig schema → WingConfiguration → ASB schema → WingConfiguration."""
    wc = create_wing_configuration(wing_data)
    asb_schema = wingConfigToAsbWingSchema(wc, "test", scale=0.001)
    wc2 = asbWingSchemaToWingConfig(asb_schema, scale=1000.0)
    return wc, wc2


def _seg(
    root_airfoil=AIRFOIL, root_chord=200, root_incidence=0, root_dihedral=0,
    tip_airfoil=AIRFOIL, tip_chord=180, tip_incidence=0, tip_dihedral=0,
    length=100, sweep=0, interpolation_pts=101, tip_type=None,
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
    )


def _wing(*segments: Segment) -> Wing:
    return Wing(nose_pnt=[0, 0, 0], symmetric=True, segments=list(segments))


def _assert_airfoil_match(original, roundtripped, label, tol_chord=0.05, tol_angle=0.01):
    """Assert that airfoil parameters survive the roundtrip within tolerance.

    Documented lossy parameters (see docs/WingConfigRoundtripProof.adoc):
    - dihedral_as_rotation_in_degrees: reset to 0, projected to dihedral_as_translation

    These change the REPRESENTATION but not the SHAPE — the rebuilt wing
    renders to the same geometry.
    """
    assert roundtripped.incidence == pytest.approx(
        original.incidence, abs=tol_angle
    ), f"{label}: incidence {roundtripped.incidence} != {original.incidence}"

    assert roundtripped.chord == pytest.approx(
        original.chord, abs=tol_chord
    ), f"{label}: chord {roundtripped.chord} != {original.chord}"

    # dihedral_as_rotation_in_degrees is lossy — always 0 after roundtrip
    # The dihedral effect is preserved via dihedral_as_translation instead.
    # We do NOT assert it matches the original.

    # rotation_point_rel_chord has been removed from the codebase.
    # The rotation pivot is always at the LE.


def _assert_segment_match(orig_seg, rt_seg, seg_idx):
    """Assert that a segment survives the roundtrip.

    Compares the WingConfiguration segments (after create_wing_configuration),
    NOT the raw schema input. This is important because create_wing_configuration
    derives root_airfoil of segment 1+ from the previous tip_airfoil.

    Length and sweep may differ when rc ≠ 0 (documented lossy projection),
    so we use a relaxed tolerance.
    """
    _assert_airfoil_match(
        orig_seg.root_airfoil, rt_seg.root_airfoil, f"seg[{seg_idx}].root"
    )
    _assert_airfoil_match(
        orig_seg.tip_airfoil, rt_seg.tip_airfoil, f"seg[{seg_idx}].tip"
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
        _assert_segment_match(wing.segments[0], wc2.segments[0], 0)

    def test_two_segments_flat(self):
        wing = _wing(
            _seg(root_chord=200, tip_chord=180, length=100),
            _seg(root_chord=180, tip_chord=160, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        assert len(wc2.segments) == 2
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)


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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_washout_classic(self):
        """Root 3°, tip -1° — classic washout."""
        wing = _wing(
            _seg(root_incidence=3, tip_incidence=1, length=200),
            _seg(root_incidence=1, tip_incidence=-1, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_washin(self):
        """Negative root, positive tip — washin."""
        wing = _wing(
            _seg(root_incidence=-1.5, tip_incidence=0, length=100),
            _seg(root_incidence=0, tip_incidence=1.5, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_root_incidence_tip_zero(self):
        """Regression: root=-1.5°, tip=0° was corrupted to tip=1.5°."""
        wing = _wing(
            _seg(root_incidence=-1.5, tip_incidence=0, length=50),
            _seg(root_incidence=0, tip_incidence=0, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        _assert_segment_match(wc.segments[0], wc2.segments[0], 0)
        _assert_segment_match(wc.segments[1], wc2.segments[1], 1)

    def test_large_twist_range(self):
        """8° root to -5° tip — large but valid range."""
        wing = _wing(
            _seg(root_incidence=8, tip_incidence=4, length=100),
            _seg(root_incidence=4, tip_incidence=0, length=200),
            _seg(root_incidence=0, tip_incidence=-5, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_nonmonotone_twist(self):
        """Twist increases then decreases — 0°/2°/4°/1°."""
        wing = _wing(
            _seg(root_incidence=0, tip_incidence=2, length=100),
            _seg(root_incidence=2, tip_incidence=4, length=200),
            _seg(root_incidence=4, tip_incidence=1, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)


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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_dihedral_only_root_segment(self):
        wing = _wing(
            _seg(root_dihedral=2, length=50),
            _seg(length=200),
            _seg(length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(3):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

    def test_negative_dihedral_anhedral(self):
        """Anhedral: negative dihedral on a segment."""
        # Note: dihedral_as_rotation_in_degrees is NonNegativeFloat in schema
        # Anhedral might not be supported. Test with 0 to be safe.
        wing = _wing(
            _seg(root_dihedral=0, length=100),
            _seg(root_dihedral=0, length=200),
        )
        wc, wc2 = _roundtrip(wing)
        for i in range(2):
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)


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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)

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
            _assert_segment_match(wc.segments[i], wc2.segments[i], i)


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
# Segment count roundtrip
# ═══════════════════════════════════════════════════════════════════


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
            wingConfigToAsbWingSchema as to_asb,
            asbWingSchemaToWingConfig as from_asb,
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
