"""Unit tests for the OpenVSP SS_CONTROL → TrailingEdgeDevice handler (gh-644).

Per the scope-clarification comment on #644 (RC-scaling focus):

* In scope: basic SS_CONTROL → TrailingEdgeDevice mapping (rel_chord
  root/tip, deflection, symmetric inherited from wing).
* Out of scope: CSGroup-gain matrix, antisymmetric flag, role
  inference, LE-devices (warn+skip), CSGroup naming heuristic.

The handler is invoked from the WING handler — we test it through
``import_vsp3`` with a fake-vsp that exposes both a WING geom and
sub-surfaces on that geom.
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_importer import import_vsp3
from app.converters.openvsp_ss_control import _u_to_segment_index, register
from app.converters.openvsp_wing_handler import register as register_wing


# ---------------------------------------------------------------------------
# Fake vsp factory — wing geom + N sub-surfaces (some SS_CONTROL)
# ---------------------------------------------------------------------------


def _make_wing_with_sub_surfaces(
    *,
    wing_id: str = "WING1",
    name: str = "MainWing",
    n_sec: int = 2,
    sub_surfaces: list[dict] | None = None,
) -> ModuleType:
    """Build fake vsp module with a WING and a list of sub-surfaces.

    sub_surfaces entries: ``{id, name, type, u_start, u_end, c_root,
    c_tip, deflection, le_flag, eta_flag, eta_start, eta_end}``.
    type ∈ {SS_CONTROL, SS_LINE, ...}; only SS_CONTROL is processed.
    """
    sub_surfaces = sub_surfaces or []

    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
    fake.LEN_M = 2
    fake.SYM_XY = 1
    fake.SYM_XZ = 2
    fake.SYM_YZ = 4
    fake.XS_FOUR_SERIES = 7
    fake.XS_POINT = 0
    fake.SS_LINE = 0
    fake.SS_RECTANGLE = 1
    fake.SS_ELLIPSE = 2
    fake.SS_CONTROL = 3
    fake.SS_FINITE_LINE = 4

    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.SetLengthUnit = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: "VEH"
    fake.FindGeoms = lambda: [wing_id]
    fake.GetGeomName = lambda gid: name if gid == wing_id else ""
    fake.GetGeomTypeName = lambda gid: "WING" if gid == wing_id else ""

    XSURF = "XSURF_WING"
    fake.GetXSecSurf = lambda gid, _i: XSURF
    fake.GetNumXSec = lambda xs: n_sec + 1
    fake.GetXSec = lambda xs, i: f"XS_{i}"
    fake.GetXSecShape = lambda xs: fake.XS_FOUR_SERIES

    # Sub-surfaces
    fake.GetSubSurfIDVec = lambda gid: [s["id"] for s in sub_surfaces]
    fake.GetSubSurfType = lambda sid: next(
        (s.get("type", fake.SS_CONTROL) for s in sub_surfaces if s["id"] == sid),
        fake.SS_CONTROL,
    )
    fake.GetSubSurfIndex = lambda sid: next(
        (i for i, s in enumerate(sub_surfaces) if s["id"] == sid), 0
    )
    fake.GetSubSurfName = lambda sid: next((s["name"] for s in sub_surfaces if s["id"] == sid), "")

    # Per-section planform parms.
    section_default = {
        "Span": 5.0,
        "Root_Chord": 1.0,
        "Tip_Chord": 0.5,
        "Sweep": 0.0,
        "Sweep_Location": 0.25,
        "Dihedral": 0.0,
        "Twist": 0.0,
    }
    parms: dict[tuple[str, str, str], float] = {
        (wing_id, "Sym_Planar_Flag", "Sym"): float(fake.SYM_XZ),
    }
    for i in range(1, n_sec + 1):
        for k, v in section_default.items():
            parms[(wing_id, k, f"XSec_{i}")] = v

    # SS_Control_<n> group parms: U/Eta extent, chord fractions, deflection, LE_Flag.
    for s in sub_surfaces:
        n = fake.GetSubSurfIndex(s["id"]) + 1
        grp = f"SS_Control_{n}"
        parms[(wing_id, "UStart", grp)] = float(s.get("u_start", 0.6))
        parms[(wing_id, "UEnd", grp)] = float(s.get("u_end", 0.95))
        parms[(wing_id, "EtaFlag", grp)] = 1.0 if s.get("eta_flag") else 0.0
        parms[(wing_id, "EtaStart", grp)] = float(s.get("eta_start", 0.6))
        parms[(wing_id, "EtaEnd", grp)] = float(s.get("eta_end", 0.95))
        parms[(wing_id, "Length_C_Start", grp)] = float(s.get("c_root", 0.25))
        parms[(wing_id, "Length_C_End", grp)] = float(s.get("c_tip", 0.25))
        parms[(wing_id, "LE_Flag", grp)] = 1.0 if s.get("le_flag") else 0.0
        parms[(wing_id, "Deflection", grp)] = float(s.get("deflection", 0.0))

    def _find_parm(container, parm, group):
        key = (container, parm, group)
        if key in parms:
            return f"PID::{container}::{group}::{parm}"
        return ""

    def _get_parm_val(pid):
        if not pid:
            return 0.0
        _, container, group, parm = pid.split("::", 3)
        return parms.get((container, parm, group), 0.0)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val
    fake.GetXSecParm = lambda xs, name: ""  # no airfoil parms in this fake

    return cast(ModuleType, fake)


@pytest.fixture(autouse=True)
def _clean_handlers():
    openvsp_importer._HANDLERS.clear()
    openvsp_importer._POST_PASSES.clear()
    register_wing()
    register()
    yield
    openvsp_importer._HANDLERS.clear()
    openvsp_importer._POST_PASSES.clear()


# ---------------------------------------------------------------------------
# _u_to_segment_index helper
# ---------------------------------------------------------------------------


class TestUToSegmentIndex:
    def test_u_at_segment_center_returns_that_segment(self):
        # 2-segment wing → segment 1 covers u in [0, 0.5], segment 2 covers [0.5, 1].
        # NB: u in OpenVSP is typically the parametric coordinate; we
        # approximate by linear distribution.
        assert _u_to_segment_index(u=0.25, n_sec=2) == 1
        assert _u_to_segment_index(u=0.75, n_sec=2) == 2

    def test_u_at_outermost_returns_last_segment(self):
        assert _u_to_segment_index(u=1.0, n_sec=3) == 3

    def test_u_at_root_returns_first_segment(self):
        assert _u_to_segment_index(u=0.0, n_sec=3) == 1

    def test_u_outside_range_clamps(self):
        assert _u_to_segment_index(u=-0.5, n_sec=2) == 1
        assert _u_to_segment_index(u=2.0, n_sec=2) == 2


# ---------------------------------------------------------------------------
# Aileron-like SS_CONTROL → TED
# ---------------------------------------------------------------------------


class TestSsControlImport:
    def test_aileron_creates_ted_on_outer_segment(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_with_sub_surfaces(
            n_sec=2,
            sub_surfaces=[
                {
                    "id": "SS_AIL",
                    "name": "Aileron",
                    "type": 3,  # SS_CONTROL
                    "u_start": 0.7,
                    "u_end": 0.95,
                    "c_root": 0.25,
                    "c_tip": 0.25,
                    "deflection": 0.0,
                    "le_flag": False,
                }
            ],
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        # The aileron lands on the outer segment — xsec 1 (segment-2's
        # inboard xsec) carries the TED.
        outer_seg = wing.x_secs[1]
        assert outer_seg.trailing_edge_device is not None
        ted = outer_seg.trailing_edge_device
        # rel_chord_* per scope: directly from Length_C_*.
        assert ted.rel_chord_root == pytest.approx(1.0 - 0.25)
        assert ted.rel_chord_tip == pytest.approx(1.0 - 0.25)
        # Symmetric inherited from wing (SYM_XZ → True).
        assert ted.symmetric is True
        # No CSGroup gain inference per scope clarification — role is OTHER.
        from app.schemas.aeroplaneschema import ControlSurfaceRole

        assert ted.role == ControlSurfaceRole.OTHER

    def test_le_device_emits_warning_and_skips(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_with_sub_surfaces(
            n_sec=2,
            sub_surfaces=[
                {
                    "id": "SS_SLAT",
                    "name": "Slat",
                    "type": 3,
                    "u_start": 0.7,
                    "u_end": 0.95,
                    "c_root": 0.25,
                    "c_tip": 0.25,
                    "le_flag": True,
                }
            ],
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        # No TED on any xsec.
        for xs in wing.x_secs:
            assert xs.trailing_edge_device is None
        # Warning about LE device.
        assert any(
            "leading" in w.reason.lower() or "le" in w.reason.lower() for w in result.warnings
        )

    def test_non_control_sub_surface_is_ignored(self, tmp_path, monkeypatch):
        """SS_LINE / SS_RECTANGLE etc. are not processed."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_with_sub_surfaces(
            n_sec=1,
            sub_surfaces=[
                {"id": "SS_L", "name": "Marker", "type": 0},  # SS_LINE
            ],
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        for xs in wing.x_secs:
            assert xs.trailing_edge_device is None

    def test_eta_flag_uses_eta_extent(self, tmp_path, monkeypatch):
        """When EtaFlag=1, U-extent is read from EtaStart/EtaEnd instead."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_with_sub_surfaces(
            n_sec=2,
            sub_surfaces=[
                {
                    "id": "SS_F",
                    "name": "Flap",
                    "type": 3,
                    "u_start": 0.0,  # wrong values — should be ignored
                    "u_end": 0.1,
                    "eta_flag": True,
                    "eta_start": 0.7,
                    "eta_end": 0.95,
                    "c_root": 0.30,
                    "c_tip": 0.30,
                }
            ],
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        outer = wing.x_secs[1]
        assert outer.trailing_edge_device is not None
        ted = outer.trailing_edge_device
        assert ted.rel_chord_root == pytest.approx(1.0 - 0.30)
        assert ted.rel_chord_tip == pytest.approx(1.0 - 0.30)

    def test_asymmetric_wing_yields_non_symmetric_ted(self, tmp_path, monkeypatch):
        """If wing.symmetric=False (no SYM_XZ bit), TED inherits False."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_with_sub_surfaces(
            n_sec=1,
            sub_surfaces=[
                {
                    "id": "SS_A",
                    "name": "A",
                    "type": 3,
                    "u_start": 0.7,
                    "u_end": 0.95,
                    "c_root": 0.25,
                    "c_tip": 0.25,
                }
            ],
        )
        # Override Sym_Planar_Flag to 0 (no symmetry) by patching
        # GetParmVal directly — the FindParm closure cannot be reached.
        original_get = fake.GetParmVal

        def _patched_get(pid):
            if pid.endswith("Sym_Planar_Flag"):
                return 0.0
            return original_get(pid)

        fake.GetParmVal = _patched_get
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        outer = wing.x_secs[0]  # n_sec=1 → root is xsec[0], TED on segment 1 (xsec[0])
        # TED carries the wing's symmetric flag.
        assert outer.trailing_edge_device is not None
        assert outer.trailing_edge_device.symmetric is False
