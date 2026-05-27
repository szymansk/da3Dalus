"""gh-753 — augment wing xsecs between same-airfoil anchors.

The augmentation runs inside the WING handler after the original
xsec loop, before the Geom XForm pass. It inserts
``_N_INTERP_PER_PAIR`` interpolated xsecs between consecutive
anchor pairs that share the same ``airfoil`` reference. Pairs
with different airfoils are skipped so the user retains full
profile-editability for Re-number scaling workflows.

These tests pin three contract points:

1. Same-airfoil pair → ``N_INTERP`` inserts; NACA name preserved.
2. Different-airfoil pair → 0 inserts (user-edit-ability).
3. Spitfire-style 4-anchor wing → 4 + 4·3 = 16 total xsecs;
   xyz_le values follow VSP's parametric surface (verified
   against the stub VSP's ``CompPnt01`` return values).
"""

from __future__ import annotations

import math

import pytest

from app.converters.openvsp_importer import ImportContext
from app.converters.openvsp_wing_handler import (
    _N_INTERP_PER_PAIR,
    _W_LE,
    _W_TE,
    _augment_same_airfoil_pairs,
    _chord_from_le_te,
    _sample_le_te_at,
)
from app.schemas.aeroplaneschema import WingXSecSchema


def _ctx() -> ImportContext:
    """Fresh ImportContext for each test — collects warnings."""
    return ImportContext()


# ---------------------------------------------------------------------------
# VSP stub — minimal CompPnt01 returning a deterministic
# (LE, TE) pair as a function of (u, w).
# ---------------------------------------------------------------------------


class _Pnt:
    """Minimal stand-in for VSP's ``vec3d`` — only ``x()``, ``y()``,
    ``z()`` are exercised by the handler."""

    def __init__(self, x: float, y: float, z: float):
        self._x, self._y, self._z = x, y, z

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y

    def z(self) -> float:
        return self._z


def _ellipse_vsp(half_span: float = 6.0, root_chord: float = 2.0):
    """Build a VSP stub whose CompPnt01 traces an elliptical
    planform (Spitfire-style). For spanwise parameter ``u`` ∈ [0, 1]:

      y = half_span · u
      chord(u) = root_chord · sqrt(1 - u²)     # ellipse
      LE.x = -chord(u)/2,  TE.x = +chord(u)/2
      LE.z = TE.z = 0      # no twist

    No XForm — caller assumes body frame.
    """

    class _Stub:
        @staticmethod
        def CompPnt01(_gid: str, _surf: int, u: float, w: float) -> _Pnt:
            y = half_span * u
            chord = root_chord * math.sqrt(max(0.0, 1.0 - u * u))
            if abs(w - _W_LE) < 1e-9:
                return _Pnt(-chord / 2.0, y, 0.0)
            if abs(w - _W_TE) < 1e-9:
                return _Pnt(+chord / 2.0, y, 0.0)
            # Other w values not exercised in tests; return LE.
            return _Pnt(-chord / 2.0, y, 0.0)

    return _Stub()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _xsec(*, airfoil: str, xyz_le=(0.0, 0.0, 0.0), chord=1.0, twist=0.0, t=None):
    """Compact WingXSecSchema constructor for tests."""
    return WingXSecSchema(
        xyz_le=list(xyz_le),
        chord=chord,
        twist=twist,
        airfoil=airfoil,
        x_sec_type=t,
    )


# ---------------------------------------------------------------------------
# Chord + twist derivation
# ---------------------------------------------------------------------------


class TestChordFromLeTe:
    """``_chord_from_le_te`` returns only the planform chord. Twist is
    NOT derived from VSP body-frame LE/TE (would mix dihedral and
    section-Z stagger into twist — PR #754 review #1). The augmenter
    interpolates twist linearly between anchor twists instead — see
    ``TestTwistInterpolation`` below."""

    def test_horizontal_chord(self):
        chord = _chord_from_le_te((0.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        assert chord == pytest.approx(1.0)

    def test_chord_is_3d_distance(self):
        # LE at origin, TE 1 m forward + 0.1 m up — chord is the
        # straight-line distance, includes the vertical component.
        chord = _chord_from_le_te((0.0, 0.0, 0.1), (1.0, 0.0, 0.0))
        assert chord == pytest.approx(math.sqrt(1.01), rel=1e-9)

    def test_degenerate_chord_returns_zero(self):
        chord = _chord_from_le_te((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
        assert chord == 0.0


# ---------------------------------------------------------------------------
# Sample LE / TE at u
# ---------------------------------------------------------------------------


class TestSampleLeTeAt:
    def test_returns_tuples_in_meters(self):
        vsp = _ellipse_vsp()
        le, te = _sample_le_te_at(vsp, "wing-gid", u=0.0)
        # At u=0 (root), chord = root_chord = 2.0
        assert le == (-1.0, 0.0, 0.0)
        assert te == (1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# Augmentation contract
# ---------------------------------------------------------------------------


class TestSameAirfoilPairAugmentation:
    """gh-753 happy path: two anchors with the same airfoil get
    ``_N_INTERP_PER_PAIR`` interpolated xsecs between them."""

    def test_inserts_n_interp_xsecs(self):
        anchors = [
            _xsec(airfoil="naca2412", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2412", xyz_le=(0.0, 6.0, 0.0), chord=0.0, t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # 2 anchors + N inserts = 2 + 4 = 6
        assert len(out) == 2 + _N_INTERP_PER_PAIR

    def test_preserves_naca_name_on_inserts(self):
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # All inserts inherit the anchor's airfoil — never a generated
        # ``vsp_imported_*.dat`` for same-airfoil paths.
        for xs in out[1:-1]:
            assert xs.airfoil == "naca2412"

    def test_inserts_carry_segment_type(self):
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # The inserts sit between root and the terminal xsec, so they
        # all carry x_sec_type="segment" (intermediate).
        for xs in out[1:-1]:
            assert xs.x_sec_type == "segment"

    def test_inserts_follow_vsp_spline_not_linear_interp(self):
        """For a Spitfire-style elliptical wing, the chord at u=0.5
        is ``root_chord * sqrt(1 - 0.5²) = 1.732`` (≠ linear midpoint
        between root_chord=2.0 and tip_chord=0.0 which would be 1.0).
        Tests the augmentation reads the real VSP spline, not a
        straight interpolation between the anchors.
        """
        anchors = [
            _xsec(airfoil="naca2412", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2412", xyz_le=(0.0, 6.0, 0.0), chord=0.0, t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # The middle insert (k=2) sits at u = 0 + 2 · (1/(4+1)) = 0.4.
        # On the elliptical surface, chord(0.4) = 2 · sqrt(1 - 0.16) ≈ 1.833.
        # Linear interpolation between anchors would give 2.0·(1-0.4)=1.2.
        # Pin the spline-following value, not the linear approximation.
        # out[0]=root, out[1..4]=inserts at u=0.2/0.4/0.6/0.8, out[5]=tip.
        # The insert at u=0.4 is out[2]; chord(0.4) = 2·sqrt(1-0.16)
        # ≈ 1.833 on the ellipse, NOT 1.2 which is what linear
        # interpolation between root (2.0) and tip (0.0) would give.
        u04 = out[2]
        expected_chord = 2.0 * math.sqrt(1.0 - 0.4 * 0.4)
        assert u04.chord == pytest.approx(expected_chord, rel=1e-6)


class TestDifferentAirfoilPairSkipped:
    """gh-753 user constraint: pairs with different airfoils are
    skipped so the user can swap profiles for Re-number scaling
    at the anchors without dealing with morphed-profile blobs in
    between."""

    def test_zero_inserts_between_different_airfoils(self):
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca6409", t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # 2 anchors, no inserts.
        assert len(out) == 2
        assert out[0].airfoil == "naca2412"
        assert out[1].airfoil == "naca6409"

    def test_mixed_wing_augments_only_same_airfoil_segments(self):
        """A three-anchor wing where root→mid share airfoil and mid→tip
        differ should get ``N_INTERP`` inserts in the first segment
        and zero in the second."""
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t="segment"),
            _xsec(airfoil="naca6409", t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # 3 anchors + N inserts (first segment only)
        assert len(out) == 3 + _N_INTERP_PER_PAIR


class TestSpitfireAnchorCount:
    """Pin the Spitfire scenario from the user's screenshot: 4 anchor
    xsecs (all NACA 2213 or similar, same airfoil throughout) → 4 +
    3·N inserts = 16 total xsecs in the schema."""

    def test_four_anchors_same_airfoil_gives_sixteen_xsecs(self):
        anchors = [
            _xsec(airfoil="naca2213", t="root"),
            _xsec(airfoil="naca2213", t="segment"),
            _xsec(airfoil="naca2213", t="segment"),
            _xsec(airfoil="naca2213", t=None),
        ]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # 4 anchors + 3 pairs · N inserts each = 4 + 12 = 16
        assert len(out) == 4 + 3 * _N_INTERP_PER_PAIR


class TestTwistInterpolation:
    """PR #754 review #1: twist must NOT be derived from body-frame
    LE/TE (which would mix dihedral and section-Z stagger into a
    bogus twist value, especially bad for VTPs). Instead, augmenter
    interpolates ``twist`` linearly between the bracketing anchor
    twists at the fractional position ``k / (N_INTERP + 1)``."""

    def test_interpolates_twist_between_anchors(self):
        # Root twist = 0°, tip twist = -4° → 4 inserts at fractional
        # positions 0.2/0.4/0.6/0.8 → twists ≈ -0.8/-1.6/-2.4/-3.2°.
        anchors = [
            _xsec(airfoil="naca2412", twist=0.0, t="root"),
            _xsec(airfoil="naca2412", twist=-4.0, t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing"
        )
        inserts = out[1:-1]
        expected = [-0.8, -1.6, -2.4, -3.2]
        for ins, exp in zip(inserts, expected):
            assert ins.twist == pytest.approx(exp, rel=1e-9)

    def test_zero_twist_anchors_yield_zero_twist_inserts(self):
        # All-zero twist (Spitfire, no washout) → every insert is 0.
        # Critical: must NOT pick up dihedral from body-frame LE/TE
        # via a geometric atan2 — even with a dihedral-aware stub
        # the augmenter sees twist=0 on both anchors and interpolates
        # to 0 throughout.
        anchors = [
            _xsec(airfoil="naca2412", twist=0.0, t="root"),
            _xsec(airfoil="naca2412", twist=0.0, t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing"
        )
        for ins in out[1:-1]:
            assert ins.twist == 0.0

    def test_dihedral_does_not_leak_into_twist(self):
        """The PR #754 review specifically called out VTPs and
        dihedral wings: body-frame LE/TE has ``le.z != te.z`` due
        to dihedral or vertical-tail rotation, which a geometric
        ``atan2`` twist derivation would interpret as twist. The
        augmenter must ignore the body-frame geometry and use anchor
        twists exclusively."""

        # Stub whose LE is 0.5 m above the chord plane (extreme
        # dihedral) — would produce ~27° false twist if augmenter
        # used atan2.
        class _DihedralStub:
            @staticmethod
            def CompPnt01(_gid, _surf, u, w):
                y = 6.0 * u
                chord = 2.0 * math.sqrt(max(0.0, 1.0 - u * u))
                # LE.z > TE.z by 0.5 m everywhere (artificial)
                if abs(w - _W_LE) < 1e-9:
                    return _Pnt(-chord / 2.0, y, 0.5)
                return _Pnt(chord / 2.0, y, 0.0)

        anchors = [
            _xsec(airfoil="naca2412", twist=0.0, t="root"),
            _xsec(airfoil="naca2412", twist=0.0, t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _DihedralStub(), "wing-gid", _ctx(), "wing"
        )
        # Anchor twists are 0 → every insert twist must be 0 even
        # though the body-frame LE/TE has a 0.5 m vertical offset.
        for ins in out[1:-1]:
            assert ins.twist == 0.0, (
                f"dihedral leaked into twist: {ins.twist}° — augmenter "
                "must use anchor twists, not body-frame atan2"
            )


class TestLossyWarning:
    """PR #754 review #2: if ≥1 expected insert silently fails,
    the augmenter must emit an info-warning via ``ctx`` so the user
    can correlate the visual symptom (still-polygonal wing) with a
    real importer event in the import report."""

    def test_emits_warning_when_all_inserts_fail(self):
        """A VSP stub whose ``CompPnt01`` raises for every u causes
        all 4 inserts to silently fail. Pre-fix, the wing rendered
        polygonal without any user-visible signal. Post-fix, a single
        info-warning surfaces the count diff."""

        class _AlwaysRaises:
            @staticmethod
            def CompPnt01(_gid, _surf, _u, _w):
                raise RuntimeError("synthetic VSP failure")

        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _AlwaysRaises(), "wing-gid", ctx, "main_wing"
        )
        # No inserts succeeded → 2 anchors only.
        assert len(out) == 2
        # Exactly one info-warning emitted with the count diff.
        info_warnings = [
            w for w in ctx.warnings if w.severity == "info" and "gh-753" in w.reason
        ]
        assert len(info_warnings) == 1
        assert info_warnings[0].component_name == "main_wing"
        assert "0/4" in info_warnings[0].reason

    def test_emits_warning_when_some_inserts_fail(self):
        """Partial failure (1 of 4 u-samples raises) → warning
        emitted with the partial count so the user sees the wing
        is degraded but not entirely missing intermediates."""

        class _FlakyAtMidU:
            @staticmethod
            def CompPnt01(_gid, _surf, u, w):
                if 0.35 < u < 0.45:  # k=2 only
                    raise RuntimeError("synthetic mid-u failure")
                chord = 2.0 * math.sqrt(max(0.0, 1.0 - u * u))
                if abs(w - _W_LE) < 1e-9:
                    return _Pnt(-chord / 2.0, 6.0 * u, 0.0)
                return _Pnt(chord / 2.0, 6.0 * u, 0.0)

        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _FlakyAtMidU(), "wing-gid", ctx, "main_wing"
        )
        # 3 successful inserts + 2 anchors = 5
        assert len(out) == 5
        info_warnings = [w for w in ctx.warnings if "gh-753" in w.reason]
        assert len(info_warnings) == 1
        assert "3/4" in info_warnings[0].reason

    def test_no_warning_when_all_inserts_succeed(self):
        """Happy path: all inserts succeed → no warning (would be
        noise for healthy imports)."""
        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        _augment_same_airfoil_pairs(
            anchors, _ellipse_vsp(), "wing-gid", ctx, "main_wing"
        )
        info_warnings = [w for w in ctx.warnings if "gh-753" in w.reason]
        assert info_warnings == []


class TestDegenerateInputs:
    def test_single_xsec_passthrough(self):
        anchors = [_xsec(airfoil="naca2412", t="root")]
        out = _augment_same_airfoil_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        assert out == anchors

    def test_no_comppnt01_passes_through_unchanged(self):
        """Defensive: very old VSP builds or test stubs without
        CompPnt01 must produce the original anchor list (no
        AttributeError)."""

        class _StubWithoutCompPnt:
            pass  # no CompPnt01 attribute

        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _StubWithoutCompPnt(), "wing-gid", _ctx(), "wing"
        )
        assert out == anchors

    def test_comppnt01_raises_skips_that_u_only(self):
        """If CompPnt01 raises at a specific u (e.g. one VSP version
        with a edge-case bug), the augmenter skips that u and
        continues with the rest. The renderer just sees one fewer
        xsec, not a crashed import."""

        class _FlakyVsp:
            def __init__(self):
                self.calls = 0

            def CompPnt01(self, _gid, _surf, u, w):
                self.calls += 1
                if 0.35 < u < 0.45:
                    raise RuntimeError("VSP edge-case at this u")
                # Otherwise behave like the ellipse stub.
                chord = 2.0 * math.sqrt(max(0.0, 1.0 - u * u))
                if abs(w - _W_LE) < 1e-9:
                    return _Pnt(-chord / 2.0, 6.0 * u, 0.0)
                return _Pnt(chord / 2.0, 6.0 * u, 0.0)

        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_same_airfoil_pairs(
            anchors, _FlakyVsp(), "wing-gid", _ctx(), "wing"
        )
        # The u≈0.4 insert is skipped; the other 3 succeed.
        # Total: 2 anchors + 3 successful inserts = 5
        assert len(out) == 5
