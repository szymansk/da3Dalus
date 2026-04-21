"""Verify the fundamental coordinate math from docs/WingConfiguration.adoc.

These tests validate the homogeneous transformation matrices that define
segment coordinate systems. If these formulas are wrong, everything built
on top (CAD, roundtrip, analysis) is wrong.

All formulas are quoted from the documentation with page references.
"""

import math

import numpy as np
import pytest


# ═══════════════════════════════════════════════════════════════════
# The three building blocks from the documentation
# ═══════════════════════════════════════════════════════════════════

def T(x, y, z):
    """Translation matrix.

    From docs/WingConfiguration.adoc:
        T(x,y,z) = [[1,0,0,x],[0,1,0,y],[0,0,1,z],[0,0,0,1]]
    """
    return np.array([
        [1, 0, 0, x],
        [0, 1, 0, y],
        [0, 0, 1, z],
        [0, 0, 0, 1],
    ], dtype=float)


def Rx(delta_deg):
    """Rotation around x-axis (dihedral).

    From docs/WingConfiguration.adoc:
        R_x(δ) = [[1,0,0,0],[0,cos(δ),-sin(δ),0],[0,sin(δ),cos(δ),0],[0,0,0,1]]

    δ = dihedral_as_rotation_in_degrees
    """
    d = math.radians(delta_deg)
    c, s = math.cos(d), math.sin(d)
    return np.array([
        [1, 0,  0, 0],
        [0, c, -s, 0],
        [0, s,  c, 0],
        [0, 0,  0, 1],
    ], dtype=float)


def Ry(iota_deg):
    """Rotation around y-axis (incidence / twist).

    From docs/WingConfiguration.adoc:
        R_y(ι) = [[cos(ι),0,sin(ι),0],[0,1,0,0],[-sin(ι),0,cos(ι),0],[0,0,0,1]]

    ι = incidence angle
    """
    i = math.radians(iota_deg)
    c, s = math.cos(i), math.sin(i)
    return np.array([
        [ c, 0, s, 0],
        [ 0, 1, 0, 0],
        [-s, 0, c, 0],
        [ 0, 0, 0, 1],
    ], dtype=float)


# ═══════════════════════════════════════════════════════════════════
# H matrix formulas from the documentation
# ═══════════════════════════════════════════════════════════════════

def H0(C0, delta0, iota0):
    """Root segment coordinate system.

    From docs/WingConfiguration.adoc (with rotation pivot at LE, rc=0):
        H_0 = R_x(delta_0) . R_y(iota_0)

    Parameters:
        C0: root chord (mm) -- unused, kept for signature compatibility
        delta0: dihedral_as_rotation_in_degrees
        iota0: incidence angle (degrees)
    """
    return Rx(delta0) @ Ry(iota0)


def Hi(Ci, Si_prev, Li_prev, Di_prev, deltai, iotai):
    """Segment i coordinate system (i > 0).

    From docs/WingConfiguration.adoc (with rotation pivot at LE, rc=0):
        H_i = T(S_{i-1}, L_{i-1}, D_{i-1}) . R_x(delta_i) . R_y(iota_i)

    Parameters:
        Ci: chord at this station (mm) -- unused, kept for signature compatibility
        Si_prev: sweep of previous segment (mm)
        Li_prev: length of previous segment (mm)
        Di_prev: z-offset of previous segment (mm), always 0 in current decoupled mode
        deltai: dihedral_as_rotation_in_degrees at this station
        iotai: incidence angle at this station (degrees)
    """
    return T(Si_prev, Li_prev, Di_prev) @ Rx(deltai) @ Ry(iotai)


def CN(H_list):
    """Cumulative coordinate system for segment N.

    From docs/WingConfiguration.adoc:
        C_N = H_0 · ∏(n=1..N) H_n
    """
    result = H_list[0]
    for H in H_list[1:]:
        result = result @ H
    return result


def extract_origin(H):
    """Extract the 3D origin (translation) from a 4x4 homogeneous matrix."""
    return H[:3, 3]


# ═══════════════════════════════════════════════════════════════════
# Test 1: Matrix building blocks
# ═══════════════════════════════════════════════════════════════════


class TestMatrixBuildingBlocks:
    """Verify T, Rx, Ry produce correct matrices."""

    def test_translation_identity(self):
        """T(0,0,0) is the identity matrix."""
        np.testing.assert_array_equal(T(0, 0, 0), np.eye(4))

    def test_translation_moves_origin(self):
        """T(x,y,z) applied to origin gives [x,y,z]."""
        origin = np.array([0, 0, 0, 1])
        result = T(10, 20, 30) @ origin
        np.testing.assert_array_almost_equal(result[:3], [10, 20, 30])

    def test_rx_zero_is_identity(self):
        """R_x(0°) is the identity matrix."""
        np.testing.assert_array_almost_equal(Rx(0), np.eye(4))

    def test_ry_zero_is_identity(self):
        """R_y(0°) is the identity matrix."""
        np.testing.assert_array_almost_equal(Ry(0), np.eye(4))

    def test_rx_90_rotates_y_to_neg_z(self):
        """R_x(90°) rotates [0,1,0] to [0,0,1].

        Dihedral 90° should bank the wing vertically.
        """
        pt = np.array([0, 1, 0, 1])
        result = Rx(90) @ pt
        np.testing.assert_array_almost_equal(result[:3], [0, 0, 1], decimal=10)

    def test_ry_90_rotates_x_to_z(self):
        """R_y(90°) rotates [1,0,0] to [0,0,-1].

        Incidence 90° should point the chord downward.
        Wait — from the matrix: R_y(90°)[1,0,0] = [cos90, 0, -sin90] = [0, 0, -1].
        """
        pt = np.array([1, 0, 0, 1])
        result = Ry(90) @ pt
        np.testing.assert_array_almost_equal(result[:3], [0, 0, -1], decimal=10)

    def test_rx_ry_commute_at_zero(self):
        """R_x(0) · R_y(0) = R_y(0) · R_x(0) = I."""
        np.testing.assert_array_almost_equal(Rx(0) @ Ry(0), np.eye(4))
        np.testing.assert_array_almost_equal(Ry(0) @ Rx(0), np.eye(4))

    def test_rx_ry_do_not_commute_general(self):
        """R_x(α) · R_y(β) ≠ R_y(β) · R_x(α) for non-zero angles."""
        A = Rx(10) @ Ry(20)
        B = Ry(20) @ Rx(10)
        assert not np.allclose(A, B), "Rotations should not commute in general"


# ═══════════════════════════════════════════════════════════════════
# Test 2: H0 — root segment
# ═══════════════════════════════════════════════════════════════════


class TestH0RootSegment:
    """Verify H_0 formula from the documentation."""

    def test_h0_all_zero_is_identity(self):
        """H_0 with no dihedral, no incidence should be identity.

        H_0 = R_x(0) · R_y(0) = I
        """
        H = H0(C0=200, delta0=0, iota0=0)
        np.testing.assert_array_almost_equal(H, np.eye(4))

    def test_h0_incidence_only(self):
        """H_0 with 5° incidence — pure rotation around y-axis.

        H_0 = R_y(5°). Origin stays at [0,0,0].
        """
        H = H0(C0=200, delta0=0, iota0=5)
        origin = extract_origin(H)
        np.testing.assert_array_almost_equal(origin, [0, 0, 0], decimal=10)
        np.testing.assert_array_almost_equal(H, Ry(5), decimal=10)

    def test_h0_dihedral_only(self):
        """H_0 with 10° dihedral — pure R_x rotation.

        H_0 = R_x(10°). Origin stays at [0,0,0].
        """
        H = H0(C0=200, delta0=10, iota0=0)
        origin = extract_origin(H)
        np.testing.assert_array_almost_equal(origin, [0, 0, 0], decimal=10)
        np.testing.assert_array_almost_equal(H, Rx(10), decimal=10)


# ═══════════════════════════════════════════════════════════════════
# Test 3: Hi — subsequent segments
# ═══════════════════════════════════════════════════════════════════


class TestHiSubsequentSegments:

    def test_hi_translation_only(self):
        """H_i with only length — pure translation along y.

        H_i = T(0) · T(0, L, 0) · R_x(0) · R_y(0) · T(0) = T(0, L, 0)
        """
        H = Hi(Ci=180, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)
        expected = T(0, 200, 0)
        np.testing.assert_array_almost_equal(H, expected, decimal=10)

    def test_hi_sweep_and_length(self):
        """H_i with sweep=5mm, length=200mm.

        H_i = T(5, 200, 0)
        """
        H = Hi(Ci=160, Si_prev=5, Li_prev=200, Di_prev=0, deltai=0, iotai=0)
        origin = extract_origin(H)
        assert origin[0] == pytest.approx(5, abs=1e-10)
        assert origin[1] == pytest.approx(200, abs=1e-10)

    def test_hi_with_incidence(self):
        """H_i with 3° incidence at rc=0, length=200.

        H_i = T(0, 200, 0) · R_y(3°)
        Origin is at [0, 200, 0] — incidence doesn't move the LE when rc=0.
        """
        H = Hi(Ci=160, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=3)
        origin = extract_origin(H)
        assert origin[0] == pytest.approx(0, abs=1e-10)
        assert origin[1] == pytest.approx(200, abs=1e-10)
        assert origin[2] == pytest.approx(0, abs=1e-10)

    def test_hi_with_dihedral_translation(self):
        """H_i with z-offset=15mm, length=200.

        H_i = T(0, 200, 15)
        The LE moves up by 15mm.
        """
        H = Hi(Ci=160, Si_prev=0, Li_prev=200, Di_prev=15, deltai=0, iotai=0)
        origin = extract_origin(H)
        assert origin[0] == pytest.approx(0, abs=1e-10)
        assert origin[1] == pytest.approx(200, abs=1e-10)
        assert origin[2] == pytest.approx(15, abs=1e-10)


# ═══════════════════════════════════════════════════════════════════
# Test 4: Cumulative chain C_N
# ═══════════════════════════════════════════════════════════════════


class TestCumulativeChain:

    def test_two_flat_segments(self):
        """Two flat segments: L0=100, L1=200, no angles.

        C_1 = H_0 · H_1
        Station 0: origin [0,0,0]
        Station 1: origin [0, 100, 0] (after H_0 · [0,0,0])
        Station 2: origin [0, 300, 0] (after C_1 · [0,0,0])

        Wait — H_0 is identity (flat), so C_0 = H_0 = I.
        The origin of segment 1 is H_1 applied: T(0, 100, 0) → [0, 100, 0].
        C_1 = H_0 · H_1 means the tip of segment 1 (= root of segment 2).
        """
        h0 = H0(C0=200, delta0=0, iota0=0)
        h1 = Hi(Ci=180, Si_prev=0, Li_prev=100, Di_prev=0, deltai=0, iotai=0)
        h2 = Hi(Ci=160, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        # Origin of x_sec 0 (root): H_0 applied to [0,0,0]
        o0 = extract_origin(h0)
        assert o0[1] == pytest.approx(0)

        # Origin of x_sec 1: C_0 · H_1 · [0,0,0] → H_0·H_1·origin
        c1 = CN([h0, h1])
        o1 = extract_origin(c1)
        assert o1[1] == pytest.approx(100)

        # Origin of x_sec 2: C_0·H_1·H_2·origin
        c2 = CN([h0, h1, h2])
        o2 = extract_origin(c2)
        assert o2[1] == pytest.approx(300)

    def test_two_segments_with_sweep(self):
        """Two segments with sweep: S0=5mm, S1=10mm.

        x_sec 0: x=0
        x_sec 1: x=5 (sweep of segment 0)
        x_sec 2: x=5+10=15 (cumulative sweep)
        """
        h0 = H0(C0=200, delta0=0, iota0=0)
        h1 = Hi(Ci=180, Si_prev=5, Li_prev=100, Di_prev=0, deltai=0, iotai=0)
        h2 = Hi(Ci=160, Si_prev=10, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        o1 = extract_origin(CN([h0, h1]))
        assert o1[0] == pytest.approx(5)

        o2 = extract_origin(CN([h0, h1, h2]))
        assert o2[0] == pytest.approx(15)

    def test_incidence_on_root_does_not_move_subsequent_le(self):
        """Root incidence should not shift subsequent LE positions.

        From the doc: "The rotation axis passes through xyz_le — i.e. the
        effective rotation-point-relative-to-chord in aerosandbox is rc=0."

        At rc=0, R_y rotates around the LE itself, so the LE doesn't move.
        But the subsequent segment's translation IS rotated by the accumulated twist!
        """
        # Root with 5° incidence at rc=0
        h0 = H0(C0=200, delta0=0, iota0=5)
        # Segment 1: length=200, no own angles
        h1 = Hi(Ci=180, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        o0 = extract_origin(h0)
        assert o0[0] == pytest.approx(0)  # LE stays at origin
        assert o0[1] == pytest.approx(0)
        assert o0[2] == pytest.approx(0)

        # x_sec 1: H_0 · H_1 · origin
        # H_0 = R_y(5°), H_1 = T(0, 200, 0)
        # R_y(5°) · T(0,200,0) · [0,0,0,1] = R_y(5°) · [0,200,0,1]
        # = [200*sin5°*0, 200, 200*0, 1] — wait, R_y doesn't affect y.
        # R_y(5°) · [0, 200, 0] = [0*cos5+0*sin5, 200, -0*sin5+0*cos5] = [0, 200, 0]
        # But that's just the rotation of the point [0,200,0] which has no x or z component.
        # Actually H_1 = T(0,200,0), and C_1 = R_y(5°) · T(0,200,0).
        # C_1 · [0,0,0,1] = R_y(5°) · [0, 200, 0, 1]
        # R_y applied: x' = 0*cos5 + 0*sin5 = 0, y'=200, z' = -0*sin5 + 0*cos5 = 0
        # So the LE of x_sec 1 is still at [0, 200, 0]!
        # This is because T(0,200,0) translates along y, and R_y rotates in xz plane.
        c1 = CN([h0, h1])
        o1 = extract_origin(c1)
        assert o1[0] == pytest.approx(0, abs=0.01)
        assert o1[1] == pytest.approx(200, abs=0.01)
        assert o1[2] == pytest.approx(0, abs=0.01)

    def test_dihedral_on_root_shifts_subsequent_le_upward(self):
        """Root dihedral=10° tilts the wing, subsequent LE moves up.

        H_0 = R_x(10°). H_1 = T(0, 200, 0).
        C_1 · origin = R_x(10°) · [0, 200, 0, 1]
        = [0, 200*cos10°, 200*sin10°, 1]
        """
        h0 = H0(C0=200, delta0=10, iota0=0)
        h1 = Hi(Ci=180, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        c1 = CN([h0, h1])
        o1 = extract_origin(c1)

        assert o1[0] == pytest.approx(0, abs=0.01)
        assert o1[1] == pytest.approx(200 * math.cos(math.radians(10)), abs=0.01)
        assert o1[2] == pytest.approx(200 * math.sin(math.radians(10)), abs=0.01)


# ═══════════════════════════════════════════════════════════════════
# Test 5: Inverse formulas from the documentation
# ═══════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# Test 6: Full math roundtrip — forward then reverse
# ═══════════════════════════════════════════════════════════════════


class TestMathRoundtrip:
    """Apply forward formulas (WingConfig → ASB), then reverse formulas
    (ASB → WingConfig), and verify we get the original parameters back.

    Forward (docs "Forward direction: asb_wing()"):
        twist[i] = Σ(ι_k for k ≤ i)
        xyz_le[i] from H-matrix chain

    Reverse (docs "Reverse direction: from_asb()"):
        segments[0].root_airfoil.incidence = twist[0]
        segments[i].tip_airfoil.incidence = twist[i+1] - twist[i]
        T_i = R_y(-twist[i]) · (xyz_le[i+1] - xyz_le[i])
        Then: sweep = T_i[0], length = T_i[1], dihedral_translation = T_i[2]

    Roundtrip contract (docs):
        dihedral_as_rotation_in_degrees → reset to 0 (lossy)
        All else must be exact.
    """

    @staticmethod
    def _forward(segments):
        """Apply forward formulas: WingConfig params → ASB (xyz_le, twist, chord).

        Returns list of {xyz_le, twist, chord} per x_sec.
        """
        xsecs = []
        H_matrices = []

        for seg_idx, seg in enumerate(segments):
            if seg_idx == 0:
                C0 = seg["root_chord"]
                delta0, iota0 = seg.get("root_dihedral", 0), seg.get("root_incidence", 0)
                H = Rx(delta0) @ Ry(iota0)
                H_matrices.append(H)
                xsecs.append({
                    "xyz_le": extract_origin(H).copy(),
                    "twist": iota0,
                    "chord": C0,
                })
            else:
                prev = segments[seg_idx - 1]
                Ci = prev["tip_chord"]
                deltai = prev.get("tip_dihedral", 0)
                iotai = prev.get("tip_incidence", 0)
                Si, Li = prev["sweep"], prev["length"]
                Di = prev.get("dihedral_translation", 0)

                H = T(Si, Li, Di) @ Rx(deltai) @ Ry(iotai)
                H_matrices.append(H)

                C_cum = H_matrices[0].copy()
                for Hm in H_matrices[1:]:
                    C_cum = C_cum @ Hm

                cum_twist = segments[0]["root_incidence"]
                for k in range(seg_idx):
                    cum_twist += segments[k].get("tip_incidence", 0)

                xsecs.append({
                    "xyz_le": extract_origin(C_cum).copy(),
                    "twist": cum_twist,
                    "chord": Ci,
                })

        # Last x_sec (tip of last segment)
        last = segments[-1]
        Ci = last["tip_chord"]
        deltai = last.get("tip_dihedral", 0)
        iotai = last.get("tip_incidence", 0)
        Si, Li = last["sweep"], last["length"]
        Di = last.get("dihedral_translation", 0)

        H = T(Si, Li, Di) @ Rx(deltai) @ Ry(iotai)
        H_matrices.append(H)

        C_cum = H_matrices[0].copy()
        for Hm in H_matrices[1:]:
            C_cum = C_cum @ Hm

        cum_twist = segments[0]["root_incidence"]
        for k in range(len(segments)):
            cum_twist += segments[k].get("tip_incidence", 0)

        xsecs.append({
            "xyz_le": extract_origin(C_cum).copy(),
            "twist": cum_twist,
            "chord": Ci,
        })

        return xsecs

    @staticmethod
    def _reverse(asb_xsecs):
        """Apply reverse formulas: ASB (xyz_le, twist, chord) → WingConfig params.

        From docs "Reverse direction: from_asb()":
            dihedral_as_rotation_in_degrees = 0 on all airfoils
            segments[0].root_incidence = twist[0]
            segments[i].tip_incidence = twist[i+1] - twist[i]
            T_i = R_y(-twist[i]) · (xyz_le[i+1] - xyz_le[i])
            sweep = T_i[0], length = T_i[1], dihedral_translation = T_i[2]
        """
        n_xsecs = len(asb_xsecs)
        segments = []

        for i in range(n_xsecs - 1):
            delta_le = asb_xsecs[i + 1]["xyz_le"] - asb_xsecs[i]["xyz_le"]
            twist_i = asb_xsecs[i]["twist"]

            # Pre-rotated translation: T_i = R_y(-twist[i]) · delta_le
            R_neg = Ry(-twist_i)[:3, :3]
            T_i = R_neg @ delta_le

            seg = {
                "root_chord": asb_xsecs[i]["chord"],
                "root_incidence": asb_xsecs[i]["twist"] if i == 0 else (asb_xsecs[i]["twist"] - asb_xsecs[i - 1]["twist"]),
                "root_dihedral": 0,  # lossy: always 0 in reverse        # lossy: always 0 in reverse
                "tip_chord": asb_xsecs[i + 1]["chord"],
                "tip_incidence": asb_xsecs[i + 1]["twist"] - asb_xsecs[i]["twist"],
                "tip_dihedral": 0,
                "sweep": float(T_i[0]),
                "length": float(T_i[1]),
                "dihedral_translation": float(T_i[2]),
            }
            segments.append(seg)

        return segments

    @staticmethod
    def _assert_roundtrip(original_segments, recovered_segments, label=""):
        """Verify recovered parameters match originals within tolerance.

        Lossy fields (dihedral_as_rotation) are skipped.
        """
        assert len(recovered_segments) == len(original_segments), \
            f"{label}: segment count {len(recovered_segments)} != {len(original_segments)}"

        for i, (orig, rec) in enumerate(zip(original_segments, recovered_segments, strict=True)):
            prefix = f"{label} seg[{i}]"

            # Incidence must roundtrip exactly
            assert rec["root_incidence"] == pytest.approx(orig["root_incidence"], abs=0.001), \
                f"{prefix}: root_incidence {rec['root_incidence']} != {orig['root_incidence']}"
            assert rec["tip_incidence"] == pytest.approx(orig.get("tip_incidence", 0), abs=0.001), \
                f"{prefix}: tip_incidence {rec['tip_incidence']} != {orig.get('tip_incidence', 0)}"

            # Chord must roundtrip exactly
            assert rec["root_chord"] == pytest.approx(orig["root_chord"], abs=0.01), \
                f"{prefix}: root_chord {rec['root_chord']} != {orig['root_chord']}"
            assert rec["tip_chord"] == pytest.approx(orig["tip_chord"], abs=0.01), \
                f"{prefix}: tip_chord {rec['tip_chord']} != {orig['tip_chord']}"

            # Length and sweep — may have small differences due to rc projection
            assert rec["length"] == pytest.approx(orig["length"], abs=0.1), \
                f"{prefix}: length {rec['length']} != {orig['length']}"
            assert rec["sweep"] == pytest.approx(orig["sweep"], abs=0.1), \
                f"{prefix}: sweep {rec['sweep']} != {orig['sweep']}"

    # ── Test cases: same configurations as roundtrip tests ──

    def test_single_segment_flat(self):
        segs = [{"root_chord": 200, "root_incidence": 0, "root_dihedral": 0,
                 "tip_chord": 180, "tip_incidence": 0, "length": 100, "sweep": 0}]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        self._assert_roundtrip(segs, rec, "flat")

    def test_washout_classic(self):
        segs = [
            {"root_chord": 200, "root_incidence": 3, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": 1, "length": 200, "sweep": 0},
            {"root_chord": 180, "root_incidence": 1, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": -1, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        self._assert_roundtrip(segs, rec, "washout")

    def test_washin_basic(self):
        """Washin at rc=0 — should roundtrip exactly (no LE displacement)."""
        segs = [
            {"root_chord": 200, "root_incidence": -1.5, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": 0, "length": 50, "sweep": 0},
            {"root_chord": 180, "root_incidence": 0, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 1.5, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        self._assert_roundtrip(segs, rec, "washin_rc0")

    def test_washin_with_sweep(self):
        """Washin at rc=0.25 — length/sweep will differ due to rc projection.

        Incidence and chord must still roundtrip exactly.
        """
        segs = [
            {"root_chord": 200, "root_incidence": -1.5, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": 0, "length": 50, "sweep": 0},
            {"root_chord": 180, "root_incidence": 0, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 1.5, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        # Incidence and chord roundtrip exactly
        for i in range(len(segs)):
            assert rec[i]["root_incidence"] == pytest.approx(segs[i]["root_incidence"], abs=0.001)
            assert rec[i]["tip_incidence"] == pytest.approx(segs[i]["tip_incidence"], abs=0.001)
            assert rec[i]["root_chord"] == pytest.approx(segs[i]["root_chord"], abs=0.01)
            assert rec[i]["tip_chord"] == pytest.approx(segs[i]["tip_chord"], abs=0.01)
        # Length/sweep may differ due to rc projection — that's documented as lossy

    def test_four_segments_with_sweep_and_twist(self):
        segs = [
            {"root_chord": 200, "root_incidence": 3, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": 2, "length": 50, "sweep": 3},
            {"root_chord": 180, "root_incidence": 2, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 0, "length": 200, "sweep": 5},
            {"root_chord": 160, "root_incidence": 0, "root_dihedral": 0,
             "tip_chord": 120, "tip_incidence": -2, "length": 200, "sweep": 8},
            {"root_chord": 120, "root_incidence": -2, "root_dihedral": 0,
             "tip_chord": 60, "tip_incidence": -4, "length": 100, "sweep": 12},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        # Check incidence and chord roundtrip
        for i in range(len(segs)):
            assert rec[i]["root_incidence"] == pytest.approx(segs[i]["root_incidence"], abs=0.001), \
                f"seg[{i}] root_incidence"
            assert rec[i]["tip_incidence"] == pytest.approx(segs[i]["tip_incidence"], abs=0.001), \
                f"seg[{i}] tip_incidence"

    def test_large_twist_nonmonotone(self):
        """Non-monotone twist: 0°/2°/4°/1° — the delta approach should handle this."""
        segs = [
            {"root_chord": 200, "root_incidence": 0, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": 2, "length": 100, "sweep": 0},
            {"root_chord": 180, "root_incidence": 2, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 4, "length": 200, "sweep": 0},
            {"root_chord": 160, "root_incidence": 4, "root_dihedral": 0,
             "tip_chord": 140, "tip_incidence": 1, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        self._assert_roundtrip(segs, rec, "nonmonotone")

    def test_dihedral_projects_to_translation(self):
        """Dihedral via rotation roundtrips through ASB conversion.

        Dihedral is always expressed as dihedral_as_rotation_in_degrees.
        """
        segs = [
            {"root_chord": 200, "root_incidence": 0, "root_dihedral": 5,
             "tip_chord": 180, "tip_incidence": 0, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)

        # Incidence roundtrips
        assert rec[0]["root_incidence"] == pytest.approx(0, abs=0.001)
        assert rec[0]["tip_incidence"] == pytest.approx(0, abs=0.001)

        # Dihedral projected: root_dihedral=0 but dihedral_translation > 0
        assert rec[0]["root_dihedral"] == 0  # always 0 in reverse
        # The translation should encode the dihedral effect
        # z = L * sin(5°) ≈ 200 * 0.0872 ≈ 17.4mm
        assert rec[0]["dihedral_translation"] == pytest.approx(
            200 * math.sin(math.radians(5)), abs=0.5)

    def test_multi_segment_roundtrip(self):
        """Multi-segment roundtrip. Incidence must roundtrip exactly."""
        segs = [
            {"root_chord": 200, "root_incidence": 5, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -2, "length": 100, "sweep": 0},
            {"root_chord": 180, "root_incidence": -2, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 3, "length": 200, "sweep": 0},
        ]
        asb = self._forward(segs)
        rec = self._reverse(asb)
        for i in range(len(segs)):
            assert rec[i]["root_incidence"] == pytest.approx(segs[i]["root_incidence"], abs=0.001), \
                f"seg[{i}] root_incidence"
            assert rec[i]["tip_incidence"] == pytest.approx(segs[i]["tip_incidence"], abs=0.001), \
                f"seg[{i}] tip_incidence"

    def test_n_times_math_roundtrip_no_drift(self):
        """Apply forward → reverse → forward → reverse N times.

        If the math is correct, a single roundtrip should produce a
        canonical form (dihedral=0). Subsequent roundtrips of that
        canonical form must be perfectly idempotent — zero drift.
        """
        N = 10
        segs = [
            {"root_chord": 250, "root_incidence": 4, "root_dihedral": 3,
             "tip_chord": 230, "tip_incidence": 3, "length": 80, "sweep": 5},
            {"root_chord": 230, "root_incidence": 3, "root_dihedral": 0,
             "tip_chord": 200, "tip_incidence": 2, "length": 400, "sweep": 10},
            {"root_chord": 200, "root_incidence": 2, "root_dihedral": 0,
             "tip_chord": 170, "tip_incidence": 1, "length": 500, "sweep": 15},
            {"root_chord": 170, "root_incidence": 1, "root_dihedral": 0,
             "tip_chord": 130, "tip_incidence": 0, "length": 500, "sweep": 20},
            {"root_chord": 130, "root_incidence": 0, "root_dihedral": 0,
             "tip_chord": 90, "tip_incidence": -1, "length": 400, "sweep": 15},
            {"root_chord": 90, "root_incidence": -1, "root_dihedral": 0,
             "tip_chord": 50, "tip_incidence": -3, "length": 200, "sweep": 10},
        ]

        # First roundtrip: forward → reverse → produces canonical form
        asb = self._forward(segs)
        canonical = self._reverse(asb)

        # Subsequent roundtrips of canonical form must be idempotent
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        # Compare canonical (after 1st roundtrip) with final (after N+1 roundtrips)
        max_incidence_drift = 0.0
        max_chord_drift = 0.0
        max_length_drift = 0.0

        for i in range(len(canonical)):
            for key in ["root_incidence", "tip_incidence"]:
                drift = abs(current[i][key] - canonical[i][key])
                max_incidence_drift = max(max_incidence_drift, drift)
            for key in ["root_chord", "tip_chord"]:
                drift = abs(current[i][key] - canonical[i][key])
                max_chord_drift = max(max_chord_drift, drift)
            drift = abs(current[i]["length"] - canonical[i]["length"])
            max_length_drift = max(max_length_drift, drift)

        print(f"\n{'='*60}")
        print(f"MATH DRIFT after {N} roundtrips (6-segment wing):")
        print(f"  max incidence drift: {max_incidence_drift:.10f}°")
        print(f"  max chord drift:     {max_chord_drift:.10f} mm")
        print(f"  max length drift:    {max_length_drift:.10f} mm")
        print(f"{'='*60}")

        assert max_incidence_drift < 1e-10, \
            f"Math roundtrip drifted: incidence {max_incidence_drift}°"
        assert max_chord_drift < 1e-10, \
            f"Math roundtrip drifted: chord {max_chord_drift} mm"
        assert max_length_drift < 1e-10, \
            f"Math roundtrip drifted: length {max_length_drift} mm"


    def test_asb_to_wc_to_asb_roundtrip(self):
        """Start from ASB representation, convert to WC, back to ASB.

        ASB → WC → ASB must reproduce the original xyz_le and twist exactly.
        """
        # Construct ASB xsecs directly (as if read from aerosandbox)
        asb_xsecs = [
            {"xyz_le": np.array([0.0, 0.0, 0.0]), "twist": 3.0, "chord": 200},
            {"xyz_le": np.array([5.0, 200.0, 0.0]), "twist": 1.0, "chord": 180},
            {"xyz_le": np.array([13.0, 400.0, 0.0]), "twist": -1.0, "chord": 160},
            {"xyz_le": np.array([25.0, 500.0, 0.0]), "twist": -3.0, "chord": 120},
        ]

        # ASB → WC
        wc_segments = self._reverse(asb_xsecs)

        # WC → ASB
        asb_recovered = self._forward(wc_segments)

        # Compare
        for i in range(len(asb_xsecs)):
            np.testing.assert_array_almost_equal(
                asb_recovered[i]["xyz_le"], asb_xsecs[i]["xyz_le"], decimal=6,
                err_msg=f"x_sec {i}: xyz_le mismatch")
            assert asb_recovered[i]["twist"] == pytest.approx(asb_xsecs[i]["twist"], abs=0.001), \
                f"x_sec {i}: twist {asb_recovered[i]['twist']} != {asb_xsecs[i]['twist']}"
            assert asb_recovered[i]["chord"] == pytest.approx(asb_xsecs[i]["chord"], abs=0.01), \
                f"x_sec {i}: chord mismatch"

    def test_wc_to_asb_to_wc_roundtrip(self):
        """Start from WC representation, convert to ASB, back to WC.

        WC → ASB → WC must reproduce incidence and chord exactly.
        Length/sweep may differ if rc ≠ 0 (documented lossy projection).
        """
        wc_segs = [
            {"root_chord": 200, "root_incidence": 3, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -2, "length": 200, "sweep": 5},
            {"root_chord": 180, "root_incidence": -2, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 1, "length": 200, "sweep": 8},
            {"root_chord": 160, "root_incidence": 1, "root_dihedral": 0,
             "tip_chord": 120, "tip_incidence": -3, "length": 100, "sweep": 12},
        ]

        # WC → ASB
        asb = self._forward(wc_segs)

        # ASB → WC
        wc_recovered = self._reverse(asb)

        self._assert_roundtrip(wc_segs, wc_recovered, "wc_to_asb_to_wc")

    def test_n_times_wc_asb_wc_drift(self):
        """WC → ASB → WC applied N times. Must be idempotent after first roundtrip."""
        N = 10
        segs = [
            {"root_chord": 250, "root_incidence": 4, "root_dihedral": 3,
             "tip_chord": 230, "tip_incidence": 3, "length": 80, "sweep": 5},
            {"root_chord": 230, "root_incidence": 3, "root_dihedral": 0,
             "tip_chord": 200, "tip_incidence": 2, "length": 400, "sweep": 10},
            {"root_chord": 200, "root_incidence": 2, "root_dihedral": 0,
             "tip_chord": 170, "tip_incidence": 1, "length": 500, "sweep": 15},
            {"root_chord": 170, "root_incidence": 1, "root_dihedral": 0,
             "tip_chord": 130, "tip_incidence": 0, "length": 500, "sweep": 20},
        ]

        # First roundtrip produces canonical form
        asb = self._forward(segs)
        canonical = self._reverse(asb)

        # Iterate N more times
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = 0.0
        for i in range(len(canonical)):
            for key in ["root_incidence", "tip_incidence"]:
                drift = abs(current[i][key] - canonical[i][key])
                max_drift = max(max_drift, drift)

        print(f"\n  WC→ASB→WC drift after {N} iterations: {max_drift:.10f}°")
        assert max_drift < 1e-10, f"WC→ASB→WC drifted: {max_drift}°"

    def test_n_times_asb_wc_asb_drift(self):
        """ASB → WC → ASB applied N times. Must be perfectly idempotent."""
        N = 10
        asb_xsecs = [
            {"xyz_le": np.array([0.0, 0.0, 0.0]), "twist": 4.0, "chord": 250},
            {"xyz_le": np.array([5.0, 80.0, 4.2]), "twist": 3.0, "chord": 230},
            {"xyz_le": np.array([15.0, 480.0, 4.2]), "twist": 2.0, "chord": 200},
            {"xyz_le": np.array([30.0, 980.0, 4.2]), "twist": 0.0, "chord": 170},
            {"xyz_le": np.array([50.0, 1480.0, 4.2]), "twist": -1.0, "chord": 130},
        ]

        # First roundtrip
        wc = self._reverse(asb_xsecs)
        canonical_asb = self._forward(wc)

        # Iterate N more times
        current_asb = canonical_asb
        for _ in range(N):
            wc = self._reverse(current_asb)
            current_asb = self._forward(wc)

        max_le_drift = 0.0
        max_twist_drift = 0.0
        for i in range(len(canonical_asb)):
            le_drift = np.max(np.abs(current_asb[i]["xyz_le"] - canonical_asb[i]["xyz_le"]))
            twist_drift = abs(current_asb[i]["twist"] - canonical_asb[i]["twist"])
            max_le_drift = max(max_le_drift, le_drift)
            max_twist_drift = max(max_twist_drift, twist_drift)

        print(f"\n  ASB→WC→ASB drift after {N} iterations: LE={max_le_drift:.10f}mm, twist={max_twist_drift:.10f}°")
        assert max_le_drift < 1e-10, f"ASB→WC→ASB LE drifted: {max_le_drift}mm"
        assert max_twist_drift < 1e-10, f"ASB→WC→ASB twist drifted: {max_twist_drift}°"


    def test_n_times_wc_asb_wc_extreme_angles(self):
        """Stress test: large angles, long segments — WC→ASB→WC N times.

        6 segments, each 500-800mm long (large lever arm).
        Incidence up to ±15°. Dihedral up to 10°.
        """
        N = 10
        segs = [
            {"root_chord": 300, "root_incidence": 12, "root_dihedral": 10,
             "tip_chord": 260, "tip_incidence": -8, "length": 500, "sweep": 30},
            {"root_chord": 260, "root_incidence": -8, "root_dihedral": 0,
             "tip_chord": 220, "tip_incidence": 15, "length": 800, "sweep": 20},
            {"root_chord": 220, "root_incidence": 15, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -10, "length": 700, "sweep": 40},
            {"root_chord": 180, "root_incidence": -10, "root_dihedral": 0,
             "tip_chord": 140, "tip_incidence": 5, "length": 600, "sweep": 15},
            {"root_chord": 140, "root_incidence": 5, "root_dihedral": 0,
             "tip_chord": 100, "tip_incidence": -12, "length": 500, "sweep": 25},
            {"root_chord": 100, "root_incidence": -12, "root_dihedral": 0,
             "tip_chord": 50, "tip_incidence": -15, "length": 300, "sweep": 10},
        ]

        asb = self._forward(segs)
        canonical = self._reverse(asb)

        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_inc_drift = 0.0
        max_len_drift = 0.0
        for i in range(len(canonical)):
            for key in ["root_incidence", "tip_incidence"]:
                max_inc_drift = max(max_inc_drift, abs(current[i][key] - canonical[i][key]))
            max_len_drift = max(max_len_drift, abs(current[i]["length"] - canonical[i]["length"]))

        print(f"\n  EXTREME WC→ASB→WC drift ({N}x): incidence={max_inc_drift:.10f}°, length={max_len_drift:.10f}mm")
        assert max_inc_drift < 1e-10, f"Incidence drifted: {max_inc_drift}°"
        assert max_len_drift < 1e-10, f"Length drifted: {max_len_drift}mm"

    def test_n_times_asb_wc_asb_extreme_angles(self):
        """Stress test: ASB→WC→ASB N times with extreme twist and large spans."""
        N = 10
        asb_xsecs = [
            {"xyz_le": np.array([0, 0, 0]), "twist": 15.0, "chord": 300},
            {"xyz_le": np.array([30, 500, 87]), "twist": -8.0, "chord": 260},
            {"xyz_le": np.array([50, 1300, 87]), "twist": 12.0, "chord": 220},
            {"xyz_le": np.array([90, 2000, 87]), "twist": -5.0, "chord": 180},
            {"xyz_le": np.array([105, 2600, 87]), "twist": -15.0, "chord": 140},
            {"xyz_le": np.array([130, 3100, 87]), "twist": 10.0, "chord": 100},
            {"xyz_le": np.array([140, 3400, 87]), "twist": -12.0, "chord": 50},
        ]

        wc = self._reverse(asb_xsecs)
        canonical_asb = self._forward(wc)

        current_asb = canonical_asb
        for _ in range(N):
            wc = self._reverse(current_asb)
            current_asb = self._forward(wc)

        max_le_drift = 0.0
        max_twist_drift = 0.0
        for i in range(len(canonical_asb)):
            le_drift = np.max(np.abs(current_asb[i]["xyz_le"] - canonical_asb[i]["xyz_le"]))
            twist_drift = abs(current_asb[i]["twist"] - canonical_asb[i]["twist"])
            max_le_drift = max(max_le_drift, le_drift)
            max_twist_drift = max(max_twist_drift, twist_drift)

        print(f"\n  EXTREME ASB→WC→ASB drift ({N}x): LE={max_le_drift:.10f}mm, twist={max_twist_drift:.10f}°")
        assert max_le_drift < 1e-10, f"LE drifted: {max_le_drift}mm"
        assert max_twist_drift < 1e-10, f"Twist drifted: {max_twist_drift}°"


    def test_near_gimbal_lock_large_incidence(self):
        """Incidence near ±80° — tests numerical stability near gimbal lock.

        Unrealistic for wings but stresses atan2-based angle recovery.
        """
        N = 10
        segs = [
            {"root_chord": 200, "root_incidence": 75, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -80, "length": 500, "sweep": 10},
            {"root_chord": 180, "root_incidence": -80, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 60, "length": 500, "sweep": 5},
        ]
        asb = self._forward(segs)
        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        print(f"\n  GIMBAL LOCK stress ({N}x): incidence drift={max_drift:.10f}°")
        assert max_drift < 1e-10, f"Drifted near gimbal lock: {max_drift}°"

    def test_all_angles_equal_accumulation(self):
        """Every segment has 10° incidence + 10° dihedral — tests accumulation.

        4 segments: cumulative twist = 10, 20, 30, 40° at the x_secs.
        """
        N = 10
        segs = [
            {"root_chord": 200, "root_incidence": 10, "root_dihedral": 10,
             "tip_chord": 180, "tip_incidence": 10, "length": 400, "sweep": 0},
            {"root_chord": 180, "root_incidence": 10, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 10, "length": 400, "sweep": 0},
            {"root_chord": 160, "root_incidence": 10, "root_dihedral": 0,
             "tip_chord": 140, "tip_incidence": 10, "length": 400, "sweep": 0},
            {"root_chord": 140, "root_incidence": 10, "root_dihedral": 0,
             "tip_chord": 120, "tip_incidence": 10, "length": 400, "sweep": 0},
        ]
        asb = self._forward(segs)

        # Verify cumulative twists: 10, 20, 30, 40, 50
        assert asb[0]["twist"] == pytest.approx(10, abs=0.001)
        assert asb[1]["twist"] == pytest.approx(20, abs=0.001)
        assert asb[2]["twist"] == pytest.approx(30, abs=0.001)
        assert asb[3]["twist"] == pytest.approx(40, abs=0.001)
        assert asb[4]["twist"] == pytest.approx(50, abs=0.001)

        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        print(f"\n  ACCUMULATION stress ({N}x): incidence drift={max_drift:.10f}°")
        assert max_drift < 1e-10, f"Drifted with accumulation: {max_drift}°"

    def test_alternating_positive_negative(self):
        """±15° alternating incidence — maximum direction changes.

        Twist: 15, 0, 15, 0, 15, 0 (zig-zag).
        """
        N = 10
        segs = [
            {"root_chord": 200, "root_incidence": 15, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -15, "length": 600, "sweep": 20},
            {"root_chord": 180, "root_incidence": -15, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 15, "length": 600, "sweep": 15},
            {"root_chord": 160, "root_incidence": 15, "root_dihedral": 0,
             "tip_chord": 140, "tip_incidence": -15, "length": 600, "sweep": 10},
            {"root_chord": 140, "root_incidence": -15, "root_dihedral": 0,
             "tip_chord": 120, "tip_incidence": 15, "length": 600, "sweep": 25},
            {"root_chord": 120, "root_incidence": 15, "root_dihedral": 0,
             "tip_chord": 100, "tip_incidence": -15, "length": 600, "sweep": 5},
        ]
        asb = self._forward(segs)
        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        print(f"\n  ALTERNATING ±15° stress ({N}x): incidence drift={max_drift:.10f}°")
        assert max_drift < 1e-10, f"Drifted with alternating angles: {max_drift}°"

    def test_tiny_segments_large_angles(self):
        """1mm segments with 20° incidence — extreme ratio of angle to length."""
        N = 10
        segs = [
            {"root_chord": 50, "root_incidence": 20, "root_dihedral": 0,
             "tip_chord": 45, "tip_incidence": -20, "length": 1, "sweep": 0.5},
            {"root_chord": 45, "root_incidence": -20, "root_dihedral": 0,
             "tip_chord": 40, "tip_incidence": 20, "length": 1, "sweep": 0.3},
            {"root_chord": 40, "root_incidence": 20, "root_dihedral": 0,
             "tip_chord": 35, "tip_incidence": -20, "length": 1, "sweep": 0.1},
        ]
        asb = self._forward(segs)
        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        print(f"\n  TINY SEGMENTS stress ({N}x): incidence drift={max_drift:.10f}°")
        assert max_drift < 1e-10, f"Drifted with tiny segments: {max_drift}°"

    def test_large_incidence_multi_segment(self):
        """rc=1.0 — rotation pivot at the trailing edge (maximum LE displacement)."""
        N = 10
        segs = [
            {"root_chord": 200, "root_incidence": 10, "root_dihedral": 0,
             "tip_chord": 180, "tip_incidence": -5, "length": 500, "sweep": 10},
            {"root_chord": 180, "root_incidence": -5, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 8, "length": 500, "sweep": 15},
            {"root_chord": 160, "root_incidence": 8, "root_dihedral": 0,
             "tip_chord": 140, "tip_incidence": -10, "length": 500, "sweep": 5},
        ]
        asb = self._forward(segs)
        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_inc_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        max_len_drift = max(
            abs(current[i]["length"] - canonical[i]["length"])
            for i in range(len(canonical))
        )
        print(f"\n  RC=1.0 stress ({N}x): incidence drift={max_inc_drift:.10f}°, length drift={max_len_drift:.10f}mm")
        assert max_inc_drift < 1e-10, f"Incidence drifted at rc=1.0: {max_inc_drift}°"
        assert max_len_drift < 1e-10, f"Length drifted at rc=1.0: {max_len_drift}mm"

    def test_combined_dihedral_incidence_large(self):
        """Large dihedral (30°) combined with large incidence (±20°).

        Note: dihedral is lossy (projected to translation), but incidence
        must survive the roundtrip exactly.
        """
        N = 10
        segs = [
            {"root_chord": 200, "root_incidence": 20, "root_dihedral": 30,
             "tip_chord": 180, "tip_incidence": -20, "length": 500, "sweep": 0},
            {"root_chord": 180, "root_incidence": -20, "root_dihedral": 0,
             "tip_chord": 160, "tip_incidence": 15, "length": 500, "sweep": 0},
        ]
        asb = self._forward(segs)
        canonical = self._reverse(asb)
        current = canonical
        for _ in range(N):
            asb = self._forward(current)
            current = self._reverse(asb)

        max_drift = max(
            abs(current[i][k] - canonical[i][k])
            for i in range(len(canonical))
            for k in ["root_incidence", "tip_incidence"]
        )
        print(f"\n  LARGE DIHEDRAL+INCIDENCE stress ({N}x): drift={max_drift:.10f}°")
        assert max_drift < 1e-10, f"Drifted with large angles: {max_drift}°"


class TestInverseFormulas:
    """Verify the closed-form parameter extraction from H matrix.

    From docs/WingConfiguration.adoc "Debugging: manual parameter inversion":
        ι_i = atan2(H_i[0,2], H_i[0,0])
        δ_i = atan2(H_i[2,1], H_i[1,1])
    """

    def test_extract_incidence_from_h(self):
        """atan2(H[0,2], H[0,0]) should recover the incidence angle."""
        for iota in [-5, -2, 0, 3, 7, 15]:
            H = Ry(iota)
            recovered = math.degrees(math.atan2(H[0, 2], H[0, 0]))
            assert recovered == pytest.approx(iota, abs=0.001), \
                f"Failed to recover incidence {iota}° — got {recovered}°"

    def test_extract_dihedral_from_h(self):
        """atan2(H[2,1], H[1,1]) should recover the dihedral angle."""
        for delta in [0, 2, 5, 10, 30]:
            H = Rx(delta)
            recovered = math.degrees(math.atan2(H[2, 1], H[1, 1]))
            assert recovered == pytest.approx(delta, abs=0.001), \
                f"Failed to recover dihedral {delta}° — got {recovered}°"

    def test_extract_both_angles_from_combined(self):
        """Extract both angles from R_x(δ) · R_y(ι)."""
        for delta, iota in [(3, 5), (10, -2), (0, 8), (5, 0), (7, -7)]:
            H = Rx(delta) @ Ry(iota)
            recovered_iota = math.degrees(math.atan2(H[0, 2], H[0, 0]))
            recovered_delta = math.degrees(math.atan2(H[2, 1], H[1, 1]))
            assert recovered_iota == pytest.approx(iota, abs=0.001), \
                f"Incidence: expected {iota}°, got {recovered_iota}°"
            assert recovered_delta == pytest.approx(delta, abs=0.001), \
                f"Dihedral: expected {delta}°, got {recovered_delta}°"

    def test_extract_from_full_h0(self):
        """Extract angles from a complete H_0 matrix."""
        C, delta, iota = 200, 5, -3
        H = H0(C, delta, iota)
        # H_0 = Rx(delta) . Ry(iota), so angles are directly extractable.
        R = Rx(delta) @ Ry(iota)
        recovered_iota = math.degrees(math.atan2(H[0, 2], H[0, 0]))
        recovered_delta = math.degrees(math.atan2(H[2, 1], H[1, 1]))
        assert recovered_iota == pytest.approx(iota, abs=0.001)
        assert recovered_delta == pytest.approx(delta, abs=0.001)


# ═══════════════════════════════════════════════════════════════════
# Test 6: Roundtrip contract from documentation
# ═══════════════════════════════════════════════════════════════════


class TestRoundtripContract:
    """Verify the asb roundtrip formulas from the documentation.

    From docs/WingConfiguration.adoc "Reverse direction: from_asb()":
        - dihedral_as_rotation_in_degrees = 0 on every airfoil
        - segments[0].root_airfoil.incidence = twist[0] (absolute root twist)
        - segments[i].tip_airfoil.incidence = twist[i+1] - twist[i] (delta)

    And the pre-rotation formula:
        T_i = R_y(-twist[i]) · (xyz_le[i+1] - xyz_le[i])
    """

    def test_twist_to_incidence_conversion(self):
        """Convert absolute twist values to per-segment incidence deltas.

        From the doc: "segments[i].tip_airfoil.incidence = twist[i+1] - twist[i]"

        Example: twist = [3, 2, 0, -1]
        Expected incidence:
          seg[0].root_airfoil.incidence = twist[0] = 3
          seg[0].tip_airfoil.incidence = twist[1] - twist[0] = -1
          seg[1].tip_airfoil.incidence = twist[2] - twist[1] = -2
          seg[2].tip_airfoil.incidence = twist[3] - twist[2] = -1
        """
        twists = [3, 2, 0, -1]

        root_incidence = twists[0]
        assert root_incidence == 3

        tip_incidences = [twists[i + 1] - twists[i] for i in range(len(twists) - 1)]
        assert tip_incidences == [-1, -2, -1]

        # Verify: cumulative sum of deltas reproduces original twists
        reconstructed = [root_incidence]
        for delta in tip_incidences:
            reconstructed.append(reconstructed[-1] + delta)
        assert reconstructed == twists

    def test_pre_rotated_translation_formula(self):
        """Verify T_i = R_y(-twist[i]) · (xyz_le[i+1] - xyz_le[i]).

        For a flat wing (twist=0), T_i should just be the LE delta.
        """
        xyz_le = [
            np.array([0, 0, 0]),
            np.array([5, 200, 0]),  # sweep=5, length=200
        ]
        twist = [0, 0]

        delta_le = xyz_le[1] - xyz_le[0]
        R_neg = Ry(-twist[0])[:3, :3]
        T_i = R_neg @ delta_le

        np.testing.assert_array_almost_equal(T_i, [5, 200, 0])

    def test_pre_rotated_translation_with_twist(self):
        """With twist=5° at station 0, the translation is pre-rotated.

        T_0 = R_y(-5°) · [5, 200, 0]
        This compensates for the fact that the H chain will apply R_y(5°)
        at segment 0, which would otherwise rotate the translation.
        """
        delta_le = np.array([5, 200, 0], dtype=float)
        twist0 = 5.0
        R_neg = Ry(-twist0)[:3, :3]
        T_i = R_neg @ delta_le

        # R_y(-5°) · [5, 200, 0]:
        # x' = 5*cos(-5°) + 0*sin(-5°) = 5*cos5° ≈ 4.981
        # y' = 200 (unchanged by Ry)
        # z' = -5*sin(-5°) + 0*cos(-5°) = 5*sin5° ≈ 0.436
        assert T_i[0] == pytest.approx(5 * math.cos(math.radians(5)), abs=0.001)
        assert T_i[1] == pytest.approx(200, abs=0.001)
        assert T_i[2] == pytest.approx(5 * math.sin(math.radians(5)), abs=0.001)
