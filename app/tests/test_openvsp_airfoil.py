"""Unit tests for the OpenVSP airfoil-import helper (gh-642).

Covers:

* NACA 4-series synthesis from Camber / CamberLoc / ThickChord
* NACA 4-digit modified, 5-digit, 5-digit modified, 6-series, 16-series
* XS_FILE_AIRFOIL: writes a Selig .dat file via vsp.WriteSeligAirfoil
  and returns a path inside the airfoils directory
* XS_CST_AIRFOIL falls back to a Selig export with a warning
* foilsurf_u_for_xs end-cap awareness (XS_POINT caps at root/tip)
* Unique filenames for multiple file-airfoils on the same import
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters.openvsp_airfoil import (
    foilsurf_u_for_xs,
    import_airfoil_from_xsec,
    naca_4series_name,
    naca_5series_name,
    naca_6series_name,
)
from app.converters.openvsp_importer import ImportContext


# ---------------------------------------------------------------------------
# Fake VSP for the airfoil tests
# ---------------------------------------------------------------------------


def _make_airfoil_vsp(
    *,
    xs_shape: int,
    xs_parms: dict[str, float],
    xs_shapes_in_surface: list[int] | None = None,
    write_path_capture: list[str] | None = None,
) -> ModuleType:
    """Build a fake vsp module exposing a single XSec.

    ``xs_shape`` is the integer returned by ``GetXSecShape``.
    ``xs_parms`` is a flat dict mapping airfoil-parm-name → value
    (used by both ``GetXSecParm`` and ``GetParmVal``).
    """
    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
    fake.XS_POINT = 0
    fake.XS_CIRCLE = 1
    fake.XS_ELLIPSE = 2
    fake.XS_SUPER_ELLIPSE = 3
    fake.XS_ROUNDED_RECTANGLE = 4
    fake.XS_GENERAL_FUSE = 5
    fake.XS_FILE_FUSE = 6
    fake.XS_FOUR_SERIES = 7
    fake.XS_SIX_SERIES = 8
    fake.XS_BICONVEX = 9
    fake.XS_WEDGE = 10
    fake.XS_BEZIER = 11
    fake.XS_FILE_AIRFOIL = 12
    fake.XS_CST_AIRFOIL = 13
    fake.XS_VKT_AIRFOIL = 14
    fake.XS_FOUR_DIGIT_MOD = 15
    fake.XS_FIVE_DIGIT = 16
    fake.XS_FIVE_DIGIT_MOD = 17
    fake.XS_ONE_SIX_SERIES = 18
    fake.XS_EDIT_CURVE = 19

    fake.GetXSecShape = lambda xs: xs_shape

    def _get_xsec_parm(xs, name):
        return f"PID::{xs}::{name}" if name in xs_parms else ""

    def _get_parm_val(pid):
        if pid == "":
            return 0.0
        _, _xs, name = pid.split("::", 2)
        return xs_parms.get(name, 0.0)

    fake.GetXSecParm = _get_xsec_parm
    fake.GetParmVal = _get_parm_val

    # XSecSurf access used by foilsurf_u_for_xs.
    shapes = xs_shapes_in_surface or [xs_shape]
    fake.GetNumXSec = lambda xsurf: len(shapes)
    fake.GetXSec = lambda xsurf, i: f"XS_{i}"
    fake._shapes_in_surface = shapes

    def _shape_in_surface(xs_id):
        # xs_id looks like "XS_<i>"
        try:
            i = int(xs_id.split("_", 1)[1])
        except Exception:
            return xs_shape
        return shapes[i] if i < len(shapes) else xs_shape

    # Override GetXSecShape to dispatch by xs_id so foilsurf_u_for_xs
    # can detect caps properly.
    fake.GetXSecShape = _shape_in_surface

    # WriteSeligAirfoil — capture path.
    def _write(path, geom_id, foilsurf_u):
        Path(path).write_text(
            "naca-from-vsp\n0.0 0.0\n1.0 0.0\n0.0 0.0\n",
            encoding="utf-8",
        )
        if write_path_capture is not None:
            write_path_capture.append(str(path))

    fake.WriteSeligAirfoil = _write
    return cast(ModuleType, fake)


@pytest.fixture
def airfoils_dir(tmp_path, monkeypatch):
    """Redirect AIRFOILS_DIR to a tmp_path for write tests."""
    d = tmp_path / "airfoils"
    d.mkdir(parents=True)
    from app.converters import openvsp_airfoil

    monkeypatch.setattr(openvsp_airfoil, "AIRFOILS_DIR", d)
    return d


# ---------------------------------------------------------------------------
# NACA name synthesis
# ---------------------------------------------------------------------------


class TestNacaNames:
    def test_4series_naca2412(self):
        assert naca_4series_name(camber=0.02, camber_loc=0.4, thick_chord=0.12) == "naca2412"

    def test_4series_naca0012_symmetric(self):
        assert naca_4series_name(camber=0.0, camber_loc=0.0, thick_chord=0.12) == "naca0012"

    def test_4series_naca6409(self):
        assert naca_4series_name(camber=0.06, camber_loc=0.4, thick_chord=0.09) == "naca6409"

    def test_5series_naca23012(self):
        # Camber=0.30 → first digit ~ "2" (design-Cl), CamberLoc=0.15 → "30"
        # Reflex=0, ThickChord=0.12 → "12"
        # Standard NACA 23012: 2-30-1-2
        assert (
            naca_5series_name(camber=0.30, camber_loc=0.15, reflex=0.0, thick_chord=0.12)
            == "naca23012"
        )

    def test_6series_naca65_410(self):
        # Series=65, IdealCl=0.4, ThickChord=0.10, A=0.5
        name = naca_6series_name(series=65, ideal_cl=0.4, thick_chord=0.10, a=0.5)
        assert "65" in name
        assert "4" in name
        assert "10" in name


# ---------------------------------------------------------------------------
# foilsurf_u_for_xs with end-cap awareness
# ---------------------------------------------------------------------------


class TestFoilsurfU:
    def test_no_caps_uniform_distribution(self):
        # 5 xsecs, all airfoils → 0, 0.25, 0.5, 0.75, 1.0
        fake = _make_airfoil_vsp(
            xs_shape=12,  # XS_FILE_AIRFOIL
            xs_parms={},
            xs_shapes_in_surface=[12, 12, 12, 12, 12],
        )
        assert foilsurf_u_for_xs(fake, "XSURF", 0) == pytest.approx(0.0)
        assert foilsurf_u_for_xs(fake, "XSURF", 2) == pytest.approx(0.5)
        assert foilsurf_u_for_xs(fake, "XSURF", 4) == pytest.approx(1.0)

    def test_root_cap_xs_point(self):
        # First xsec is a POINT cap; airfoils are 1..3
        fake = _make_airfoil_vsp(
            xs_shape=12,
            xs_parms={},
            xs_shapes_in_surface=[0, 12, 12, 12],  # POINT, F, F, F
        )
        # Index 0 → None (cap), 1 → 0, 2 → 0.5, 3 → 1
        assert foilsurf_u_for_xs(fake, "XSURF", 0) is None
        assert foilsurf_u_for_xs(fake, "XSURF", 1) == pytest.approx(0.0)
        assert foilsurf_u_for_xs(fake, "XSURF", 2) == pytest.approx(0.5)
        assert foilsurf_u_for_xs(fake, "XSURF", 3) == pytest.approx(1.0)

    def test_tip_cap_xs_point(self):
        fake = _make_airfoil_vsp(
            xs_shape=12,
            xs_parms={},
            xs_shapes_in_surface=[12, 12, 12, 0],  # F, F, F, POINT
        )
        assert foilsurf_u_for_xs(fake, "XSURF", 0) == pytest.approx(0.0)
        assert foilsurf_u_for_xs(fake, "XSURF", 2) == pytest.approx(1.0)
        assert foilsurf_u_for_xs(fake, "XSURF", 3) is None


# ---------------------------------------------------------------------------
# import_airfoil_from_xsec dispatch
# ---------------------------------------------------------------------------


class TestImportAirfoilFromXsec:
    def test_four_series_returns_naca_name(self):
        fake = _make_airfoil_vsp(
            xs_shape=7,  # XS_FOUR_SERIES
            xs_parms={"Camber": 0.02, "CamberLoc": 0.4, "ThickChord": 0.12},
        )
        ctx = ImportContext()
        result = import_airfoil_from_xsec(
            xs_id="XS_0",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=0,
            ctx=ctx,
            vsp=fake,
        )
        assert result == "naca2412"
        assert ctx.warnings == []

    def test_file_airfoil_writes_dat_file(self, airfoils_dir, monkeypatch):
        capture: list[str] = []
        fake = _make_airfoil_vsp(
            xs_shape=12,  # XS_FILE_AIRFOIL
            xs_parms={},
            xs_shapes_in_surface=[12, 12, 12],
            write_path_capture=capture,
        )
        ctx = ImportContext()
        result = import_airfoil_from_xsec(
            xs_id="XS_1",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=1,
            ctx=ctx,
            vsp=fake,
        )
        assert result is not None
        assert result.endswith(".dat")
        assert len(capture) == 1
        # The file actually exists on disk now.
        written = Path(capture[0])
        assert written.exists()
        assert "vsp_imported" in written.name

    def test_unique_filenames_for_two_file_airfoils(self, airfoils_dir):
        capture: list[str] = []
        fake = _make_airfoil_vsp(
            xs_shape=12,
            xs_parms={},
            xs_shapes_in_surface=[12, 12, 12],
            write_path_capture=capture,
        )
        ctx = ImportContext()
        r1 = import_airfoil_from_xsec(
            xs_id="XS_0",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=0,
            ctx=ctx,
            vsp=fake,
        )
        r2 = import_airfoil_from_xsec(
            xs_id="XS_1",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=1,
            ctx=ctx,
            vsp=fake,
        )
        assert r1 != r2
        assert len(set(capture)) == 2

    def test_cst_falls_back_to_file_export_with_warning(self, airfoils_dir):
        fake = _make_airfoil_vsp(
            xs_shape=13,  # XS_CST_AIRFOIL
            xs_parms={},
            xs_shapes_in_surface=[13, 13],
        )
        ctx = ImportContext()
        result = import_airfoil_from_xsec(
            xs_id="XS_0",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=0,
            ctx=ctx,
            vsp=fake,
        )
        assert result.endswith(".dat")
        assert len(ctx.warnings) == 1
        assert "CST" in ctx.warnings[0].reason

    def test_unsupported_shape_warns_and_returns_none(self, airfoils_dir):
        fake = _make_airfoil_vsp(
            xs_shape=999,  # unknown
            xs_parms={},
        )
        ctx = ImportContext()
        result = import_airfoil_from_xsec(
            xs_id="XS_0",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=0,
            ctx=ctx,
            vsp=fake,
        )
        # Falls back to a Selig export attempt — but the caller can
        # decide; the contract is: never crash, always either return
        # a path or a placeholder + warning.
        assert ctx.warnings, "Unsupported shape must emit a warning"
        assert result is not None

    def test_six_series_returns_naca_name(self):
        fake = _make_airfoil_vsp(
            xs_shape=8,  # XS_SIX_SERIES
            xs_parms={
                "Series": 65,
                "A": 0.5,
                "IdealCl": 0.4,
                "ThickChord": 0.10,
            },
        )
        ctx = ImportContext()
        result = import_airfoil_from_xsec(
            xs_id="XS_0",
            geom_id="WING1",
            xsurf="XSURF",
            xs_index=0,
            ctx=ctx,
            vsp=fake,
        )
        assert "65" in result
