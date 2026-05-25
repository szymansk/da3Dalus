"""Unit tests for the WING-handler XForm helpers (gh-698).

The wing handler must read each Geom's world-frame translation +
rotation (Cessna 172 regression: HTP was overlapping the main wing,
VTP was rendered flat in the X-Y plane). These tests pin the
rotation order (intrinsic XYZ) and the translation handling.
"""

from __future__ import annotations

import math
from types import ModuleType, SimpleNamespace
from typing import cast

import pytest

from app.converters.openvsp_wing_handler import (
    _apply_xform,
    _read_geom_xform,
    _read_xform_parm,
)


# ---------------------------------------------------------------------------
# _read_xform_parm / _read_geom_xform
# ---------------------------------------------------------------------------


def _make_xform_vsp(parms: dict[tuple[str, str], float]) -> ModuleType:
    """Tiny fake vsp module that exposes only FindParm/GetParmVal,
    backed by a ``{(name, group): value}`` dict.
    """
    fake = SimpleNamespace()
    fake.FindParm = lambda gid, name, group: (
        f"{gid}:{name}:{group}" if (name, group) in parms else ""
    )
    fake.GetParmVal = lambda pid: parms[(pid.split(":")[1], pid.split(":")[2])]
    return cast(ModuleType, fake)


class TestReadXformParm:
    def test_returns_zero_when_parm_missing(self):
        vsp = _make_xform_vsp({})
        assert _read_xform_parm(vsp, "GID", "X_Location") == 0.0

    def test_returns_value_when_present(self):
        vsp = _make_xform_vsp({("X_Location", "XForm"): 4.2})
        assert _read_xform_parm(vsp, "GID", "X_Location") == 4.2

    def test_coerces_to_float(self):
        vsp = _make_xform_vsp({("Y_Location", "XForm"): 1})
        assert _read_xform_parm(vsp, "GID", "Y_Location") == 1.0
        assert isinstance(_read_xform_parm(vsp, "GID", "Y_Location"), float)


class TestReadGeomXform:
    def test_all_zero_when_no_parms(self):
        vsp = _make_xform_vsp({})
        translation, rotation = _read_geom_xform(vsp, "GID")
        assert translation == (0.0, 0.0, 0.0)
        assert rotation == (0.0, 0.0, 0.0)

    def test_reads_full_xform(self):
        # Mirrors the StabVer values from the Cessna 172 regression case.
        vsp = _make_xform_vsp(
            {
                ("X_Location", "XForm"): 2.09,
                ("Y_Location", "XForm"): 0.0,
                ("Z_Location", "XForm"): 0.13,
                ("X_Rotation", "XForm"): 90.0,
                ("Y_Rotation", "XForm"): 0.0,
                ("Z_Rotation", "XForm"): 0.0,
            }
        )
        translation, rotation = _read_geom_xform(vsp, "GID")
        assert translation == (2.09, 0.0, 0.13)
        assert rotation == (90.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# _apply_xform — rotation pinning
# ---------------------------------------------------------------------------


def _approx_eq(a: list[float], b: list[float], tol: float = 1e-9) -> bool:
    return all(abs(x - y) < tol for x, y in zip(a, b, strict=True))


class TestApplyXform:
    def test_identity(self):
        out = _apply_xform([1.0, 2.0, 3.0], (0, 0, 0), (0, 0, 0))
        assert _approx_eq(out, [1.0, 2.0, 3.0])

    def test_pure_translation(self):
        out = _apply_xform([1.0, 2.0, 3.0], (10, 20, 30), (0, 0, 0))
        assert _approx_eq(out, [11.0, 22.0, 33.0])

    def test_rx_90_maps_y_to_z(self):
        """X-rotation of +90° rotates +Y onto +Z (right-hand rule).

        This is the Cessna 172 VTP case: a flat wing whose span is +Y
        becomes a vertical wing whose span is +Z.
        """
        out = _apply_xform([0.0, 1.0, 0.0], (0, 0, 0), (90.0, 0, 0))
        assert _approx_eq(out, [0.0, 0.0, 1.0])

    def test_rx_90_maps_z_to_negative_y(self):
        """+Z under Rx(+90°) goes to −Y (right-hand rule).

        Pairs with ``test_rx_90_maps_y_to_z`` to pin the chirality.
        """
        out = _apply_xform([0.0, 0.0, 1.0], (0, 0, 0), (90.0, 0, 0))
        assert _approx_eq(out, [0.0, -1.0, 0.0])

    def test_ry_90_maps_z_to_x(self):
        """+Z under Ry(+90°) goes to +X."""
        out = _apply_xform([0.0, 0.0, 1.0], (0, 0, 0), (0, 90.0, 0))
        assert _approx_eq(out, [1.0, 0.0, 0.0])

    def test_rz_90_maps_x_to_y(self):
        """+X under Rz(+90°) goes to +Y."""
        out = _apply_xform([1.0, 0.0, 0.0], (0, 0, 0), (0, 0, 90.0))
        assert _approx_eq(out, [0.0, 1.0, 0.0])

    def test_rotation_then_translation(self):
        """Cessna 172 StabVer-style XForm: translate to (2.09, 0, 0.13)
        + 90° X-rotation. A point at (0, 1, 0) — the local-frame span
        tip — should end up at (2.09, 0, 1.13)."""
        out = _apply_xform(
            [0.0, 1.0, 0.0], (2.09, 0.0, 0.13), (90.0, 0.0, 0.0)
        )
        assert _approx_eq(out, [2.09, 0.0, 1.13])

    def test_openvsp_rotation_order(self):
        """Pin OpenVSP's rotation order: matrix product ``R = Rx · Ry · Rz``
        — i.e. apply Rz to the vector first, then Ry, then Rx (gh-717).

        Sequence applied to (0, 1, 0) with (Rx=90°, Ry=90°, Rz=0°):
            Rz(0°)(0,1,0)         = (0, 1, 0)
            Ry(90°)(0,1,0)        = (0, 1, 0)            (Y is the axis)
            Rx(90°)(0,1,0)        = (0, 0, 1)            (+Y → +Z)
        """
        out = _apply_xform([0.0, 1.0, 0.0], (0, 0, 0), (90.0, 90.0, 0.0))
        assert _approx_eq(out, [0.0, 0.0, 1.0])

    def test_cessna_mainstrut_rotation(self):
        """gh-717 regression: a two-axis Geom rotation must agree with
        OpenVSP's ``CompPnt01`` world-frame surface point.

        MainStrut on the Cessna 172:
          rot   = (Rx=-30°, Ry=0°, Rz=-90°)
          trans = (+0.37, +1.27, -0.90)
          local tip xsec at (1, 0, 0) — 1 m along the local spine

        VSP says u=1.0 lands at world (+0.43, +0.40, -0.40). Pre-fix
        the handler applied rotations in reverse order and ended up
        at (+0.37, +0.27, -0.90) — horizontal instead of inclined.
        """
        out = _apply_xform(
            [1.0, 0.0, 0.0], (0.37, 1.27, -0.90), (-30.0, 0.0, -90.0)
        )
        assert _approx_eq(out, [0.37, 0.404, -0.4], tol=1e-3)

    @pytest.mark.parametrize(
        "rot_deg,inp,expected",
        [
            ((45.0, 0, 0), [0, math.sqrt(2), 0], [0, 1.0, 1.0]),
            ((-90.0, 0, 0), [0, 1, 0], [0, 0, -1]),  # opposite rotation
            ((0, 0, 180.0), [1, 0, 0], [-1, 0, 0]),  # 180° around Z
        ],
    )
    def test_various_rotations(self, rot_deg, inp, expected):
        out = _apply_xform(inp, (0, 0, 0), rot_deg)
        assert _approx_eq(out, expected, tol=1e-9)
