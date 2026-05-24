"""Unit tests for the OpenVSP FUSELAGE handler (gh-643).

Covers super-ellipse-family XSec shape mapping (CIRCLE, ELLIPSE,
SUPER_ELLIPSE, ROUNDED_RECTANGLE, POINT) and the integration via
``import_vsp3``.

All tests run without the real OpenVSP package — they mock the
`openvsp` module via a fake factory.
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_fuselage_handler import (
    _rounded_rect_to_n,
    _shape_to_super_ellipse,
    register,
)
from app.converters.openvsp_importer import ImportContext, import_vsp3


# ---------------------------------------------------------------------------
# Fake vsp factory for FUSELAGE tests
# ---------------------------------------------------------------------------


# Map of xsec shape names → integer constants matching common OpenVSP defs.
_SHAPES = {
    "POINT": 0,
    "CIRCLE": 1,
    "ELLIPSE": 2,
    "SUPER_ELLIPSE": 3,
    "ROUNDED_RECTANGLE": 4,
    "GENERAL_FUSE": 5,
    "FILE_FUSE": 6,
}


def _make_fuse_vsp(
    *,
    fuse_id: str = "FUSE1",
    name: str = "Fuselage",
    length: float = 10.0,
    xsecs: list[dict] | None = None,
    xform: dict | None = None,
) -> ModuleType:
    """Build a fake `openvsp` module describing one FUSELAGE geom.

    ``xsecs`` is a list of dicts with keys:
      shape (str), x_pct (float), and shape-specific parms
      (Circle_Diameter, Ellipse_Width/Height, Super_Width/Height/M/N,
       RoundedRect_Width/Height/Radius).
    """
    xsecs = xsecs or []
    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
    fake.LEN_M = 2
    fake.SYM_XZ = 2
    for n, v in _SHAPES.items():
        setattr(fake, f"XS_{n}", v)

    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.SetLengthUnit = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: "VEH"
    fake.FindGeoms = lambda: [fuse_id]
    fake.GetGeomName = lambda gid: name if gid == fuse_id else ""
    fake.GetGeomTypeName = lambda gid: "FUSELAGE" if gid == fuse_id else ""

    XSURF = "XSURF_FUSE"
    fake.GetXSecSurf = lambda gid, _i: XSURF
    fake.GetNumXSec = lambda xs: len(xsecs)
    fake.GetXSec = lambda xs, i: f"XS_{i}"

    def _shape_for(xs_id: str) -> int:
        idx = int(xs_id.split("_", 1)[1])
        return _SHAPES[xsecs[idx]["shape"]]

    fake.GetXSecShape = _shape_for

    # Per-xsec parms accessed via GetXSecParm + GetParmVal.
    def _get_xsec_parm(xs_id: str, name: str) -> str:
        idx = int(xs_id.split("_", 1)[1])
        return f"PID::{xs_id}::{name}" if name in xsecs[idx] else ""

    def _get_parm_val(pid: str) -> float:
        if not pid:
            return 0.0
        _, xs_id, name = pid.split("::", 2)
        idx = int(xs_id.split("_", 1)[1])
        return float(xsecs[idx].get(name, 0.0))

    fake.GetXSecParm = _get_xsec_parm

    # Parm routing per OpenVSP 3.50 convention (gh-702): Length lives on
    # the fuselage container in group Design; XLocPercent/YLocPercent/
    # ZLocPercent live on EACH XSec container in group XSec; XForm
    # translation/rotation live on the fuselage container in group XForm.
    xform = xform or {}
    XFORM_PARMS = {
        "X_Location", "Y_Location", "Z_Location",
        "X_Rotation", "Y_Rotation", "Z_Rotation",
    }

    _LOC_KEY = {"XLocPercent": "x_pct", "YLocPercent": "y_pct", "ZLocPercent": "z_pct"}

    def _find_parm(container, parm, group):
        if container == fuse_id and parm == "Length" and group == "Design":
            return "PFUSE::Length"
        if container == fuse_id and group == "XForm" and parm in XFORM_PARMS:
            return f"PXFORM::{parm}"
        if container.startswith("XS_") and group == "XSec" and parm in _LOC_KEY:
            # Mirror real OpenVSP: return "" when the test dict doesn't
            # declare the corresponding *_pct key, so the handler's
            # fallback path is exercised.
            idx = int(container.split("_", 1)[1])
            if _LOC_KEY[parm] not in xsecs[idx]:
                return ""
            return f"PXSEC::{container}::{parm}"
        return ""

    def _get_parm_val_router(pid):
        if not pid:
            return 0.0
        if pid == "PFUSE::Length":
            return float(length)
        if pid.startswith("PXFORM::"):
            return float(xform.get(pid.split("::", 1)[1], 0.0))
        if pid.startswith("PXSEC::"):
            _, xs_id, name = pid.split("::", 2)
            idx = int(xs_id.split("_", 1)[1])
            key = {"XLocPercent": "x_pct", "YLocPercent": "y_pct", "ZLocPercent": "z_pct"}[name]
            return float(xsecs[idx].get(key, 0.0))
        return _get_parm_val(pid)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val_router
    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# _shape_to_super_ellipse — pure mapping (no real vsp module needed)
# ---------------------------------------------------------------------------


class TestShapeToSuperEllipse:
    def test_circle(self):
        fake = _make_fuse_vsp(xsecs=[{"shape": "CIRCLE", "x_pct": 0.5, "Circle_Diameter": 2.0}])
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["CIRCLE"], ctx)
        assert a == pytest.approx(1.0)
        assert b == pytest.approx(1.0)
        assert n == pytest.approx(2.0)

    def test_ellipse(self):
        fake = _make_fuse_vsp(
            xsecs=[
                {
                    "shape": "ELLIPSE",
                    "x_pct": 0.5,
                    "Ellipse_Width": 3.0,
                    "Ellipse_Height": 2.0,
                }
            ]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["ELLIPSE"], ctx)
        assert a == pytest.approx(1.5)
        assert b == pytest.approx(1.0)
        assert n == pytest.approx(2.0)

    def test_super_ellipse_symmetric(self):
        fake = _make_fuse_vsp(
            xsecs=[
                {
                    "shape": "SUPER_ELLIPSE",
                    "x_pct": 0.5,
                    "Super_Width": 4.0,
                    "Super_Height": 2.0,
                    "Super_M": 3.0,
                    "Super_N": 3.0,
                }
            ]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["SUPER_ELLIPSE"], ctx)
        assert a == pytest.approx(2.0)
        assert b == pytest.approx(1.0)
        assert n == pytest.approx(3.0)
        assert ctx.warnings == []  # symmetric M/N → no warning

    def test_super_ellipse_asymmetric_warns(self):
        fake = _make_fuse_vsp(
            xsecs=[
                {
                    "shape": "SUPER_ELLIPSE",
                    "x_pct": 0.5,
                    "Super_Width": 4.0,
                    "Super_Height": 2.0,
                    "Super_M": 2.0,
                    "Super_N": 4.0,
                }
            ]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["SUPER_ELLIPSE"], ctx)
        assert n == pytest.approx(3.0)  # arithmetic mean
        assert len(ctx.warnings) == 1
        assert "asymmetric" in ctx.warnings[0].reason.lower()

    def test_rounded_rectangle_approximation(self):
        fake = _make_fuse_vsp(
            xsecs=[
                {
                    "shape": "ROUNDED_RECTANGLE",
                    "x_pct": 0.5,
                    "RoundedRect_Width": 4.0,
                    "RoundedRect_Height": 2.0,
                    "RoundedRect_Radius": 0.4,
                }
            ]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["ROUNDED_RECTANGLE"], ctx)
        assert a == pytest.approx(2.0)
        assert b == pytest.approx(1.0)
        # n should be > 2 (squarer than ellipse).
        assert n > 2.0
        # Should have a warning about the approximation.
        assert any("approxim" in w.reason.lower() for w in ctx.warnings)

    def test_point(self):
        fake = _make_fuse_vsp(xsecs=[{"shape": "POINT", "x_pct": 0.0}])
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["POINT"], ctx)
        assert a == 0.0
        assert b == 0.0
        assert n == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# _rounded_rect_to_n heuristic
# ---------------------------------------------------------------------------


class TestRoundedRectToN:
    def test_zero_radius_returns_high_exponent(self):
        # r=0 means perfect rectangle → very high n
        n = _rounded_rect_to_n(width=2.0, height=2.0, radius=0.0)
        assert n >= 10.0  # sufficient "squareness"

    def test_max_radius_returns_ellipse_exponent(self):
        # r = min(w,h)/2 — perfect circle/ellipse → n=2
        n = _rounded_rect_to_n(width=2.0, height=2.0, radius=1.0)
        assert n == pytest.approx(2.0, abs=0.5)

    def test_monotonic(self):
        ns = [
            _rounded_rect_to_n(width=2.0, height=2.0, radius=r) for r in (0.0, 0.25, 0.5, 0.75, 1.0)
        ]
        # decreasing as radius increases
        for a, b in zip(ns, ns[1:], strict=False):
            assert a >= b


# ---------------------------------------------------------------------------
# Integration via import_vsp3
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_handlers():
    openvsp_importer._HANDLERS.clear()
    register()
    yield
    openvsp_importer._HANDLERS.clear()


class TestFuselageImport:
    def test_tube_and_wing_constant_circle(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.5},
            {"shape": "CIRCLE", "x_pct": 0.3, "Circle_Diameter": 1.0},
            {"shape": "CIRCLE", "x_pct": 0.7, "Circle_Diameter": 1.0},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.2},
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=10.0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert "Fuselage" in (result.aeroplane.fuselages or {})
        fuse = result.aeroplane.fuselages["Fuselage"]
        assert len(fuse.x_secs) == 4
        # Station X positions = x_pct * length
        xs_x = [xs.xyz[0] for xs in fuse.x_secs]
        assert xs_x == pytest.approx([0.0, 3.0, 7.0, 10.0])
        # Centre xsec is a constant 1.0 m diameter → a=b=0.5, n=2
        mid = fuse.x_secs[1]
        assert mid.a == pytest.approx(0.5)
        assert mid.b == pytest.approx(0.5)
        assert mid.n == pytest.approx(2.0)

    def test_tapered_super_ellipse(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "POINT", "x_pct": 0.0},
            {
                "shape": "SUPER_ELLIPSE",
                "x_pct": 0.4,
                "Super_Width": 2.0,
                "Super_Height": 1.5,
                "Super_M": 2.5,
                "Super_N": 2.5,
            },
            {
                "shape": "SUPER_ELLIPSE",
                "x_pct": 0.6,
                "Super_Width": 2.0,
                "Super_Height": 1.5,
                "Super_M": 2.5,
                "Super_N": 2.5,
            },
            {"shape": "POINT", "x_pct": 1.0},
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=12.0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = result.aeroplane.fuselages["Fuselage"]
        # First and last are POINTs (a=b=0, n=2) — caps closed.
        assert fuse.x_secs[0].a == 0.0
        assert fuse.x_secs[-1].a == 0.0
        # Middle two are super-ellipses.
        assert fuse.x_secs[1].n == pytest.approx(2.5)
        assert fuse.x_secs[2].a == pytest.approx(1.0)

    def test_rounded_rect_emits_approximation_warning(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "POINT", "x_pct": 0.0},
            {
                "shape": "ROUNDED_RECTANGLE",
                "x_pct": 0.5,
                "RoundedRect_Width": 2.0,
                "RoundedRect_Height": 1.0,
                "RoundedRect_Radius": 0.1,
            },
            {"shape": "POINT", "x_pct": 1.0},
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=10.0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert any("approxim" in w.reason.lower() for w in result.warnings)

    def test_too_few_xsecs_skips_with_warning(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_fuse_vsp(xsecs=[{"shape": "POINT", "x_pct": 0.0}])
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert result.aeroplane.fuselages is None or not result.aeroplane.fuselages
        assert result.warnings


class TestFuselageXForm:
    """gh-702: Geom-level XForm (translation + intrinsic XYZ rotation)
    must be applied to every xsec xyz, identical pattern to the wing
    handler post-gh-698."""

    def test_pure_translation_offsets_all_xsecs(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.5},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.5},
        ]
        fake = _make_fuse_vsp(
            xsecs=xsecs,
            length=5.0,
            xform={"X_Location": 10.0, "Y_Location": -2.0, "Z_Location": 3.0},
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        # Every xsec is translated by (10, -2, 3) on top of its local xyz.
        assert fuse.x_secs[0].xyz == pytest.approx([10.0, -2.0, 3.0])
        assert fuse.x_secs[1].xyz == pytest.approx([15.0, -2.0, 3.0])

    def test_z_rotation_90_rotates_about_world_z(self, tmp_path, monkeypatch):
        # A fuselage laid along +X rotated 90° about Z should point along +Y.
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.2},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.2},
        ]
        fake = _make_fuse_vsp(
            xsecs=xsecs, length=4.0, xform={"Z_Rotation": 90.0}
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        # Local (4, 0, 0) → after Rz(90°) → (0, 4, 0)
        assert fuse.x_secs[1].xyz == pytest.approx([0.0, 4.0, 0.0], abs=1e-9)

    def test_y_rotation_neg80_with_translation_cessna_nose_strut(
        self, tmp_path, monkeypatch
    ):
        # Mirrors NoseStrut from the Cessna 172 file: translated to
        # (-1.22, 0, -1.0) and rotated by Y=-80°. A xsec at local
        # (1.5, 0, 0) → after Ry(-80°): (cos(-80)·1.5, 0, -sin(-80)·1.5)
        # = (0.260, 0, 1.477) → + translation = (-0.960, 0, 0.477).
        import math
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.1},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.1},
        ]
        fake = _make_fuse_vsp(
            xsecs=xsecs,
            length=1.5,
            xform={
                "X_Location": -1.22,
                "Z_Location": -1.0,
                "Y_Rotation": -80.0,
            },
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        # Local tip at (1.5, 0, 0). Ry(-80°): x→cos(-80)*1.5, z→-sin(-80)*1.5
        cos_t = math.cos(math.radians(-80.0))
        sin_t = math.sin(math.radians(-80.0))
        expected = [
            -1.22 + cos_t * 1.5,
            0.0,
            -1.0 + (-sin_t * 1.5),
        ]
        assert fuse.x_secs[1].xyz == pytest.approx(expected, abs=1e-9)


class TestFuselagePositionParms:
    """gh-702: per-XSec position parms live on the XSec, not on the
    parent fuselage with an _<i> suffix (corrects the earlier docstring
    + handler convention)."""

    def test_xsec_x_y_z_loc_percent_all_read(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "y_pct": 0.0, "z_pct": 0.0, "Circle_Diameter": 0.5},
            {"shape": "CIRCLE", "x_pct": 0.4, "y_pct": 0.05, "z_pct": -0.02, "Circle_Diameter": 0.5},
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=10.0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert fuse.x_secs[0].xyz == pytest.approx([0.0, 0.0, 0.0])
        assert fuse.x_secs[1].xyz == pytest.approx([4.0, 0.5, -0.2])

    def test_missing_position_parms_falls_back_to_even_spacing(
        self, tmp_path, monkeypatch
    ):
        # Provide xsec dicts WITHOUT any *_pct keys → handler falls
        # back to i/(n-1) for X, 0 for Y/Z. With length=8.0 and
        # n=5, the 3rd xsec (index 2) lands at 2/4 * 8 = 4.0.
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [{"shape": "CIRCLE", "Circle_Diameter": 0.5} for _ in range(5)]
        fake = _make_fuse_vsp(xsecs=xsecs, length=8.0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        xs_x = [xs.xyz[0] for xs in fuse.x_secs]
        assert xs_x == pytest.approx([0.0, 2.0, 4.0, 6.0, 8.0])
        # Y / Z all zero.
        assert all(xs.xyz[1] == 0.0 and xs.xyz[2] == 0.0 for xs in fuse.x_secs)
