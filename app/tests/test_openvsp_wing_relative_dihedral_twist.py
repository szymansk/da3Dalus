"""gh-755 — wing import respects VSP's ``RelativeDihedralFlag`` and
``RelativeTwistFlag``.

OpenVSP carries two per-Wing flags that switch the per-section
``Dihedral`` and ``Twist`` parms between **absolute** (world-frame,
VSP default) and **relative** (chained off the previous section).
Pre-fix, ``_handle_wing`` ignored both flags and always interpreted
the parms as absolute. A ``.vsp3`` designed with
``RelativeDihedralFlag = 1`` (e.g. the DG-101G glider, where the user
sets Section 2 = "0° dihedral" meaning "continue with the carried-
over 3°") collapsed Section 2 onto a flat-horizontal Z, producing a
visible kink at the Section 1/2 boundary.

These tests use a minimal VSP stub that exposes the parm calls the
handler relies on. Verified geometric invariants (DG-style cumulative
dihedral, cosine-correct y-step at large angles, Cessna-style flat
wing no-regression) are pinned against analytical values.
"""

from __future__ import annotations

import math

import pytest

from app.converters.openvsp_importer import (
    AeroplaneSchema,
    ImportContext,
)
from app.converters.openvsp_wing_handler import (
    _handle_wing,
    _read_relative_flag,
)


# ---------------------------------------------------------------------------
# VSP stub — just enough surface to drive ``_handle_wing``.
# ---------------------------------------------------------------------------


class _VspStub:
    """Configurable VSP stub. ``parms`` is a flat dict keyed by
    ``(parm_name, group)`` so the handler's ``FindParm`` calls
    deterministically resolve. ``XSec_<i>`` parms live under group
    ``XSec_<i>``; ``RelativeDihedralFlag`` / ``RelativeTwistFlag``
    live under ``WingGeom``; ``Sym_Planar_Flag`` under ``Sym``;
    XForm parms under ``XForm``.
    """

    SYM_XZ = 2

    def __init__(self, n_xsec: int, parms: dict[tuple[str, str], float]):
        self._n_xsec = n_xsec
        self._parms = parms
        # ``GetXSec`` returns the xs_index; the handler only stores it
        # in a local and passes it to ``import_airfoil_from_xsec``, which
        # we monkey-patch out via a stubbed _airfoil_for path. We don't
        # need a real ID — int works.
        self.GetXSecSurf = lambda gid, surf_id: "xsurf-mock"
        self.GetNumXSec = lambda xsurf: self._n_xsec
        # Stub for CompPnt01 — never called when the wing has no
        # same-airfoil pairs (the gh-753 augmenter short-circuits).
        # Provided so ``hasattr(vsp, 'CompPnt01')`` returns True.

    def GetXSec(self, xsurf, xs_index):
        return ("xs", xs_index)

    def FindParm(self, gid: str, parm: str, group: str) -> int:
        # Encode a fake non-zero parm id by hashing (gid, parm, group).
        # The handler only checks truthiness + later calls GetParmVal,
        # so any deterministic non-zero int works.
        if (parm, group) in self._parms:
            return hash((gid, parm, group)) or 1
        return 0

    def GetParmVal(self, pid: int) -> float:
        # Reverse-lookup via the same hash. Since we only need to
        # round-trip a single call, store a (pid → value) map by
        # rebuilding from ``parms`` on demand.
        # Simpler: iterate the parms dict and return the first match
        # whose ``hash((gid, parm, group))`` equals pid. For tests
        # the parms dict is tiny so the linear scan is acceptable.
        for (parm, group), value in self._parms.items():
            for gid in ("wing-gid",):  # stub only ever uses this gid
                if (hash((gid, parm, group)) or 1) == pid:
                    return float(value)
        raise KeyError(f"unknown pid {pid}")

    def CompPnt01(self, gid, surf, u, w):
        # Return a stub point — gh-753 augmenter is short-circuited
        # by all-different airfoils in these tests (the airfoils
        # come from the placeholder which is unique per xsec via the
        # monkey-patched _airfoil_for in the test wiring).
        class _P:
            def x(self) -> float:
                return 0.0

            def y(self) -> float:
                return 0.0

            def z(self) -> float:
                return 0.0

        return _P()


def _build_parms(
    *,
    n_xsec: int,
    sections: list[dict[str, float]],
    relative_dihedral: int = 0,
    relative_twist: int = 0,
    sym_xz: bool = False,
    xform_translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    xform_rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[tuple[str, str], float]:
    """Assemble the parm dict that ``_VspStub`` consumes.

    ``sections`` is a list of N-1 dicts (one per planform-section),
    each carrying ``Span``, ``Tip_Chord``, ``Sweep``, ``Sweep_Location``,
    ``Dihedral``, ``Twist``. The first section additionally needs
    ``Root_Chord``.
    """
    parms: dict[tuple[str, str], float] = {}
    for i, sec in enumerate(sections, start=1):
        for k, v in sec.items():
            parms[(k, f"XSec_{i}")] = v
    if relative_dihedral:
        parms[("RelativeDihedralFlag", "WingGeom")] = float(relative_dihedral)
    if relative_twist:
        parms[("RelativeTwistFlag", "WingGeom")] = float(relative_twist)
    if sym_xz:
        parms[("Sym_Planar_Flag", "Sym")] = float(_VspStub.SYM_XZ)
    if any(xform_translation):
        for k, v in zip(("X_Location", "Y_Location", "Z_Location"), xform_translation, strict=True):
            parms[(k, "XForm")] = v
    if any(xform_rotation):
        for k, v in zip(("X_Rotation", "Y_Rotation", "Z_Rotation"), xform_rotation, strict=True):
            parms[(k, "XForm")] = v
    return parms


@pytest.fixture
def aeroplane() -> AeroplaneSchema:
    return AeroplaneSchema(name="test-aeroplane")


@pytest.fixture
def ctx() -> ImportContext:
    return ImportContext()


# Patch the airfoil resolution so each xsec gets a UNIQUE airfoil
# reference — the gh-753 augmenter then short-circuits all same-airfoil
# pairs and doesn't add interpolated xsecs. Keeps these tests focused
# on the gh-755 dihedral/twist logic alone.
@pytest.fixture(autouse=True)
def _patch_airfoil_resolution(monkeypatch):
    from app.converters import openvsp_airfoil

    counter = {"i": 0}

    def _unique_airfoil(*args, **kwargs):
        counter["i"] += 1
        return f"./components/airfoils/test_unique_{counter['i']}.dat"

    monkeypatch.setattr(openvsp_airfoil, "import_airfoil_from_xsec", _unique_airfoil)


# ---------------------------------------------------------------------------
# _read_relative_flag
# ---------------------------------------------------------------------------


class TestReadRelativeFlag:
    def test_absent_returns_false(self):
        vsp = _VspStub(n_xsec=2, parms={})
        assert _read_relative_flag(vsp, "wing-gid", "RelativeDihedralFlag") is False

    def test_value_1_returns_true(self):
        vsp = _VspStub(n_xsec=2, parms={("RelativeDihedralFlag", "WingGeom"): 1.0})
        assert _read_relative_flag(vsp, "wing-gid", "RelativeDihedralFlag") is True

    def test_value_0_returns_false(self):
        # Parm EXISTS but is set to 0.0 — must take the
        # ``int(GetParmVal) → False`` path, not the early ``return
        # False`` for an absent parm. The pre-fix bug was symmetric
        # in both paths, but a future change to ``_read_relative_flag``
        # could regress one without the other; this test pins the
        # value-0 path explicitly. Bypass the ``_build_parms`` helper
        # so the parm is registered even with zero value.
        vsp = _VspStub(n_xsec=2, parms={("RelativeTwistFlag", "WingGeom"): 0.0})
        assert _read_relative_flag(vsp, "wing-gid", "RelativeTwistFlag") is False


# ---------------------------------------------------------------------------
# Cessna 172 — flat wing, both flags 0, no regression.
# ---------------------------------------------------------------------------


class TestCessnaFlatWingNoRegression:
    """Cessna 172: 1 section, 0° dihedral, 0° twist, both flags 0
    (default). Pre-fix code computed (cum_y = span, cum_z = 0). Post-
    fix must produce identical values."""

    def test_single_section_flat_wing(self, aeroplane, ctx):
        parms = _build_parms(
            n_xsec=2,
            sections=[
                {
                    "Root_Chord": 1.5,
                    "Tip_Chord": 1.0,
                    "Span": 5.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,
                    "Twist": 0.0,
                }
            ],
        )
        _handle_wing("wing-gid", "MainWing", aeroplane, ctx, _VspStub(2, parms))
        wing = aeroplane.wings["MainWing"]
        # Root + tip — 2 xsecs.
        assert len(wing.x_secs) == 2
        tip = wing.x_secs[-1]
        # 0° Dihedral → y = span = 5.0, z = 0.
        assert tip.xyz_le[1] == pytest.approx(5.0, abs=1e-9)
        assert tip.xyz_le[2] == pytest.approx(0.0, abs=1e-9)
        # x = small positive (LE sweep induced by 0° quarter-chord
        # sweep on a tapered wing — that's the existing
        # ``sweep_at_le`` conversion at work, not the gh-755 change).
        assert tip.xyz_le[0] == pytest.approx(0.125, rel=1e-9)
        # Twist 0° → tip twist 0°.
        assert tip.twist == 0.0


# ---------------------------------------------------------------------------
# DG-101G — RelativeDihedralFlag=1, cumulative dihedral
# ---------------------------------------------------------------------------


class TestDgRelativeDihedral:
    """DG-101G-style: 2 sections, ``RelativeDihedralFlag=1``,
    Section 1 = 3°, Section 2 = 0° (relative → continues 3°).
    Pre-fix Section 2's z stayed flat. Post-fix must rise per
    sin(3°) along the second section."""

    def test_section_2_continues_carried_over_dihedral(self, aeroplane, ctx):
        parms = _build_parms(
            n_xsec=3,
            sections=[
                {
                    "Root_Chord": 1.0,
                    "Tip_Chord": 0.8,
                    "Span": 4.5,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 3.0,
                    "Twist": 0.0,
                },
                {
                    "Tip_Chord": 0.4,
                    "Span": 3.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,  # relative → continue 3°
                    "Twist": 0.0,
                },
            ],
            relative_dihedral=1,
        )
        _handle_wing("wing-gid", "MainWing", aeroplane, ctx, _VspStub(3, parms))
        wing = aeroplane.wings["MainWing"]
        assert len(wing.x_secs) == 3

        # Section 1: y = 4.5 · cos(3°), z = 4.5 · sin(3°).
        s1 = wing.x_secs[1]
        assert s1.xyz_le[1] == pytest.approx(4.5 * math.cos(math.radians(3.0)), rel=1e-9)
        assert s1.xyz_le[2] == pytest.approx(4.5 * math.sin(math.radians(3.0)), rel=1e-9)

        # Section 2: cumulative dihedral stays 3°. Y += 3·cos(3°),
        # Z += 3·sin(3°). Pre-fix bug: Z stayed at Section 1's value.
        s2 = wing.x_secs[2]
        expected_y = 4.5 * math.cos(math.radians(3.0)) + 3.0 * math.cos(math.radians(3.0))
        expected_z = 4.5 * math.sin(math.radians(3.0)) + 3.0 * math.sin(math.radians(3.0))
        assert s2.xyz_le[1] == pytest.approx(expected_y, rel=1e-9)
        assert s2.xyz_le[2] == pytest.approx(expected_z, rel=1e-9), (
            f"Section 2 z must continue carried-over 3° dihedral; "
            f"pre-fix bug would give z = {4.5 * math.sin(math.radians(3.0)):.4f}"
        )


class TestAbsoluteDihedralStillWorks:
    """Same geometry but with ``RelativeDihedralFlag=0`` (absolute):
    Section 2 = "0°" means flat-horizontal, so Z stays at Section 1's
    value. Pin this so the absolute branch doesn't regress."""

    def test_section_2_flat_when_absolute(self, aeroplane, ctx):
        parms = _build_parms(
            n_xsec=3,
            sections=[
                {
                    "Root_Chord": 1.0,
                    "Tip_Chord": 0.8,
                    "Span": 4.5,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 3.0,
                    "Twist": 0.0,
                },
                {
                    "Tip_Chord": 0.4,
                    "Span": 3.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,  # absolute → flat-horizontal
                    "Twist": 0.0,
                },
            ],
        )
        _handle_wing("wing-gid", "MainWing", aeroplane, ctx, _VspStub(3, parms))
        wing = aeroplane.wings["MainWing"]
        s1 = wing.x_secs[1]
        s2 = wing.x_secs[2]
        # Section 1: z = 4.5·sin(3°). Section 2: z stays the same
        # (cum_dihedral resets to absolute 0°).
        assert s2.xyz_le[2] == pytest.approx(s1.xyz_le[2], rel=1e-9), (
            "absolute mode: Section 2 with 0° dihedral must NOT carry the prior section's slope"
        )
        # y advances by span exactly (cos(0°) = 1).
        assert s2.xyz_le[1] == pytest.approx(s1.xyz_le[1] + 3.0, rel=1e-9)


# ---------------------------------------------------------------------------
# Twist relative / absolute
# ---------------------------------------------------------------------------


class TestRelativeTwist:
    """Same flag pattern for Twist. ``RelativeTwistFlag=1`` →
    each XSec's twist is incremental over the previous; in absolute
    mode it replaces."""

    def test_relative_twist_accumulates(self, aeroplane, ctx):
        parms = _build_parms(
            n_xsec=3,
            sections=[
                {
                    "Root_Chord": 1.0,
                    "Tip_Chord": 0.8,
                    "Span": 1.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,
                    "Twist": 2.0,
                },
                {
                    "Tip_Chord": 0.5,
                    "Span": 1.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,
                    "Twist": -3.0,
                },
            ],
            relative_twist=1,
        )
        _handle_wing("wing-gid", "MainWing", aeroplane, ctx, _VspStub(3, parms))
        wing = aeroplane.wings["MainWing"]
        # Section 1 twist: 2°. Section 2 twist: 2° + (-3°) = -1°.
        assert wing.x_secs[1].twist == pytest.approx(2.0, rel=1e-9)
        assert wing.x_secs[2].twist == pytest.approx(-1.0, rel=1e-9)

    def test_absolute_twist_replaces(self, aeroplane, ctx):
        # Same parms but flag absent → absolute mode.
        parms = _build_parms(
            n_xsec=3,
            sections=[
                {
                    "Root_Chord": 1.0,
                    "Tip_Chord": 0.8,
                    "Span": 1.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,
                    "Twist": 2.0,
                },
                {
                    "Tip_Chord": 0.5,
                    "Span": 1.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 0.0,
                    "Twist": -3.0,
                },
            ],
        )
        _handle_wing("wing-gid", "MainWing", aeroplane, ctx, _VspStub(3, parms))
        wing = aeroplane.wings["MainWing"]
        # Each XSec's twist replaces, not adds.
        assert wing.x_secs[1].twist == pytest.approx(2.0, rel=1e-9)
        assert wing.x_secs[2].twist == pytest.approx(-3.0, rel=1e-9)


# ---------------------------------------------------------------------------
# Cosine-correct Y-step (winglet / V-tail at high dihedral)
# ---------------------------------------------------------------------------


class TestCosineCorrectYStep:
    """Pre-fix code used ``cum_y += span`` (small-angle approximation,
    ≈ correct up to ~5°). At 60° dihedral the error is large:
    real Y-step is span · cos(60°) = 0.5 · span. Pin that against the
    analytical value so winglets / V-tail surfaces import accurately."""

    def test_60deg_dihedral_y_step_uses_cosine(self, aeroplane, ctx):
        parms = _build_parms(
            n_xsec=2,
            sections=[
                {
                    "Root_Chord": 0.3,
                    "Tip_Chord": 0.2,
                    "Span": 1.0,
                    "Sweep": 0.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 60.0,
                    "Twist": 0.0,
                }
            ],
        )
        _handle_wing("wing-gid", "Winglet", aeroplane, ctx, _VspStub(2, parms))
        wing = aeroplane.wings["Winglet"]
        tip = wing.x_secs[1]
        # Y must be span · cos(60°) = 0.5. Pre-fix gave 1.0 (the bare span).
        assert tip.xyz_le[1] == pytest.approx(0.5, rel=1e-9), (
            "y-step on a 60° dihedral surface must use cos(60°); "
            "pre-fix bug would give y = 1.0 (raw span)"
        )
        # Z = span · sin(60°) ≈ 0.866.
        assert tip.xyz_le[2] == pytest.approx(math.sin(math.radians(60.0)), rel=1e-9)
