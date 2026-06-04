"""Unit tests for the OpenVSP CUSTOM geom handler (gh-719).

Covers the CompPnt01-sampling path that lets us import Custom Geoms
(e.g. Generic Transport's main fuselage) which don't expose the
standard XSec-position parms.
"""

from __future__ import annotations

from types import ModuleType, SimpleNamespace
from typing import Any, Callable, Optional, cast

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_custom_handler import (
    _sample_station,
    register as register_custom,
)
from app.converters.openvsp_importer import import_vsp3


def _make_custom_vsp(
    *,
    gid: str = "CUST1",
    name: str = "Fuselage",
    n_main: int = 1,
    n_xsec_surfs: int = 1,
    n_xsecs: int = 5,
    has_comp: bool = True,
    surface: Optional[Callable[..., Any]] = None,  # (gid, surf, u, w) -> point
    sym_planar_flag: Optional[int] = None,
) -> ModuleType:
    """Build a fake openvsp module describing one Custom Geom."""
    fake = SimpleNamespace()
    fake.SYM_XZ = 2
    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: "VEH"
    fake.FindGeoms = lambda: [gid]
    fake.GetGeomName = lambda g: name if g == gid else ""
    fake.GetGeomTypeName = lambda g: "Custom" if g == gid else ""
    fake.GetNumMainSurfs = lambda g: n_main
    fake.GetNumXSecSurfs = lambda g: n_xsec_surfs

    def _find_parm(container, parm, group):
        if (
            container == gid
            and group == "Sym"
            and parm == "Sym_Planar_Flag"
            and sym_planar_flag is not None
        ):
            return "PSYM"
        return ""

    fake.FindParm = _find_parm
    fake.GetParmVal = lambda pid: float(sym_planar_flag) if pid == "PSYM" else 0.0

    if has_comp:
        # Default surface: a 20 m long body, 1.75 m diameter mid-section,
        # tapering nose at u=0 and tail at u=1. Captures the Generic
        # Transport shape closely enough for the regression test.
        def _default_surface(g, surf, u, w):
            import math

            length = 20.0
            x = -5.7 + u * length
            # Width/Height profile: 0 at u=0, peak 1.75 at u=0.25..0.5,
            # taper to 0.175/0.525 at u=0.75 then 0 at u=1.
            if u < 0.25:
                radius = u * 4 * 0.875
            elif u < 0.75:
                radius = 0.875
            else:
                radius = max(0.0, 0.875 * (1.0 - (u - 0.75) * 4.0))
            theta = 2 * math.pi * w
            y = radius * math.cos(theta)
            z = radius * math.sin(theta)
            return SimpleNamespace(x=lambda v=x: v, y=lambda v=y: v, z=lambda v=z: v)

        surface_fn = surface or _default_surface
        fake.CompPnt01 = lambda g, surf, u, w: surface_fn(g, surf, u, w)

    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# _sample_station — surface sweep returns centroid + half-axes
# ---------------------------------------------------------------------------


class TestSampleStation:
    def test_centred_circle(self):
        fake = _make_custom_vsp()
        cx, cy, cz, a, b = _sample_station(fake, "CUST1", u=0.5)
        # Mid-body: 1.75 m diameter circle, center on spine.
        assert a == pytest.approx(0.875, abs=0.01)
        assert b == pytest.approx(0.875, abs=0.01)
        assert cy == pytest.approx(0.0, abs=0.01)
        assert cz == pytest.approx(0.0, abs=0.01)
        # X is the mean over the sample — for a flat-X station it's
        # exactly the spine x value.
        assert cx == pytest.approx(-5.7 + 0.5 * 20.0)

    def test_endcap_collapses_to_point(self):
        fake = _make_custom_vsp()
        _cx, _cy, _cz, a, b = _sample_station(fake, "CUST1", u=0.0)
        assert a == pytest.approx(0.0, abs=0.01)
        assert b == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# _handle_custom integration via import_vsp3
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_handlers():
    openvsp_importer._HANDLERS.clear()
    register_custom()
    yield
    openvsp_importer._HANDLERS.clear()


class TestCustomImport:
    def test_generic_transport_style_body(self, tmp_path, monkeypatch):
        """A Custom Geom with a parametric surface lands as a 12-xsec
        fuselage with the right body length and mid-section width."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_custom_vsp()
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert "Fuselage" in (result.aeroplane.fuselages or {})
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert len(fuse.x_secs) == 12
        # First / last collapse to a point.
        assert fuse.x_secs[0].a == pytest.approx(0.0, abs=0.01)
        assert fuse.x_secs[-1].a == pytest.approx(0.0, abs=0.01)
        # Mid-body matches the default 1.75 m diameter.
        mid = fuse.x_secs[5]
        assert mid.a == pytest.approx(0.875, abs=0.01)
        # Length spans 20 m end-to-end.
        x_range = fuse.x_secs[-1].xyz[0] - fuse.x_secs[0].xyz[0]
        assert x_range == pytest.approx(20.0, abs=0.5)

    def test_skips_when_no_parametric_surface(self, tmp_path, monkeypatch):
        """Custom Geom without ``CompPnt01`` / surfaces hits a clean
        info-warning and skip — no crash."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_custom_vsp(has_comp=False, n_main=0, n_xsec_surfs=0)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert (result.aeroplane.fuselages or {}) == {}
        warnings = [
            w
            for w in result.warnings
            if w.component_type == "CUSTOM" and "no parametric surface" in w.reason
        ]
        assert warnings

    def test_sym_planar_xz_sets_symmetric(self, tmp_path, monkeypatch):
        """Sym_Planar_Flag=XZ on a Custom Geom must propagate to the
        FuselageSchema.symmetric flag (gh-715 path)."""
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_custom_vsp(sym_planar_flag=2)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert fuse.symmetric is True

    def test_sampling_failure_caught_as_warning(self, tmp_path, monkeypatch):
        """A CompPnt01 exception mid-sweep emits a warning + truncates
        the xsec list rather than crashing the whole import."""
        f = tmp_path / "x.vsp3"
        f.write_text("")

        def _flaky_surface(g, surf, u, w):
            if u > 0.5:
                raise RuntimeError("surface eval blew up")
            import math

            theta = 2 * math.pi * w
            return SimpleNamespace(
                x=lambda v=u * 10: v,
                y=lambda v=0.5 * math.cos(theta): v,
                z=lambda v=0.5 * math.sin(theta): v,
            )

        fake = _make_custom_vsp(surface=_flaky_surface)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        # Got at least 2 xsecs from the working u-range; subsequent
        # samples truncated.
        fuse = (result.aeroplane.fuselages or {})["Fuselage"]
        assert 2 <= len(fuse.x_secs) < 12
        # Warning surfaces.
        warnings = [
            w for w in result.warnings if w.component_type == "CUSTOM" and "blew up" in w.reason
        ]
        assert warnings
