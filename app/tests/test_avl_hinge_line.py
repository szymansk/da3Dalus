"""gh-1163: a trailing-edge device over several segments keeps ONE straight hinge line.

Each segment stores its hinge as chord fraction at the inboard section
(``rel_chord_root``) and at the outboard section (``rel_chord_tip``). The AVL
CONTROL that a segment copies onto its outboard section must carry the tip
value; with the root value the hinge chord fraction is constant per segment and
the hinge line kinks at every section of a tapered surface.
"""

from __future__ import annotations

import pytest

import app.schemas.aeroplaneschema as schemas
from app.services.avl_geometry_service import _build_controls_for_wing

_AF = "./components/airfoils/mh32.dat"


def _xsec(y: float, chord: float, ted=None) -> schemas.WingXSecSchema:
    return schemas.WingXSecSchema(
        xyz_le=[0.0, y, 0.0], chord=chord, twist=0.0, airfoil=_AF, trailing_edge_device=ted
    )


def _wing(*teds) -> schemas.AsbWingSchema:
    chords = [0.20, 0.16, 0.12]
    return schemas.AsbWingSchema(
        name="surf",
        symmetric=True,
        x_secs=[
            _xsec(0.25 * i, c, teds[i] if i < len(teds) else None) for i, c in enumerate(chords)
        ],
    )


def _xhinges(per_section) -> list[list[float]]:
    return [sorted(c.xhinge for c in section) for section in per_section]


def test_outboard_copy_carries_the_segment_tip_hinge():
    w = _wing(
        schemas.TrailingEdgeDeviceDetailSchema(
            name="ail", role="aileron", rel_chord_root=0.70, rel_chord_tip=0.75
        ),
        schemas.TrailingEdgeDeviceDetailSchema(
            name="ail", role="aileron", rel_chord_root=0.75, rel_chord_tip=0.80
        ),
    )
    per_section = _build_controls_for_wing(w, wing_key="wing")
    # section 1 is the tip of segment 0 and the root of segment 1: both entries at 0.75
    assert _xhinges(per_section) == [[0.70], [0.75, 0.75], [0.80]]


def test_hinge_line_is_straight_on_a_tapered_surface():
    # hinge at x = 0.10 m on every section (unswept hinge, tapered chord 0.20 -> 0.16 -> 0.12)
    w = _wing(
        schemas.TrailingEdgeDeviceDetailSchema(
            name="elev", role="elevator", rel_chord_root=0.5, rel_chord_tip=0.625
        ),
        schemas.TrailingEdgeDeviceDetailSchema(
            name="elev", role="elevator", rel_chord_root=0.625, rel_chord_tip=0.1 / 0.12
        ),
    )
    per_section = _build_controls_for_wing(w, wing_key="hlw")
    for xsec, section in zip(w.x_secs, per_section, strict=True):
        for ctrl in section:
            assert xsec.xyz_le[0] + ctrl.xhinge * xsec.chord == pytest.approx(0.10)


def test_missing_tip_keeps_the_root_hinge():
    w = _wing(schemas.TrailingEdgeDeviceDetailSchema(name="flap", role="flap", rel_chord_root=0.8))
    per_section = _build_controls_for_wing(w, wing_key="wing")
    assert _xhinges(per_section) == [[0.8], [0.8], []]


def test_dual_axis_surface_uses_the_tip_on_both_axes():
    w = _wing(
        schemas.TrailingEdgeDeviceDetailSchema(
            name="ev", role="elevon", rel_chord_root=0.70, rel_chord_tip=0.78
        )
    )
    per_section = _build_controls_for_wing(w, wing_key="wing")
    assert _xhinges(per_section) == [[0.70, 0.70], [0.78, 0.78], []]
