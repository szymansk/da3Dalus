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
    _fit_n_from_xsec_points,
    _rounded_rect_to_n,
    _sample_xsec_yz,
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
    "SHIFT_LE": 7,
    "SHIFT_MID": 8,
    "SHIFT_TE": 9,
}


# Map shape name → (width-key, height-key) on the per-xsec dict. The
# stub uses these to expose ``GetXSecWidth``/``GetXSecHeight`` — the
# shape-agnostic OpenVSP accessors that the production handler relies
# on as of gh-709.
_WIDTH_HEIGHT_KEYS: dict[str, tuple[str | None, str | None]] = {
    "POINT": (None, None),
    "CIRCLE": ("Circle_Diameter", "Circle_Diameter"),
    "ELLIPSE": ("Ellipse_Width", "Ellipse_Height"),
    "SUPER_ELLIPSE": ("Super_Width", "Super_Height"),
    "ROUNDED_RECTANGLE": ("RoundedRect_Width", "RoundedRect_Height"),
    "GENERAL_FUSE": ("width", "height"),
    "FILE_FUSE": ("width", "height"),
    "SHIFT_LE": ("width", "height"),
    "SHIFT_MID": ("width", "height"),
    "SHIFT_TE": ("width", "height"),
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

    # gh-709: production handler now reads bounding W/H via shape-agnostic
    # ``GetXSecWidth``/``GetXSecHeight``. Stub them by looking up the
    # per-shape width/height keys defined above.
    def _xsec_dim(xs_id: str, axis: str) -> float:
        idx = int(xs_id.split("_", 1)[1])
        xs = xsecs[idx]
        shape_name = xs["shape"]
        w_key, h_key = _WIDTH_HEIGHT_KEYS.get(shape_name, (None, None))
        key = w_key if axis == "W" else h_key
        if key is None or key not in xs:
            return 0.0
        return float(xs[key])

    fake.GetXSecWidth = lambda xs_id: _xsec_dim(xs_id, "W")
    fake.GetXSecHeight = lambda xs_id: _xsec_dim(xs_id, "H")

    # Parm routing per OpenVSP 3.50 convention (gh-711): Length lives on
    # the fuselage container in group Design; XForm translation/rotation
    # live on the fuselage container in group XForm. The per-XSec
    # position parms (XLocPercent etc.) cannot be reached via
    # ``FindParm(xs_id, ..., "XSec")`` — real OpenVSP 3.50 returns ""
    # for that call. They are only reachable via ``GetXSecParm`` (see
    # ``_get_xsec_parm`` stub above, which already routes ``x_pct``/
    # ``y_pct``/``z_pct`` through the right XSec keys).
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
        # gh-715: Sym_Planar_Flag lives in group ``Sym`` on the Geom.
        if container == fuse_id and group == "Sym" and parm == "Sym_Planar_Flag":
            if "Sym_Planar_Flag" not in xform:
                return ""
            return "PSYM::Sym_Planar_Flag"
        # XSec-position parms: real OpenVSP 3.50 returns "" here — the
        # handler must reach them via GetXSecParm instead.
        return ""

    # Route GetXSecParm so position parms (XLocPercent/YLocPercent/
    # ZLocPercent) work via the same key lookup as the shape parms.
    _orig_get_xsec_parm = fake.GetXSecParm

    def _get_xsec_parm_routed(xs_id: str, name: str) -> str:
        if name in _LOC_KEY:
            idx = int(xs_id.split("_", 1)[1])
            loc_key = _LOC_KEY[name]
            if loc_key not in xsecs[idx]:
                return ""
            return f"PXSEC::{xs_id}::{name}"
        return _orig_get_xsec_parm(xs_id, name)

    fake.GetXSecParm = _get_xsec_parm_routed

    def _get_parm_val_router(pid):
        if not pid:
            return 0.0
        if pid == "PFUSE::Length":
            return float(length)
        if pid == "PSYM::Sym_Planar_Flag":
            return float(xform.get("Sym_Planar_Flag", 0))
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
# gh-709: shape-agnostic bounding-reader for unsupported shapes
# ---------------------------------------------------------------------------


class TestShapeAgnosticBoundingReader:
    """For shape types we cannot decode parm-by-parm (GENERAL_FUSE,
    SHIFT_LE/MID/TE, FILE_FUSE) the handler must fall back to OpenVSP's
    shape-agnostic ``GetXSecWidth``/``GetXSecHeight`` accessors instead
    of returning the hard-coded ``(0.5, 0.5, 2.0)`` placeholder that
    used to produce identical-barrel imports (Cessna 172, gh-709).
    """

    def test_general_fuse_reads_real_bounding_box(self):
        # Mid-fuselage xsec of a Cessna 172 has W=1.10, H=1.45.
        fake = _make_fuse_vsp(
            xsecs=[{"shape": "GENERAL_FUSE", "x_pct": 0.5, "width": 1.10, "height": 1.45}]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["GENERAL_FUSE"], ctx)
        assert a == pytest.approx(0.55)
        assert b == pytest.approx(0.725)
        # Bounding ellipse approximation — n defaults to 2.
        assert n == pytest.approx(2.0)
        # Info-warning surfaces the approximation so the user knows
        # the exact outline was lost.
        assert any("approxim" in w.reason.lower() for w in ctx.warnings)

    def test_shift_le_endcap_returns_zero(self):
        # SHIFT_LE on a real fuselage is the nose / tail cap — bounding
        # W and H are 0, so the xsec must collapse to a point.
        fake = _make_fuse_vsp(
            xsecs=[{"shape": "SHIFT_LE", "x_pct": 0.0, "width": 0.0, "height": 0.0}]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["SHIFT_LE"], ctx)
        assert a == 0.0
        assert b == 0.0
        assert n == pytest.approx(2.0)

    def test_shift_te_with_real_dimensions(self):
        # SHIFT_TE xsec[1] on Cessna 172 has W=H=0.28 — it's NOT an
        # endcap, just a loft-control marker on an ellipse-shaped curve.
        fake = _make_fuse_vsp(
            xsecs=[{"shape": "SHIFT_TE", "x_pct": 0.05, "width": 0.28, "height": 0.28}]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["SHIFT_TE"], ctx)
        assert a == pytest.approx(0.14)
        assert b == pytest.approx(0.14)

    def test_file_fuse_reads_real_bounding_box(self):
        fake = _make_fuse_vsp(
            xsecs=[{"shape": "FILE_FUSE", "x_pct": 0.5, "width": 0.8, "height": 0.6}]
        )
        ctx = ImportContext()
        a, b, n = _shape_to_super_ellipse(fake, "XS_0", _SHAPES["FILE_FUSE"], ctx)
        assert a == pytest.approx(0.4)
        assert b == pytest.approx(0.3)
        assert n == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# gh-709 regression: Cessna 172 fuselage shape mix
# ---------------------------------------------------------------------------


class TestCessna172FuselageRegression:
    """The Cessna 172 fuselage in cessna172.vsp3 has 10 xsecs with a
    mix of SHIFT_LE, SHIFT_TE, SUPER_ELLIPSE, and GENERAL_FUSE. The
    pre-gh-709 handler returned 0.5/0.5 for 4 of 10 xsecs, producing
    a chain of identical barrels. This test replays the exact shape
    pattern and asserts the import now matches reality.
    """

    def test_mixed_xsecs_produce_tapered_fuselage(self, tmp_path, monkeypatch):
        f = tmp_path / "cessna_replay.vsp3"
        f.write_text("")
        # Values lifted from a real probe of cessna172.vsp3 (see
        # gh-709 description).
        xsecs = [
            {"shape": "SHIFT_LE", "x_pct": 0.00, "width": 0.00, "height": 0.00},
            {"shape": "SHIFT_TE", "x_pct": 0.05, "width": 0.28, "height": 0.28},
            {"shape": "SUPER_ELLIPSE", "x_pct": 0.15, "Super_Width": 0.82, "Super_Height": 0.52,
             "Super_M": 2.0, "Super_N": 2.0},
            {"shape": "SUPER_ELLIPSE", "x_pct": 0.30, "Super_Width": 1.00, "Super_Height": 0.98,
             "Super_M": 2.0, "Super_N": 2.0},
            {"shape": "SUPER_ELLIPSE", "x_pct": 0.45, "Super_Width": 1.07, "Super_Height": 1.04,
             "Super_M": 2.0, "Super_N": 2.0},
            {"shape": "GENERAL_FUSE", "x_pct": 0.60, "width": 1.10, "height": 1.45},
            {"shape": "GENERAL_FUSE", "x_pct": 0.75, "width": 1.10, "height": 1.22},
            {"shape": "SUPER_ELLIPSE", "x_pct": 0.85, "Super_Width": 0.97, "Super_Height": 0.88,
             "Super_M": 2.0, "Super_N": 2.0},
            {"shape": "SUPER_ELLIPSE", "x_pct": 0.95, "Super_Width": 0.10, "Super_Height": 0.36,
             "Super_M": 2.0, "Super_N": 2.0},
            {"shape": "SHIFT_LE", "x_pct": 1.00, "width": 0.00, "height": 0.00},
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=7.23)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)

        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        # Endcaps collapse to a point.
        assert fuse.x_secs[0].a == 0.0
        assert fuse.x_secs[0].b == 0.0
        assert fuse.x_secs[-1].a == 0.0
        # Middle GENERAL_FUSE sections must have the real bounding box,
        # NOT the legacy 0.5/0.5 fallback.
        gen_fuse_a = fuse.x_secs[5]
        assert gen_fuse_a.a == pytest.approx(0.55)
        assert gen_fuse_a.b == pytest.approx(0.725)
        gen_fuse_b = fuse.x_secs[6]
        assert gen_fuse_b.a == pytest.approx(0.55)
        assert gen_fuse_b.b == pytest.approx(0.61)
        # No two adjacent non-endcap xsecs may share the same (a, b) —
        # that's the chain-of-identical-barrels signature.
        bodies = fuse.x_secs[1:-1]
        for left, right in zip(bodies, bodies[1:], strict=False):
            assert (left.a, left.b) != (right.a, right.b)

    def test_sym_planar_flag_xz_sets_symmetric_true(self, tmp_path, monkeypatch):
        """gh-715: Sym_Planar_Flag = 2 (XZ) on the Geom must map to
        FuselageSchema.symmetric = True so downstream consumers
        mirror the half-fuselage automatically.
        """
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.0},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.3},
        ]
        fake = _make_fuse_vsp(
            xsecs=xsecs, length=1.0, xform={"Sym_Planar_Flag": 2}
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert fuse.symmetric is True

    def test_sym_planar_flag_none_keeps_symmetric_false(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.0},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.3},
        ]
        # Sym=0 (none) — typical for main fuselages on the symmetry plane.
        fake = _make_fuse_vsp(
            xsecs=xsecs, length=1.0, xform={"Sym_Planar_Flag": 0}
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert fuse.symmetric is False

    def test_sym_planar_flag_unsupported_warns_and_falls_back(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        xsecs = [
            {"shape": "CIRCLE", "x_pct": 0.0, "Circle_Diameter": 0.0},
            {"shape": "CIRCLE", "x_pct": 1.0, "Circle_Diameter": 0.3},
        ]
        # Sym=4 (YZ) — top/bottom mirror is unusual for fuselages.
        fake = _make_fuse_vsp(
            xsecs=xsecs, length=1.0, xform={"Sym_Planar_Flag": 4}
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert fuse.symmetric is False
        # Info warning surfaces the unsupported mode.
        sym_warnings = [
            w for w in result.warnings
            if w.component_type == "FUSELAGE" and "Sym_Planar_Flag" in w.reason
        ]
        assert sym_warnings, [w.reason for w in result.warnings]

    def test_real_cessna_xsec_positions_match(self, tmp_path, monkeypatch):
        """gh-711: every xsec X/Z position must match the real Cessna
        172 values within 1 mm, not the ``i/(n-1)``-fallback evenly
        spaced grid the broken FindParm path produced.
        """
        f = tmp_path / "cessna_pos.vsp3"
        f.write_text("")
        length = 7.23
        # (XLocPercent, ZLocPercent) probed from cessna172.vsp3.
        positions = [
            (0.0000, 0.0000),
            (0.0567, 0.0000),
            (0.0747, -0.0069),
            (0.1494, -0.0221),
            (0.2102, -0.0194),
            (0.2752, 0.0124),
            (0.5076, 0.0194),
            (0.5864, 0.0097),
            (0.9862, 0.0429),
            (1.0000, 0.0429),
        ]
        # Minimal xsec list — only the position parms matter here, shape
        # values are stubs sufficient for the bounding reader to return
        # something non-degenerate.
        xsecs = [
            {
                "shape": "SUPER_ELLIPSE", "x_pct": x, "z_pct": z,
                "Super_Width": 0.5, "Super_Height": 0.5,
                "Super_M": 2.0, "Super_N": 2.0,
            }
            for x, z in positions
        ]
        fake = _make_fuse_vsp(xsecs=xsecs, length=length)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)

        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        for i, (x_pct, z_pct) in enumerate(positions):
            expected_x = x_pct * length
            expected_z = z_pct * length
            assert fuse.x_secs[i].xyz[0] == pytest.approx(expected_x, abs=1e-3), (
                f"xsec[{i}] X drift: expected {expected_x:.4f} m, "
                f"got {fuse.x_secs[i].xyz[0]:.4f} m"
            )
            assert fuse.x_secs[i].xyz[2] == pytest.approx(expected_z, abs=1e-3), (
                f"xsec[{i}] Z versatz lost: expected {expected_z:+.4f} m, "
                f"got {fuse.x_secs[i].xyz[2]:+.4f} m"
            )


# ---------------------------------------------------------------------------
# _rounded_rect_to_n heuristic
# ---------------------------------------------------------------------------


class TestSuperEllipseFit:
    """gh-713: ``_fit_n_from_xsec_points`` recovers the super-ellipse
    exponent ``n`` from a sampled outline. The bounding-box half-axes
    ``a`` and ``b`` are inputs (we trust ``GetXSecWidth/Height`` for
    those); only ``n`` is free.
    """

    @staticmethod
    def _sample_superellipse(a: float, b: float, n: float, n_points: int = 24) -> list[tuple[float, float]]:
        """Sample n_points evenly in parameter ``t ∈ [0, 2π)`` from the
        super-ellipse ``|y/a|^n + |z/b|^n = 1``.
        """
        import math

        pts: list[tuple[float, float]] = []
        for k in range(n_points):
            t = 2.0 * math.pi * k / n_points
            ct, st = math.cos(t), math.sin(t)
            # Parametric form: y = a · sign(ct) · |ct|^(2/n), z = b · sign(st) · |st|^(2/n)
            y = a * (1.0 if ct >= 0 else -1.0) * abs(ct) ** (2.0 / n)
            z = b * (1.0 if st >= 0 else -1.0) * abs(st) ** (2.0 / n)
            pts.append((y, z))
        return pts

    def test_recovers_ellipse_n_equals_2(self):
        pts = self._sample_superellipse(a=1.0, b=0.5, n=2.0)
        n = _fit_n_from_xsec_points(pts, a=1.0, b=0.5)
        assert n == pytest.approx(2.0, abs=0.1)

    def test_recovers_n_equals_4(self):
        # Squarer profile — classic Mansardendach shape.
        pts = self._sample_superellipse(a=0.55, b=0.725, n=4.0)
        n = _fit_n_from_xsec_points(pts, a=0.55, b=0.725)
        assert n == pytest.approx(4.0, abs=0.1)

    def test_recovers_diamond_n_equals_1(self):
        pts = self._sample_superellipse(a=1.0, b=1.0, n=1.0)
        n = _fit_n_from_xsec_points(pts, a=1.0, b=1.0)
        assert n == pytest.approx(1.0, abs=0.15)

    def test_clamps_for_degenerate_axes(self):
        # If ``a`` or ``b`` is zero (endcap-like) the fit is undefined —
        # must return the safe default n=2 without raising.
        assert _fit_n_from_xsec_points([(0.0, 0.0)], a=0.0, b=0.5) == pytest.approx(2.0)
        assert _fit_n_from_xsec_points([(0.5, 0.0)], a=1.0, b=0.0) == pytest.approx(2.0)

    def test_clamps_for_too_few_points(self):
        # Need at least a handful of off-axis samples to fit a curve.
        assert _fit_n_from_xsec_points([], a=1.0, b=0.5) == pytest.approx(2.0)
        assert _fit_n_from_xsec_points([(0.5, 0.25)], a=1.0, b=0.5) == pytest.approx(2.0)

    def test_clamps_to_sane_range(self):
        # Random scatter inside the bounding box — fit must stay in [1, 50].
        pts = [(0.3, 0.1), (0.5, 0.2), (0.2, 0.4), (-0.3, -0.1), (-0.5, 0.2)]
        n = _fit_n_from_xsec_points(pts, a=1.0, b=0.5)
        assert 1.0 <= n <= 50.0


class TestSampleXsecYz:
    """``_sample_xsec_yz`` wraps ``vsp.ComputeXSecPnt`` into a defensive
    centroid-subtracted list — must degrade safely when the API is
    missing or throws, and must centre the sample on the bounding
    middle so the super-ellipse fit downstream sees an origin-centred
    cloud.
    """

    def _make_minimal_vsp(self, with_compute=True, raise_on_compute=False, pts=None):
        fake = SimpleNamespace()
        if with_compute:
            class _P:
                def __init__(self, x, y, z):
                    self._x, self._y, self._z = x, y, z
                def x(self): return self._x
                def y(self): return self._y
                def z(self): return self._z

            samples = pts or [(0.0, y, z) for y, z in [
                (0.5, 0.5), (-0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)
            ]]

            def _compute(_xs_id, fract):
                if raise_on_compute:
                    raise RuntimeError("API drift")
                k = int(fract * len(samples)) % len(samples)
                return _P(*samples[k])

            fake.ComputeXSecPnt = _compute
        return fake

    def test_returns_empty_when_compute_missing(self):
        fake = SimpleNamespace()  # no ComputeXSecPnt at all
        assert _sample_xsec_yz(cast(ModuleType, fake), "XS_0") == []

    def test_returns_empty_when_compute_raises(self):
        fake = self._make_minimal_vsp(raise_on_compute=True)
        assert _sample_xsec_yz(cast(ModuleType, fake), "XS_0") == []

    def test_subtracts_bounding_midpoint(self):
        # All sample points sit at (y=2, z=3) — centred → (0, 0).
        fake = self._make_minimal_vsp(pts=[(0.0, 2.0, 3.0)] * 8)
        out = _sample_xsec_yz(cast(ModuleType, fake), "XS_0", n_points=8)
        assert len(out) == 8
        for y, z in out:
            assert y == pytest.approx(0.0)
            assert z == pytest.approx(0.0)


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
