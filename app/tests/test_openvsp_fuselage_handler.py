"""Unit tests for the OpenVSP FUSELAGE handler (gh-643).

Covers super-ellipse-family XSec shape mapping (CIRCLE, ELLIPSE,
SUPER_ELLIPSE, ROUNDED_RECTANGLE, POINT) and the integration via
``import_vsp3``.

All tests run without the real OpenVSP package — they mock the
`openvsp` module via a fake factory.
"""

from __future__ import annotations

from types import ModuleType

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
) -> ModuleType:
    """Build a fake `openvsp` module describing one FUSELAGE geom.

    ``xsecs`` is a list of dicts with keys:
      shape (str), x_pct (float), and shape-specific parms
      (Circle_Diameter, Ellipse_Width/Height, Super_Width/Height/M/N,
       RoundedRect_Width/Height/Radius).
    """
    xsecs = xsecs or []
    fake = ModuleType("openvsp")
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

    # Per-fuselage parms (Length, XLocPercent_<i>) accessed via FindParm.
    def _find_parm(container, parm, group):
        if container == fuse_id:
            if parm == "Length" and group == "Design":
                return "PFUSE::Length"
            if parm.startswith("XLocPercent_"):
                return f"PFUSE::{parm}"
        return ""

    def _get_parm_val_router(pid):
        if not pid:
            return 0.0
        if pid == "PFUSE::Length":
            return float(length)
        if pid.startswith("PFUSE::XLocPercent_"):
            idx = int(pid.split("_", 1)[1])
            return float(xsecs[idx].get("x_pct", 0.0))
        return _get_parm_val(pid)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val_router
    return fake


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
        for a, b in zip(ns, ns[1:]):
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
