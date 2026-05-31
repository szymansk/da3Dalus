"""Wing xsec augmentation (gh-753 → gh-796 → gh-800).

The augmentation runs inside the WING handler after the original xsec
loop, before the Geom XForm pass. It inserts interpolated xsecs between
**every** consecutive anchor pair, with positions chosen
**curvature-adaptively** (gh-800): the pair's u-range is bisected and an
insert is added wherever the VSP loft deviates from the straight
anchor→anchor line by more than ``_AUGMENT_TOL_REL`` of the chord —
dense where the spline curves (elliptical tip, gull bend), ~none where
it is straight, capped at ``2**_AUGMENT_MAX_DEPTH - 1`` per pair.

Insert airfoils (gh-796): same-airfoil pairs inherit the NACA name;
differing-airfoil pairs get a Kulfan-morphed profile (nearest-anchor
fallback). Inserts follow VSP's parametric surface via ``CompPnt01``,
not a linear interpolation. Twist is linearly interpolated between the
bracketing anchor twists at each insert's spanwise fraction.
"""

from __future__ import annotations

import math

import pytest

from app.converters.openvsp_importer import ImportContext
from app.converters.openvsp_wing_handler import (
    _AUGMENT_MAX_DEPTH,
    _AUGMENT_TOL_REL,
    _OUTCOME_DEDUPED,
    _W_LE,
    _W_TE,
    _adaptive_u_fractions,
    _anchor_u_position,
    _augment_xsec_pairs,
    _chord_from_le_te,
    _find_cap_safe_u_max,
    _sample_le_te_at,
    _try_emit_one_insert,
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
    adaptively-placed interpolated xsecs between them; count is
    curvature-driven and bounded by ``2**_AUGMENT_MAX_DEPTH - 1`` per
    pair; the NACA name is preserved on every insert."""

    def test_inserts_some_xsecs_for_curved_pair(self):
        anchors = [
            _xsec(airfoil="naca2412", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2412", xyz_le=(0.0, 6.0, 0.0), chord=0.0, t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # gh-800: the elliptical pair curves → adaptive inserts are added
        # (count is curvature-driven, not a fixed 4), capped per pair.
        assert 2 < len(out) <= 2 + (2**_AUGMENT_MAX_DEPTH - 1)

    def test_preserves_naca_name_on_inserts(self):
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # All inserts inherit the anchor's airfoil — never a generated
        # ``vsp_imported_*.dat`` for same-airfoil paths.
        for xs in out[1:-1]:
            assert xs.airfoil == "naca2412"

    def test_inserts_carry_segment_type(self):
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # The inserts sit between root and the terminal xsec, so they
        # all carry x_sec_type="segment" (intermediate).
        for xs in out[1:-1]:
            assert xs.x_sec_type == "segment"

    def test_inserts_follow_vsp_spline_not_linear_interp(self):
        """Every insert's chord follows the real elliptical surface, not a
        straight interpolation between the anchors. The ellipse stub has
        ``chord(u) = 2·sqrt(1 - u²)`` with ``u = y / half_span`` — so each
        insert's chord must match the ellipse at its own y (≠ linear
        ``2·(1 - u)``)."""
        half_span = 6.0
        anchors = [
            _xsec(airfoil="naca2412", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2412", xyz_le=(0.0, half_span, 0.0), chord=0.0, t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        inserts = out[1:-1]
        assert inserts  # the curved pair produced inserts
        for ins in inserts:
            u = ins.xyz_le[1] / half_span
            ellipse_chord = 2.0 * math.sqrt(max(0.0, 1.0 - u * u))
            linear_chord = 2.0 * (1.0 - u)
            assert ins.chord == pytest.approx(ellipse_chord, rel=1e-6)
            # and meaningfully off the linear approximation (except near ends)
            if 0.1 < u < 0.95:
                assert abs(ins.chord - linear_chord) > 1e-3


class TestDifferentAirfoilPairMorphed:
    """gh-796: pairs with DIFFERENT airfoils are now augmented too — each
    insert carries a morphed profile (a content-hash ``vsp_morph_*.dat``).
    Morphing is mocked here to keep the test CAD-free and deterministic;
    the real Kulfan morph is exercised in test_openvsp_airfoil_hash_morph.py.
    """

    def test_inserts_between_different_airfoils_carry_morphed_profile(self, monkeypatch):
        from app.converters import openvsp_airfoil

        calls: list[tuple[str, str]] = []

        def _fake_morph(a, b, t):
            calls.append((a, b))
            return "./components/airfoils/vsp_morph_DEADBEEF.dat"

        monkeypatch.setattr(openvsp_airfoil, "morph_airfoils", _fake_morph)
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca6409", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")

        inserts = out[1:-1]
        assert inserts  # adaptive count, but the curved pair produces inserts
        assert all(
            ins.airfoil == "./components/airfoils/vsp_morph_DEADBEEF.dat"
            for ins in inserts
        )
        # one morph call per insert, always between the two anchor airfoils
        assert calls == [("naca2412", "naca6409")] * len(inserts)
        # Anchors keep their raw airfoils (faithful original).
        assert out[0].airfoil == "naca2412"
        assert out[-1].airfoil == "naca6409"

    def test_morph_failure_falls_back_to_nearest_anchor(self, monkeypatch):
        from app.converters import openvsp_airfoil

        monkeypatch.setattr(openvsp_airfoil, "morph_airfoils", lambda a, b, t: None)
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca6409", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        # Each insert falls back to the nearest anchor by its spanwise
        # fraction t (= u for a single 0→1 pair, and u = y/half_span here):
        # naca2412 for t<0.5, else naca6409.
        inserts = out[1:-1]
        assert inserts
        for ins in inserts:
            t = ins.xyz_le[1] / 6.0
            assert ins.airfoil == ("naca2412" if t < 0.5 else "naca6409")

    def test_morph_fallback_emits_info_warning(self, monkeypatch):
        from app.converters import openvsp_airfoil

        monkeypatch.setattr(openvsp_airfoil, "morph_airfoils", lambda a, b, t: None)
        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca6409", t=None),
        ]
        _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", ctx, "main_wing")
        assert any("nearest anchor" in w.reason for w in ctx.warnings)

    def test_mixed_wing_augments_all_segments(self, monkeypatch):
        """Root→mid same airfoil, mid→tip different: BOTH segments are
        augmented — the same-airfoil pair inherits the NACA name, the
        differing pair gets morphed inserts."""
        from app.converters import openvsp_airfoil

        monkeypatch.setattr(
            openvsp_airfoil,
            "morph_airfoils",
            lambda a, b, t: "./components/airfoils/vsp_morph_X.dat",
        )
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t="segment"),
            _xsec(airfoil="naca6409", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        inserts = out[1:-1]
        # First (same-airfoil) pair contributes naca2412 inserts (sampled
        # y>0 distinguishes them from the mid anchor, which keeps y=0);
        # second (differing) pair contributes morphed inserts.
        assert any(x.airfoil == "naca2412" and x.xyz_le[1] > 0.0 for x in inserts)
        assert any(
            x.airfoil == "./components/airfoils/vsp_morph_X.dat" for x in inserts
        )


class TestSpitfireAnchorCount:
    """Spitfire scenario: a 4-anchor elliptical wing is adaptively
    augmented — more than the 4 raw anchors, capped per pair, with the
    high-curvature tip pair denser than the inner pairs (gh-800)."""

    def test_four_anchors_adaptively_augmented(self):
        anchors = [
            _xsec(airfoil="naca2213", t="root"),
            _xsec(airfoil="naca2213", t="segment"),
            _xsec(airfoil="naca2213", t="segment"),
            _xsec(airfoil="naca2213", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        cap = 2**_AUGMENT_MAX_DEPTH - 1
        assert 4 < len(out) <= 4 + 3 * cap
        # tip pair (high ellipse curvature) is denser than the inner pair
        inner = _adaptive_u_fractions(_ellipse_vsp(), "g", 0.0, 1.0 / 3.0)
        tip = _adaptive_u_fractions(_ellipse_vsp(), "g", 2.0 / 3.0, 1.0)
        assert len(tip) > len(inner)


class TestTwistInterpolation:
    """PR #754 review #1: twist must NOT be derived from body-frame
    LE/TE (which would mix dihedral and section-Z stagger into a
    bogus twist value, especially bad for VTPs). Instead, augmenter
    interpolates ``twist`` linearly between the bracketing anchor
    twists at each insert's spanwise fraction ``t``."""

    def test_interpolates_twist_between_anchors(self):
        # Root twist = 0°, tip twist = -4°. Each insert's twist is the
        # linear interpolation at its spanwise fraction t (= u = y/half_span
        # for a single 0→1 pair): twist = -4·t.
        anchors = [
            _xsec(airfoil="naca2412", twist=0.0, t="root"),
            _xsec(airfoil="naca2412", twist=-4.0, t=None),
        ]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
        inserts = out[1:-1]
        assert inserts
        for ins in inserts:
            t = ins.xyz_le[1] / 6.0
            assert ins.twist == pytest.approx(-4.0 * t, rel=1e-9, abs=1e-9)

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
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
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
        out = _augment_xsec_pairs(anchors, _DihedralStub(), "wing-gid", _ctx(), "wing")
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

    def test_warns_when_pair_cannot_be_sampled(self):
        """A VSP stub whose ``CompPnt01`` raises for every u means the
        adaptive sampler can't assess the pair at all → 0 inserts and a
        single info-warning so the polygonal wing isn't silent (gh-800,
        preserving the gh-753 lossy-warning intent)."""

        class _AlwaysRaises:
            @staticmethod
            def CompPnt01(_gid, _surf, _u, _w):
                raise RuntimeError("synthetic VSP failure")

        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        out = _augment_xsec_pairs(anchors, _AlwaysRaises(), "wing-gid", ctx, "main_wing")
        # No inserts → 2 anchors only.
        assert len(out) == 2
        sampling_warnings = [
            w for w in ctx.warnings if w.severity == "info" and "could not sample" in w.reason
        ]
        assert len(sampling_warnings) == 1
        assert sampling_warnings[0].component_name == "main_wing"

    def test_partial_sampling_failure_degrades_gracefully(self):
        """Endpoints sample fine but a mid-u sample raises: the bisection
        just stops that branch — fewer inserts, all valid, no crash, and
        no spurious 'could not sample' warning (the pair WAS assessable)."""

        class _FlakyAtMidU:
            @staticmethod
            def CompPnt01(_gid, _surf, u, w):
                if 0.35 < u < 0.45:
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
        out = _augment_xsec_pairs(anchors, _FlakyAtMidU(), "wing-gid", ctx, "main_wing")
        assert len(out) >= 2  # never crashes; some inserts may survive
        assert not [w for w in ctx.warnings if "could not sample" in w.reason]

    def test_no_warning_when_all_inserts_succeed(self):
        """Happy path: a fully-sampleable wing → no degradation warning."""
        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2412", t="root"),
            _xsec(airfoil="naca2412", t=None),
        ]
        _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", ctx, "main_wing")
        assert not [
            w
            for w in ctx.warnings
            if "could not sample" in w.reason or "gh-758" in w.reason
        ]


class TestDegenerateInputs:
    def test_single_xsec_passthrough(self):
        anchors = [_xsec(airfoil="naca2412", t="root")]
        out = _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", _ctx(), "wing")
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
        out = _augment_xsec_pairs(
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
        out = _augment_xsec_pairs(anchors, _FlakyVsp(), "wing-gid", _ctx(), "wing")
        # Import never crashes; the adaptive bisection simply avoids the
        # flaky u-band, so no surviving insert lands inside it.
        assert len(out) >= 2
        for ins in out[1:-1]:
            u = ins.xyz_le[1] / 6.0
            assert not (0.35 < u < 0.45)


# ---------------------------------------------------------------------------
# gh-758 — Tip-cap-aware augmentation
# ---------------------------------------------------------------------------
#
# Real VSP wings have an implicit tip cap (round / flat / etc.) which
# occupies an u-range near 1.0 on the main wing surface. Within this
# range, ``CompPnt01(gid, 0, u, w)`` returns near-identical points that
# converge to the cap centerline as u → 1.0 — see the gh-758 issue body
# for the Cessna 172 + Spitfire reproductions where DB rows 8/9/10 had
# exactly identical ``xyz_le = [-0.055, 5.243, 0.510]`` after
# augmentation.
#
# The fix introduces ``_find_cap_safe_u_max`` to probe the surface for
# the largest non-convergent u, and the augmenter skips any insert
# whose u exceeds that threshold. A defensive xyz_le-dedup catches any
# edge case the probe might miss.


def _capped_vsp(
    half_span: float = 6.0,
    root_chord: float = 2.0,
    u_cap_start: float = 0.90,
    cap_z: float = 0.5,
    cap_chord: float = 0.05,
):
    """Build a VSP stub whose CompPnt01 simulates a real wing surface
    WITH a tip cap. For u < u_cap_start, behaves like the ellipse stub
    (smoothly varying LE/TE). For u >= u_cap_start, the LE clusters to
    the cap centerline at (-cap_chord/2, half_span * u_cap_start, cap_z)
    while the TE clusters to (+cap_chord/2, ..., cap_z) — preserving a
    small non-zero ``cap_chord`` distance so the augmenter's
    ``chord <= 0`` check does NOT fire.

    That distinction matters: review on PR #759 caught that a stub where
    cap-region LE == TE made the existing ``if chord <= 0: continue``
    silently drop every cap-region insert pre-fix, so the regression
    tests "passed" against the pre-fix code. Real VSP CompPnt01 returns
    distinct-but-clustered LE/TE in the cap region — the Spitfire DB
    evidence (rows 8/9/10 with identical xyz_le but non-zero chord)
    is exactly this shape. This stub models that faithfully so the
    tests actually pin the regression they claim to.
    """

    class _Stub:
        # gh-760: legacy capped stub keeps the gh-758 cap-probe path
        # exercised by NOT exposing ``CapUMinOption`` / ``CapUMaxOption``
        # parms. Returning 0 from ``FindParm`` for EndCap parms forces
        # the augmenter to fall back to ``_find_cap_safe_u_max`` — the
        # original behaviour these gh-758 tests pin.
        @staticmethod
        def FindParm(_gid: str, _parm: str, _group: str) -> int:
            return 0

        @staticmethod
        def CompPnt01(_gid: str, _surf: int, u: float, w: float) -> _Pnt:
            if u >= u_cap_start:
                # Cap region: LE/TE cluster to the cap centerline ±
                # cap_chord/2 — identical for every u in the cap, but
                # LE != TE so chord > 0 (matches Spitfire DB evidence).
                y_cap = half_span * u_cap_start
                if abs(w - _W_LE) < 1e-9:
                    return _Pnt(-cap_chord / 2.0, y_cap, cap_z)
                if abs(w - _W_TE) < 1e-9:
                    return _Pnt(+cap_chord / 2.0, y_cap, cap_z)
                return _Pnt(-cap_chord / 2.0, y_cap, cap_z)
            y = half_span * u
            chord = root_chord * math.sqrt(max(0.0, 1.0 - u * u))
            if abs(w - _W_LE) < 1e-9:
                return _Pnt(-chord / 2.0, y, 0.0)
            if abs(w - _W_TE) < 1e-9:
                return _Pnt(+chord / 2.0, y, 0.0)
            return _Pnt(-chord / 2.0, y, 0.0)

    return _Stub()


class TestFindCapSafeUMax:
    """Probe-based detection of the largest u for which CompPnt01
    still returns a distinct (= non-cap) point. The augmenter clamps
    inserts to stay clear of this boundary."""

    def test_no_cap_returns_high_u(self):
        """The plain ellipse stub has no cap — every u ∈ [0, 1] gives
        a distinct point. The probe returns ~1.0 (or the largest probe
        value that's still distinct from u=1.0)."""
        u_max = _find_cap_safe_u_max(_ellipse_vsp(), "wing-gid")
        assert u_max >= 0.95

    def test_capped_returns_below_cap_start(self):
        """A capped stub with u_cap_start=0.90 → probe must return a
        u_max <= 0.90 so that inserts stay clear of the cap region."""
        u_max = _find_cap_safe_u_max(_capped_vsp(u_cap_start=0.85), "wing-gid")
        assert u_max <= 0.90

    def test_no_comppnt01_returns_one(self):
        """No CompPnt01 → probe is unusable; return 1.0 (= no clamping,
        the augmenter's early-return covers the actual call sites)."""

        class _StubWithoutCompPnt:
            pass

        u_max = _find_cap_safe_u_max(_StubWithoutCompPnt(), "wing-gid")
        assert u_max == 1.0

    def test_raising_comppnt01_returns_one(self):
        """If CompPnt01 raises on the tip probe, fall back to 1.0
        (= no clamping; let the augmenter's per-u exception path
        handle individual failures)."""

        class _AlwaysRaises:
            @staticmethod
            def CompPnt01(_gid, _surf, _u, _w):
                raise RuntimeError("synthetic")

        u_max = _find_cap_safe_u_max(_AlwaysRaises(), "wing-gid")
        assert u_max == 1.0


class TestCapAwareAugmentation:
    """gh-758 acceptance criterion: a wing with a tip cap must NOT
    produce duplicate xyz_le rows in the augmented xsec list, and no
    insert must land on the cap surface (which would visually lift
    the wing into a z-kink)."""

    def test_no_duplicate_xyz_le_with_tip_cap(self):
        """A 4-anchor wing on a capped stub must produce 0 duplicate
        consecutive xyz_le values. This is the direct DB-inspection
        criterion from the issue body."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 2.0, 0.0), chord=1.8, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 4.0, 0.0), chord=1.2, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 5.4, 0.0), chord=0.4, t=None),
        ]
        out = _augment_xsec_pairs(
            anchors, _capped_vsp(u_cap_start=0.85), "wing-gid", _ctx(), "wing"
        )
        # Walk the output and assert no two consecutive xsecs share
        # an xyz_le within 1e-6 m (= 1 μm — far below any meaningful
        # wing geometry resolution).
        for prev, curr in zip(out, out[1:], strict=False):
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev.xyz_le, curr.xyz_le, strict=True)))
            assert d > 1e-6, f"Duplicate xyz_le detected: {prev.xyz_le} == {curr.xyz_le}"

    def test_no_insert_lands_on_cap_z(self):
        """Inserts must not pick up the cap's Z-offset (which causes
        the 'tip-caps parked at z≈1' visual symptom). Anchors all have
        z=0; inserts must keep z near 0 too.

        4-anchor setup so the last pair's outer inserts (u ≈ 0.867,
        0.933) actually exercise the cap region pre-fix — that's the
        regression reported in the gh-758 issue body.
        """
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 2.0, 0.0), chord=1.8, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 4.0, 0.0), chord=1.2, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 5.1, 0.0), chord=0.4, t=None),
        ]
        out = _augment_xsec_pairs(
            anchors, _capped_vsp(u_cap_start=0.85, cap_z=0.5), "wing-gid", _ctx(), "wing"
        )
        # All inserts (everything except first/last anchors) must have
        # z ≈ 0 (the non-cap surface), not z = 0.5 (the cap centerline).
        for ins in out[1:-1]:
            assert abs(ins.xyz_le[2]) < 1e-6, (
                f"Insert picked up cap Z: xyz_le={ins.xyz_le} — "
                "augmenter should have skipped this cap-region u"
            )

    def test_emits_cap_truncation_warning(self):
        """When inserts are skipped due to the cap region, the
        augmenter must surface that via ctx.add_warning so the user
        can correlate the visual symptom (fewer-than-expected xsecs
        near the tip) with an import event. Phrased differently from
        the existing 'CompPnt01 failure' warning so the two are
        distinguishable in the import report.

        Setup mirrors the Spitfire's 4-anchor wing — the gh-758 bug
        reproducer — where the outer pair's outer inserts land in
        the cap region.
        """
        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 2.0, 0.0), chord=1.8, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 4.0, 0.0), chord=1.2, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 5.4, 0.0), chord=0.4, t=None),
        ]
        _augment_xsec_pairs(
            anchors, _capped_vsp(u_cap_start=0.85), "wing-gid", ctx, "main_wing"
        )
        # Look for a gh-758 cap-truncation warning specifically.
        cap_warnings = [w for w in ctx.warnings if w.severity == "info" and "gh-758" in w.reason]
        assert len(cap_warnings) == 1
        assert cap_warnings[0].component_name == "main_wing"

    def test_no_cap_warning_for_no_cap_wing(self):
        """A wing with no cap (ellipse stub, u_max ≈ 1.0) must NOT
        emit the cap-truncation warning — would be noise on healthy
        imports."""
        ctx = _ctx()
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 6.0, 0.0), chord=0.0, t=None),
        ]
        _augment_xsec_pairs(anchors, _ellipse_vsp(), "wing-gid", ctx, "main_wing")
        cap_warnings = [w for w in ctx.warnings if "gh-758" in w.reason]
        assert cap_warnings == []

    def test_inserts_remain_in_non_cap_segments(self):
        """The first segments of a multi-anchor wing (root→mid) are far
        from the tip cap. Their inserts must still happen normally — the
        clamp only affects the outermost segment."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 2.0, 0.0), chord=1.8, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 5.4, 0.0), chord=0.4, t=None),
        ]
        out = _augment_xsec_pairs(
            anchors, _capped_vsp(u_cap_start=0.85), "wing-gid", _ctx(), "wing"
        )
        # First segment (root → mid, u ∈ [0, 0.5]) is well below the cap
        # start and gets adaptive inserts; the second (mid → tip) is partly
        # cap-clamped. The exact count is curvature-driven — the >= 7 bound
        # is a conservative floor that both segments clear in practice.
        assert len(out) >= 7

    def test_dedup_safety_net_drops_clustered_insert(self):
        """The LE-dedup safety net (``_try_emit_one_insert`` → DEDUPED)
        drops an insert whose LE clusters within ``_DEDUP_EPS`` of the
        previous xsec. Tested at the mechanism level since the adaptive
        sampler (gh-800) no longer manufactures mid-span clusters itself
        — the net remains a defence for cap-convergence regions.
        """

        def _flat_vsp():
            class _Stub:
                @staticmethod
                def CompPnt01(_gid, _surf, _u, w):
                    # Same LE/TE for any u → any insert clusters.
                    return _Pnt(-0.5, 3.0, 0.0) if abs(w - _W_LE) < 1e-9 else _Pnt(0.5, 3.0, 0.0)

            return _Stub()

        out = [_xsec(airfoil="naca2213", xyz_le=(-0.5, 3.0, 0.0), chord=1.0, t="root")]
        outcome = _try_emit_one_insert(
            vsp=_flat_vsp(),
            gid="g",
            u=0.5,
            u_max=1.0,
            twist_deg=0.0,
            airfoil="naca2213",
            out=out,
        )
        assert outcome == _OUTCOME_DEDUPED
        assert len(out) == 1  # the clustered insert was not appended

    def test_no_duplicate_xyz_le_in_adaptive_output(self):
        """Whatever the adaptive bisection produces, consecutive output
        xsecs are never duplicates (dedup invariant)."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 5.88, 0.0), chord=0.0, t=None),
        ]
        out = _augment_xsec_pairs(
            anchors, _capped_vsp(u_cap_start=0.98), "wing-gid", _ctx(), "wing"
        )
        assert len(out) > 2  # the elliptical pair produced inserts
        for prev, curr in zip(out, out[1:], strict=False):
            d = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(prev.xyz_le, curr.xyz_le, strict=True))
            )
            assert d > 1e-6

    def test_dihedral_with_cap_does_not_kink_at_tip(self):
        """gh-758 DG-101G evidence: a dihedral wing with a tip cap
        used to render a Z-jump kink near the tip. The fix's u-clamp
        keeps inserts clear of the cap, and the augmenter's twist
        interpolation continues to ignore body-frame Z (PR #754).
        Combined: no kink, no false twist."""

        def _dihedral_capped_vsp():
            class _Stub:
                @staticmethod
                def CompPnt01(_gid, _surf, u, w):
                    if u >= 0.85:
                        # Cap region: LE clusters at cap_z. Pre-fix
                        # would lift the tip section to z=0.5.
                        if abs(w - _W_LE) < 1e-9:
                            return _Pnt(-0.025, 5.1, 0.5)
                        return _Pnt(+0.025, 5.1, 0.5)
                    # Non-cap: LE is dihedral'd (z = 0.1 * u).
                    y = 6.0 * u
                    z = 0.1 * u
                    chord = 2.0 * math.sqrt(max(0.0, 1.0 - u * u))
                    if abs(w - _W_LE) < 1e-9:
                        return _Pnt(-chord / 2.0, y, z)
                    return _Pnt(+chord / 2.0, y, z)

            return _Stub()

        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(0.0, 0.0, 0.0), chord=2.0, twist=0.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(0.0, 6.0, 0.6), chord=0.0, twist=0.0, t=None),
        ]
        out = _augment_xsec_pairs(
            anchors, _dihedral_capped_vsp(), "wing-gid", _ctx(), "wing"
        )
        # No insert may carry the cap z-offset (0.5).
        for ins in out[1:-1]:
            assert ins.xyz_le[2] < 0.4, f"Cap Z leaked into a dihedral wing insert: {ins.xyz_le}"
        # And twist stays 0 (no atan2 from body-frame Z).
        for ins in out[1:-1]:
            assert ins.twist == 0.0


# ---------------------------------------------------------------------------
# gh-760 — VSP anchor-u formula
# ---------------------------------------------------------------------------
#
# Real VSP wings do not place anchors uniformly across u ∈ [0, 1]. The
# anchor-u positions depend on the wing's cap configuration:
#
#     cap_min = 1 if CapUMinOption > 0 else 0     # root cap present?
#     cap_max = 1 if CapUMaxOption > 0 else 0     # tip cap present?
#     total_segments = (n_xsec - 1) + cap_min + cap_max
#     anchor_u[i] = (i + cap_min) / total_segments
#
# Verified empirically via ``GetUWTess01`` across 13 wings in
# Spitfire / Cessna 172 / DG-101G — see issue #760 for the dashboard
# Phase 4 table. The pre-fix augmenter assumed ``u = i / (n_anchors - 1)``,
# producing the Spitfire xsec 5/6 collision (insert at augmenter-u 0.6
# landed on Anchor 2's real VSP u = 0.6).


class _CappedWingStub:
    """VSP stub that exposes ``CapUMinOption`` / ``CapUMaxOption``
    via ``FindParm`` + ``GetParmVal`` so the new ``_anchor_u_position``
    helper can read them. CompPnt01 simulates an ellipse with the
    correct cap-aware u-parameterization: anchor i sits at u =
    (i + cap_min) / total_segments.

    cap_*_option is 0 for no cap, 1 for flat cap, 2 for round cap
    (matching VSP's enum). Any non-zero value counts as cap_present=1.
    """

    def __init__(
        self,
        n_xsec: int,
        cap_min_option: int = 1,
        cap_max_option: int = 1,
        half_span: float = 6.0,
        root_chord: float = 2.0,
    ):
        self.n_xsec = n_xsec
        self.cap_min_option = cap_min_option
        self.cap_max_option = cap_max_option
        self.half_span = half_span
        self.root_chord = root_chord
        cap_min = 1 if cap_min_option > 0 else 0
        cap_max = 1 if cap_max_option > 0 else 0
        self.total_segments = (n_xsec - 1) + cap_min + cap_max
        self.cap_min = cap_min
        self.cap_max = cap_max

    # FindParm / GetParmVal — only resolve CapU*Option from EndCap group.
    def FindParm(self, gid: str, parm: str, group: str) -> int:
        if group == "EndCap" and parm == "CapUMinOption":
            return 11
        if group == "EndCap" and parm == "CapUMaxOption":
            return 12
        return 0

    def GetParmVal(self, pid: int) -> float:
        if pid == 11:
            return float(self.cap_min_option)
        if pid == 12:
            return float(self.cap_max_option)
        raise KeyError(pid)

    # CompPnt01 — cap-aware ellipse. u_anchor[i] = (i+cap_min)/total.
    # Between anchors → linear interpolation in y; in cap regions →
    # converge to the root/tip anchor point (matches real VSP).
    def CompPnt01(self, _gid: str, _surf: int, u: float, w: float) -> "_Pnt":
        if self.cap_min and u < self.cap_min / self.total_segments:
            # Root cap — converge to Anchor 0
            return self._anchor_pnt(0, w)
        if self.cap_max and u > (self.n_xsec - 1 + self.cap_min) / self.total_segments:
            # Tip cap — converge to Anchor n-1
            return self._anchor_pnt(self.n_xsec - 1, w)
        # In a section: find which one, then interpolate
        for i in range(self.n_xsec - 1):
            u_lo = (i + self.cap_min) / self.total_segments
            u_hi = (i + 1 + self.cap_min) / self.total_segments
            if u_lo <= u <= u_hi + 1e-9:
                # frac ∈ [0, 1] within the section
                frac = (u - u_lo) / (u_hi - u_lo) if u_hi > u_lo else 0.0
                y_lo = self.half_span * i / (self.n_xsec - 1)
                y_hi = self.half_span * (i + 1) / (self.n_xsec - 1)
                y = y_lo + frac * (y_hi - y_lo)
                chord = self.root_chord * math.sqrt(max(0.0, 1.0 - (y / self.half_span) ** 2))
                if abs(w - _W_LE) < 1e-9:
                    return _Pnt(-chord / 2.0, y, 0.0)
                if abs(w - _W_TE) < 1e-9:
                    return _Pnt(+chord / 2.0, y, 0.0)
                return _Pnt(-chord / 2.0, y, 0.0)
        # Fallback for u slightly outside [0, 1]: return tip
        return self._anchor_pnt(self.n_xsec - 1, w)

    def _anchor_pnt(self, i: int, w: float) -> "_Pnt":
        y = self.half_span * i / (self.n_xsec - 1)
        chord = self.root_chord * math.sqrt(max(0.0, 1.0 - (y / self.half_span) ** 2))
        if abs(w - _W_LE) < 1e-9:
            return _Pnt(-chord / 2.0, y, 0.0)
        if abs(w - _W_TE) < 1e-9:
            return _Pnt(+chord / 2.0, y, 0.0)
        return _Pnt(-chord / 2.0, y, 0.0)


class TestAnchorUPosition:
    """gh-760 contract — VSP's actual u-position per anchor depends on
    cap configuration. Pin the formula across the four canonical cases:
    both caps, neither cap, root-only, tip-only."""

    def test_both_caps_present(self):
        """Standard wing (Wing, Spitfire) — both ``CapUMinOption`` and
        ``CapUMaxOption`` non-zero → anchor i at (i+1)/(n_xsec+1)."""
        vsp = _CappedWingStub(n_xsec=4, cap_min_option=1, cap_max_option=1)
        # 4 anchors, total_segments = 3 + 1 + 1 = 5
        # Anchor i at (i + 1) / 5
        for i, expected in enumerate([0.2, 0.4, 0.6, 0.8]):
            assert _anchor_u_position(vsp, "wing-gid", i, 4) == pytest.approx(expected)

    def test_no_caps(self):
        """Edge case: both options = 0 → anchors span full u-range.
        Anchor 0 at u=0, anchor n-1 at u=1."""
        vsp = _CappedWingStub(n_xsec=3, cap_min_option=0, cap_max_option=0)
        # total_segments = 2 + 0 + 0 = 2
        # Anchor i at i / 2
        for i, expected in enumerate([0.0, 0.5, 1.0]):
            assert _anchor_u_position(vsp, "wing-gid", i, 3) == pytest.approx(expected)

    def test_root_only_cap(self):
        """``CapUMinOption > 0, CapUMaxOption = 0`` — anchors offset
        forward; anchor n-1 sits at the tip (u=1)."""
        vsp = _CappedWingStub(n_xsec=3, cap_min_option=1, cap_max_option=0)
        # total_segments = 2 + 1 + 0 = 3
        # Anchor i at (i + 1) / 3
        for i, expected in enumerate([1 / 3, 2 / 3, 3 / 3]):
            assert _anchor_u_position(vsp, "wing-gid", i, 3) == pytest.approx(expected)

    def test_tip_only_cap_matches_dg_htail(self):
        """``CapUMinOption = 0, CapUMaxOption > 0`` — the DG-101G H-Tail
        edge case. Anchor 0 at u=0 (no root cap), anchor n-1 inboard
        of tip cap."""
        vsp = _CappedWingStub(n_xsec=2, cap_min_option=0, cap_max_option=2)
        # total_segments = 1 + 0 + 1 = 2
        # Anchor i at i / 2
        assert _anchor_u_position(vsp, "wing-gid", 0, 2) == pytest.approx(0.0)
        assert _anchor_u_position(vsp, "wing-gid", 1, 2) == pytest.approx(0.5)

    def test_round_cap_option_2_counts_as_present(self):
        """VSP's ``CapU*Option = 2`` (round cap) still means "cap
        present". The helper treats any non-zero value as cap_present=1.
        """
        vsp = _CappedWingStub(n_xsec=3, cap_min_option=2, cap_max_option=2)
        # Same as both_caps_present (round vs flat doesn't change u-position)
        for i, expected in enumerate([0.25, 0.5, 0.75]):
            assert _anchor_u_position(vsp, "wing-gid", i, 3) == pytest.approx(expected)


class TestAugmenterUsesCorrectUMapping:
    """gh-760: the regression scenario. Spitfire-like 4-anchor wing
    with both caps. The pre-fix augmenter mapped anchor i to
    u = i/(n_anchors-1), so the last insert in pair (n-2 → n-1) at
    u_lo + 4·step = (n-2)/(n-1) + 4·(1/(n-1))/5 = (n-2)/(n-1) +
    0.8/(n-1) landed at Anchor n-1's real VSP u for n=4 (= 0.6).

    Post-fix, inserts in pair (i → i+1) span [u_anchor[i], u_anchor[i+1]]
    which is BETWEEN the anchors' actual u-positions — no collision."""

    def test_no_insert_collides_with_next_anchor(self):
        """Pin the Spitfire 5/6 collision: with cap-aware u-mapping,
        the last insert in pair (n-2 → n-1) sits BEFORE anchor n-1's
        real u-position. Pre-fix the insert and the anchor had the
        same xyz_le (the user's "oversized oval" near the tip)."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(-0.92, 2.0, 0.0), chord=1.83, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(-0.60, 4.0, 0.0), chord=1.20, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(-0.07, 5.5, 0.0), chord=0.14, t=None),
        ]
        vsp = _CappedWingStub(n_xsec=4, cap_min_option=1, cap_max_option=1)
        out = _augment_xsec_pairs(anchors, vsp, "wing-gid", _ctx(), "Wing")
        # No consecutive xsecs share an xyz_le within 1 mm (= the
        # gh-760 DB-evidence threshold; pre-fix the gap was ~1 mm).
        for prev, curr in zip(out, out[1:], strict=False):
            d = math.sqrt(sum((a - b) ** 2 for a, b in zip(prev.xyz_le, curr.xyz_le, strict=True)))
            assert d > 1e-3, (
                f"Insert collides with next anchor: prev={prev.xyz_le}, curr={curr.xyz_le} "
                f"(distance {d * 1000:.2f} mm) — gh-760 u-mapping regression."
            )

    def test_outer_section_gets_inserts(self):
        """Pre-fix, pair (n-2 → n-1) inserts mapped to u ∈ [0.667, 1.0]
        (for 4 anchors) and were ALL cap-clamped by the gh-758 safety
        net (u_max ≈ 0.7). Post-fix, they map to u ∈ [0.6, 0.8] which
        is fully inside the wing surface — all 4 should INSERT."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(-0.92, 2.0, 0.0), chord=1.83, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(-0.60, 4.0, 0.0), chord=1.20, t="segment"),
            _xsec(airfoil="naca2213", xyz_le=(-0.07, 5.5, 0.0), chord=0.14, t=None),
        ]
        vsp = _CappedWingStub(n_xsec=4, cap_min_option=1, cap_max_option=1)
        out = _augment_xsec_pairs(anchors, vsp, "wing-gid", _ctx(), "Wing")
        # The contract here is that the OUTER pair (anchor n-2 → n-1) is no
        # longer entirely cap-clamped (the pre-fix bug) — it must contribute
        # inserts. The adaptive count is curvature-driven.
        outer_pair_inserts = 0
        # The outer pair's inserts sit between anchor 2 (y=4.0) and
        # anchor 3 (y=5.5), so y ∈ (4.0, 5.5).
        for xs in out:
            if 4.0 < xs.xyz_le[1] < 5.5:
                outer_pair_inserts += 1
        assert outer_pair_inserts >= 2, (
            f"Outer pair (anchor n-2 → n-1) got only {outer_pair_inserts} inserts "
            "— pre-fix this section was entirely cap-clamped."
        )

    def test_inner_section_no_root_cap_dedup(self):
        """Pre-fix, pair 0→1 inserts at augmenter-u ∈ (0, 0.333) landed
        in VSP's root-cap region (u ∈ [0, 0.2] for both-caps wing) and
        got DEDUPED. Post-fix, inserts map to u ∈ (0.2, 0.4) — clear
        of the root cap."""
        anchors = [
            _xsec(airfoil="naca2213", xyz_le=(-1.0, 0.0, 0.0), chord=2.0, t="root"),
            _xsec(airfoil="naca2213", xyz_le=(-0.92, 2.0, 0.0), chord=1.83, t=None),
        ]
        ctx = _ctx()
        vsp = _CappedWingStub(n_xsec=2, cap_min_option=1, cap_max_option=1)
        out = _augment_xsec_pairs(anchors, vsp, "wing-gid", ctx, "Wing")
        # Adaptive inserts are produced (count is curvature-driven) and none
        # dedup, because cap-aware u-mapping keeps them clear of the root cap.
        assert len(out) > 2
        # The dedup safety-net warning must NOT fire — cap-aware
        # u-mapping eliminates the root-cap collision.
        dedup_warnings = [
            w for w in ctx.warnings if "gh-758" in w.reason and "LE-dedup" in w.reason
        ]
        assert dedup_warnings == [], (
            "LE-dedup fired on a cap-aware mapping — should be unreachable "
            "in the no-pathological-cap case."
        )
