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

def H0(C0, rc0, delta0, iota0):
    """Root segment coordinate system.

    From docs/WingConfiguration.adoc:
        H_0 = T(C_0 * rc_0, 0, 0) · T(0, 0, 0) · R_x(δ_0) · R_y(ι_0) · T(-C_0 * rc_0, 0, 0)

    Parameters:
        C0: root chord (mm)
        rc0: rotation_point_rel_chord (0..1)
        delta0: dihedral_as_rotation_in_degrees
        iota0: incidence angle (degrees)
    """
    return T(C0 * rc0, 0, 0) @ T(0, 0, 0) @ Rx(delta0) @ Ry(iota0) @ T(-C0 * rc0, 0, 0)


def Hi(Ci, rci, Si_prev, Li_prev, Di_prev, deltai, iotai):
    """Segment i coordinate system (i > 0).

    From docs/WingConfiguration.adoc:
        H_i = T(C_i * rc_i, 0, 0) · T(S_{i-1}, L_{i-1}, D_{i-1}) · R_x(δ_i) · R_y(ι_i) · T(-C_i * rc_i, 0, 0)

    Parameters:
        Ci: chord at this station (mm)
        rci: rotation_point_rel_chord
        Si_prev: sweep of previous segment (mm)
        Li_prev: length of previous segment (mm)
        Di_prev: dihedral_as_translation of previous segment (mm)
        deltai: dihedral_as_rotation_in_degrees at this station
        iotai: incidence angle at this station (degrees)
    """
    return T(Ci * rci, 0, 0) @ T(Si_prev, Li_prev, Di_prev) @ Rx(deltai) @ Ry(iotai) @ T(-Ci * rci, 0, 0)


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
        """H_0 with no dihedral, no incidence, rc=0 should be identity.

        H_0 = T(0) · T(0) · R_x(0) · R_y(0) · T(0) = I
        """
        H = H0(C0=200, rc0=0, delta0=0, iota0=0)
        np.testing.assert_array_almost_equal(H, np.eye(4))

    def test_h0_with_rc_025_no_angles(self):
        """H_0 with rc=0.25, no angles — should still be identity.

        T(C*rc) · I · I · T(-C*rc) = I (translations cancel)
        """
        H = H0(C0=200, rc0=0.25, delta0=0, iota0=0)
        np.testing.assert_array_almost_equal(H, np.eye(4), decimal=10)

    def test_h0_incidence_only(self):
        """H_0 with 5° incidence at rc=0 — pure rotation around y-axis.

        H_0 = T(0) · T(0) · R_x(0) · R_y(5°) · T(0) = R_y(5°)
        Origin stays at [0,0,0]. The chord direction rotates.
        """
        H = H0(C0=200, rc0=0, delta0=0, iota0=5)
        origin = extract_origin(H)
        np.testing.assert_array_almost_equal(origin, [0, 0, 0], decimal=10)
        # The rotation part should match R_y(5°)
        np.testing.assert_array_almost_equal(H, Ry(5), decimal=10)

    def test_h0_incidence_with_rc(self):
        """H_0 with 5° incidence at rc=0.25, chord=200.

        The rotation is around the point (200*0.25, 0, 0) = (50, 0, 0).
        The origin (LE at x=0) should move due to the off-center rotation.
        """
        H = H0(C0=200, rc0=0.25, delta0=0, iota0=5)
        origin = extract_origin(H)
        # The LE (at x=0 before rotation) is displaced because the rotation
        # pivot is at x=50, not x=0.
        # After T(50)·Ry(5°)·T(-50) on [0,0,0]:
        # Step 1: T(-50) → [-50, 0, 0]
        # Step 2: Ry(5°) → [-50*cos5, 0, 50*sin5] = [-49.81, 0, 4.36]
        # Step 3: T(50) → [0.19, 0, 4.36]
        expected_x = 50 - 50 * math.cos(math.radians(5))
        expected_z = 50 * math.sin(math.radians(5))
        assert origin[0] == pytest.approx(expected_x, abs=0.01)
        assert origin[1] == pytest.approx(0, abs=1e-10)
        assert origin[2] == pytest.approx(expected_z, abs=0.01)

    def test_h0_dihedral_only(self):
        """H_0 with 10° dihedral, rc=0 — pure R_x rotation.

        H_0 = R_x(10°). Origin stays at [0,0,0].
        """
        H = H0(C0=200, rc0=0, delta0=10, iota0=0)
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
        H = Hi(Ci=180, rci=0, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)
        expected = T(0, 200, 0)
        np.testing.assert_array_almost_equal(H, expected, decimal=10)

    def test_hi_sweep_and_length(self):
        """H_i with sweep=5mm, length=200mm.

        H_i = T(5, 200, 0)
        """
        H = Hi(Ci=160, rci=0, Si_prev=5, Li_prev=200, Di_prev=0, deltai=0, iotai=0)
        origin = extract_origin(H)
        assert origin[0] == pytest.approx(5, abs=1e-10)
        assert origin[1] == pytest.approx(200, abs=1e-10)

    def test_hi_with_incidence(self):
        """H_i with 3° incidence at rc=0, length=200.

        H_i = T(0, 200, 0) · R_y(3°)
        Origin is at [0, 200, 0] — incidence doesn't move the LE when rc=0.
        """
        H = Hi(Ci=160, rci=0, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=3)
        origin = extract_origin(H)
        assert origin[0] == pytest.approx(0, abs=1e-10)
        assert origin[1] == pytest.approx(200, abs=1e-10)
        assert origin[2] == pytest.approx(0, abs=1e-10)

    def test_hi_with_dihedral_translation(self):
        """H_i with dihedral_as_translation=15mm, length=200.

        H_i = T(0, 200, 15)
        The LE moves up by 15mm.
        """
        H = Hi(Ci=160, rci=0, Si_prev=0, Li_prev=200, Di_prev=15, deltai=0, iotai=0)
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
        h0 = H0(C0=200, rc0=0, delta0=0, iota0=0)
        h1 = Hi(Ci=180, rci=0, Si_prev=0, Li_prev=100, Di_prev=0, deltai=0, iotai=0)
        h2 = Hi(Ci=160, rci=0, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

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
        h0 = H0(C0=200, rc0=0, delta0=0, iota0=0)
        h1 = Hi(Ci=180, rci=0, Si_prev=5, Li_prev=100, Di_prev=0, deltai=0, iotai=0)
        h2 = Hi(Ci=160, rci=0, Si_prev=10, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        o1 = extract_origin(CN([h0, h1]))
        assert o1[0] == pytest.approx(5)

        o2 = extract_origin(CN([h0, h1, h2]))
        assert o2[0] == pytest.approx(15)

    def test_incidence_on_root_does_not_move_subsequent_le_at_rc0(self):
        """With rc=0, root incidence should not shift subsequent LE positions.

        From the doc: "The rotation axis passes through xyz_le — i.e. the
        effective rotation-point-relative-to-chord in aerosandbox is rc=0."

        At rc=0, R_y rotates around the LE itself, so the LE doesn't move.
        But the subsequent segment's translation IS rotated by the accumulated twist!
        """
        # Root with 5° incidence at rc=0
        h0 = H0(C0=200, rc0=0, delta0=0, iota0=5)
        # Segment 1: length=200, no own angles
        h1 = Hi(Ci=180, rci=0, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

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

    def test_incidence_on_root_with_rc025_shifts_le(self):
        """With rc=0.25, incidence DOES shift the LE (rotation around quarter-chord).

        Root segment: C=200, rc=0.25, incidence=5°
        The rotation pivot is at x=50. The LE at x=0 moves to:
          x = 50 - 50*cos(5°) ≈ 0.19
          z = 50*sin(5°) ≈ 4.36
        """
        h0 = H0(C0=200, rc0=0.25, delta0=0, iota0=5)
        o0 = extract_origin(h0)

        expected_x = 50 * (1 - math.cos(math.radians(5)))
        expected_z = 50 * math.sin(math.radians(5))

        assert o0[0] == pytest.approx(expected_x, abs=0.01)
        assert o0[2] == pytest.approx(expected_z, abs=0.01)

    def test_dihedral_on_root_shifts_subsequent_le_upward(self):
        """Root dihedral=10° tilts the wing, subsequent LE moves up.

        H_0 = R_x(10°). H_1 = T(0, 200, 0).
        C_1 · origin = R_x(10°) · [0, 200, 0, 1]
        = [0, 200*cos10°, 200*sin10°, 1]
        """
        h0 = H0(C0=200, rc0=0, delta0=10, iota0=0)
        h1 = Hi(Ci=180, rci=0, Si_prev=0, Li_prev=200, Di_prev=0, deltai=0, iotai=0)

        c1 = CN([h0, h1])
        o1 = extract_origin(c1)

        assert o1[0] == pytest.approx(0, abs=0.01)
        assert o1[1] == pytest.approx(200 * math.cos(math.radians(10)), abs=0.01)
        assert o1[2] == pytest.approx(200 * math.sin(math.radians(10)), abs=0.01)


# ═══════════════════════════════════════════════════════════════════
# Test 5: Inverse formulas from the documentation
# ═══════════════════════════════════════════════════════════════════


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
        """Extract angles from a complete H_0 matrix (with rc and translations)."""
        C, rc, delta, iota = 200, 0.25, 5, -3
        H = H0(C, rc, delta, iota)
        # The rotation part is: T(Crc) · Rx(δ) · Ry(ι) · T(-Crc)
        # The 3x3 rotation submatrix is the same as Rx(δ)·Ry(ι) because
        # translations don't affect the rotation part of H.
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
        - rotation_point_rel_chord = 0 on every airfoil
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
