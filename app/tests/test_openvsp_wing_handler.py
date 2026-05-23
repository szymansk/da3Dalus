"""Unit tests for the OpenVSP WING handler (gh-641).

Covers:

* Container convention — planform parms live on the WING container in
  group ``XSec_<i>`` (per review comment on gh-641).
* ``Sym_Planar_Flag`` bitmask → ``WingConfiguration.symmetric``.
* Multi-section (Yehudi-break) wings emit one ``WingXSecSchema`` per
  section + a final terminal section.
* Sweep is converted from ``Sweep_Location`` reference to the c/4
  reference (our model's convention) via ``sweep_at_c4``.
* Driver-group agnostic: post-``Update`` we read planform values
  directly, never reconstruct from drivers.
"""

from __future__ import annotations

import math
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters import openvsp_adapter, openvsp_importer
from app.converters.openvsp_importer import import_vsp3
from app.converters.openvsp_wing_handler import (
    _airfoil_placeholder,
    register,
    sweep_at_c4,
)


# ---------------------------------------------------------------------------
# Fake-vsp factory
# ---------------------------------------------------------------------------


def _make_wing_vsp(
    *,
    wing_id: str = "WING1",
    name: str = "MainWing",
    n_sec: int = 1,
    symmetric_flag: int = 2,  # SYM_XZ
    section_parms: list[dict[str, float]] | None = None,
) -> ModuleType:
    """Build a fake `openvsp` module describing a single WING geom.

    ``section_parms[i]`` describes section *i* with keys:
      Span, Root_Chord, Tip_Chord, Sweep, Sweep_Location, Dihedral, Twist
    The skeleton dispatch loop expects geom-type "WING".
    """
    section_parms = section_parms or [
        {
            "Span": 5.0,
            "Root_Chord": 1.0,
            "Tip_Chord": 0.5,
            "Sweep": 10.0,
            "Sweep_Location": 0.25,  # c/4 reference
            "Dihedral": 3.0,
            "Twist": 2.0,
        }
    ]

    fake = SimpleNamespace()  # see test_openvsp_importer for rationale
    fake.LEN_MM, fake.LEN_CM, fake.LEN_M = 0, 1, 2
    fake.LEN_IN, fake.LEN_FT, fake.LEN_YD, fake.LEN_UNITLESS = 3, 4, 5, 6
    fake.SYM_XY, fake.SYM_XZ, fake.SYM_YZ = 1, 2, 4
    fake.XS_FOUR_SERIES = 7  # arbitrary

    fake.ClearVSPModel = lambda *a, **k: None
    fake.ReadVSPFile = lambda *a, **k: None
    fake.SetLengthUnit = lambda *a, **k: None
    fake.Update = lambda *a, **k: None
    fake.GetVehicleID = lambda: "VEH"
    fake.FindGeoms = lambda: [wing_id]
    fake.GetGeomName = lambda gid: name if gid == wing_id else ""
    fake.GetGeomTypeName = lambda gid: "WING" if gid == wing_id else ""

    # XSecSurf bookkeeping
    XSURF = "XSURF_WING"
    fake.GetXSecSurf = lambda gid, _idx: XSURF
    fake.GetNumXSec = lambda xs: n_sec + 1  # n sections → n+1 xsecs

    def _get_xsec(xs, i):
        return f"XS_{i}"

    fake.GetXSec = _get_xsec

    # Per-section planform parms in group XSec_<i> on the wing container.
    # We also need Sym_Planar_Flag on the wing container in group "Sym".
    fake._parms: dict[tuple[str, str, str], float] = {  # type: ignore[attr-defined]
        (wing_id, "Sym_Planar_Flag", "Sym"): float(symmetric_flag),
    }
    # Section 0 is the root XSec — segment parms anchor on sections 1..n.
    # Per review comment: group naming is "XSec_<i>" for i in 1..n_sec.
    for i, sp in enumerate(section_parms, start=1):
        for k, v in sp.items():
            fake._parms[(wing_id, k, f"XSec_{i}")] = v

    def _find_parm(container, parm, group):
        return f"{container}::{group}::{parm}" if (container, parm, group) in fake._parms else ""

    def _get_parm_val(pid):
        if pid == "":
            return 0.0
        container, group, parm = pid.split("::", 2)
        return fake._parms.get((container, parm, group), 0.0)

    fake.FindParm = _find_parm
    fake.GetParmVal = _get_parm_val

    # Airfoil shape lookup — return XS_FOUR_SERIES so the placeholder is used.
    fake.GetXSecShape = lambda xs: fake.XS_FOUR_SERIES
    return cast(ModuleType, fake)


# ---------------------------------------------------------------------------
# sweep_at_c4 helper
# ---------------------------------------------------------------------------


class TestSweepAtC4:
    def test_pass_through_when_reference_is_quarter_chord(self):
        assert sweep_at_c4(
            sweep_xref_deg=15.0, xref=0.25, span=5.0, c_root=1.0, c_tip=0.5
        ) == pytest.approx(15.0)

    def test_le_sweep_converts_to_smaller_c4_sweep(self):
        # For a tapered wing (c_root > c_tip), the c/4 line is LESS swept
        # than the leading edge: tan(Λ_c/4) = tan(Λ_LE) - 0.25*(c_root-c_tip)/span.
        # With c_root=1, c_tip=0.5, span=5: delta = 0.25*0.5/5 = 0.025
        # tan(15°) = 0.2679; tan(Λ_c/4) = 0.2679 - 0.025 = 0.2429
        # Λ_c/4 ≈ 13.66°.
        le = 15.0
        c4 = sweep_at_c4(sweep_xref_deg=le, xref=0.0, span=5.0, c_root=1.0, c_tip=0.5)
        expected = math.degrees(math.atan(math.tan(math.radians(le)) - 0.25 * (1.0 - 0.5) / 5.0))
        assert c4 == pytest.approx(expected)
        assert c4 < le, "c/4 sweep should be smaller than LE sweep on a tapered wing"

    def test_zero_span_returns_input(self):
        assert sweep_at_c4(
            sweep_xref_deg=20.0, xref=0.5, span=0.0, c_root=1.0, c_tip=1.0
        ) == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Airfoil placeholder — until #642 lands.
# ---------------------------------------------------------------------------


class TestAirfoilPlaceholder:
    def test_returns_valid_path(self):
        p = _airfoil_placeholder()
        # Must be a string that the WingXSecSchema accepts (file path).
        assert isinstance(p, str)
        assert p.endswith(".dat")


# ---------------------------------------------------------------------------
# Integration via import_vsp3 + register()
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_handlers():
    """Each test starts with the WING handler freshly registered."""
    # Clear handlers + reset state.
    openvsp_importer._HANDLERS.clear()
    register()
    yield
    openvsp_importer._HANDLERS.clear()


class TestSingleSectionTrapezoidal:
    def test_basic_geometry(self, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_vsp(
            section_parms=[
                {
                    "Span": 5.0,
                    "Root_Chord": 1.0,
                    "Tip_Chord": 0.5,
                    "Sweep": 10.0,
                    "Sweep_Location": 0.25,
                    "Dihedral": 3.0,
                    "Twist": 2.0,
                }
            ]
        )
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        assert "MainWing" in (result.aeroplane.wings or {})
        wing = result.aeroplane.wings["MainWing"]
        assert wing.symmetric is True
        assert len(wing.x_secs) == 2  # root + tip
        # Root xsec at origin
        root = wing.x_secs[0]
        assert root.xyz_le == pytest.approx([0.0, 0.0, 0.0])
        assert root.chord == pytest.approx(1.0)
        # Tip xsec — y = span, z = span*tan(dihedral)
        tip = wing.x_secs[1]
        assert tip.xyz_le[1] == pytest.approx(5.0, rel=1e-6)
        assert tip.xyz_le[2] == pytest.approx(5.0 * math.tan(math.radians(3.0)), rel=1e-6)
        assert tip.chord == pytest.approx(0.5)
        # Twist on the tip xsec
        assert tip.twist == pytest.approx(2.0)


class TestSymmetryFlag:
    @pytest.mark.parametrize(
        "flag, expected",
        [
            (0, False),
            (1, False),  # SYM_XY only — wing not mirrored about XZ
            (2, True),  # SYM_XZ — left/right mirror
            (4, False),  # SYM_YZ — fore/aft (not how wings mirror)
            (2 | 1, True),  # combination including SYM_XZ
        ],
    )
    def test_symmetric_inferred_from_sym_xz_bit(self, flag, expected, tmp_path, monkeypatch):
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_vsp(symmetric_flag=flag)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        assert wing.symmetric is expected


class TestMultiSectionWing:
    def test_yehudi_break(self, tmp_path, monkeypatch):
        """Two sections — inner (large chord, low sweep) + outer (cranked)."""
        sections = [
            # Inner panel
            {
                "Span": 2.0,
                "Root_Chord": 1.0,
                "Tip_Chord": 0.8,
                "Sweep": 5.0,
                "Sweep_Location": 0.25,
                "Dihedral": 0.0,
                "Twist": 0.0,
            },
            # Outer panel
            {
                "Span": 3.0,
                "Root_Chord": 0.8,  # matches inner tip
                "Tip_Chord": 0.4,
                "Sweep": 20.0,
                "Sweep_Location": 0.25,
                "Dihedral": 4.0,
                "Twist": -3.0,
            },
        ]
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_vsp(n_sec=2, section_parms=sections)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        # n_sec sections → n_sec+1 xsecs.
        assert len(wing.x_secs) == 3
        # Cumulative span at each xsec along Y.
        ys = [xs.xyz_le[1] for xs in wing.x_secs]
        assert ys == pytest.approx([0.0, 2.0, 5.0], rel=1e-6)
        # Cumulative Z due to dihedral.
        # Inner panel dihedral 0 → z stays 0 at xsec 1.
        # Outer panel dihedral 4° → tip z = inner_tip_z + 3*tan(4°)
        zs = [xs.xyz_le[2] for xs in wing.x_secs]
        assert zs[0] == pytest.approx(0.0)
        assert zs[1] == pytest.approx(0.0)
        assert zs[2] == pytest.approx(3.0 * math.tan(math.radians(4.0)), rel=1e-6)


class TestSweepLocationConversion:
    def test_le_sweep_input_converted_to_c4(self, tmp_path, monkeypatch):
        """Sweep_Location=0 means input sweep is LE-referenced."""
        sections = [
            {
                "Span": 5.0,
                "Root_Chord": 1.0,
                "Tip_Chord": 0.5,
                "Sweep": 15.0,  # LE sweep
                "Sweep_Location": 0.0,
                "Dihedral": 0.0,
                "Twist": 0.0,
            }
        ]
        f = tmp_path / "x.vsp3"
        f.write_text("")
        fake = _make_wing_vsp(section_parms=sections)
        monkeypatch.setattr(openvsp_adapter, "get_vsp", lambda: fake)
        result = import_vsp3(f)
        wing = result.aeroplane.wings["MainWing"]
        # Tip leading-edge X comes from c/4 sweep on the inboard quarter-chord,
        # but we expose the geometry via xyz_le, so the LE-X follows the LE
        # sweep angle directly: tan(LE_sweep) * span.
        tip = wing.x_secs[1]
        expected_x = 5.0 * math.tan(math.radians(15.0))
        assert tip.xyz_le[0] == pytest.approx(expected_x, rel=1e-6)
