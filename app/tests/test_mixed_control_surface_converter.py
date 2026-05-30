"""gh-772 #D/#G — dual-axis emission in the ASB airplane + AVL geometry builders.

A dual-role surface (elevon/flaperon/ruddervator) must emit TWO control variables
(primary symmetric + secondary antisymmetric) on BOTH paths, with identical unique
names so the trim index map stays consistent. Single-axis surfaces are unchanged.
Differential never enters the geometry (SgnDup stays ±1).
"""

import app.schemas.aeroplaneschema as schemas
from app.converters.model_schema_converters import _asb_wing_xsecs_from_schema
from app.services.avl_geometry_service import _build_controls_for_wing

_AF = "./components/airfoils/mh32.dat"


def _wing_with_ted(ted: schemas.TrailingEdgeDeviceDetailSchema) -> schemas.AsbWingSchema:
    return schemas.AsbWingSchema(
        name="surf",
        symmetric=True,
        x_secs=[
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.0, 0.0], chord=0.2, twist=0.0, airfoil=_AF,
                trailing_edge_device=ted,
            ),
            schemas.WingXSecSchema(
                xyz_le=[0.0, 0.5, 0.0], chord=0.16, twist=0.0, airfoil=_AF,
            ),
        ],
    )


class TestAsbDualAxis:
    def test_ruddervator_emits_two_control_surfaces(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(
            role="ruddervator", rel_chord_root=0.7, deflection_deg=2.0,
            mix_gain_primary=1.2, mix_gain_secondary=0.6,
        )
        xsecs = _asb_wing_xsecs_from_schema(_wing_with_ted(ted), wing_key="vtail")
        cs = xsecs[0].control_surfaces
        assert len(cs) == 2
        primary, secondary = cs
        assert primary.symmetric is True
        assert secondary.symmetric is False
        # secondary (yaw) axis baseline deflection zeroed for the AeroBuildup fallback
        assert primary.deflection == 2.0
        assert secondary.deflection == 0.0
        # unique, role-tag-parseable names
        assert primary.name != secondary.name
        assert primary.name.startswith("[ruddervator]")
        assert secondary.name.startswith("[ruddervator]")

    def test_elevator_unchanged_single_surface(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(
            role="elevator", rel_chord_root=0.7, deflection_deg=1.0
        )
        xsecs = _asb_wing_xsecs_from_schema(_wing_with_ted(ted), wing_key="htail")
        cs = xsecs[0].control_surfaces
        assert len(cs) == 1
        assert cs[0].symmetric is True
        assert cs[0].name == "[elevator]elevator"


class TestAvlDualAxis:
    def test_ruddervator_two_control_lines_sgndup_signs(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(
            role="ruddervator", rel_chord_root=0.7,
            mix_gain_primary=1.2, mix_gain_secondary=0.6,
        )
        per_section = _build_controls_for_wing(_wing_with_ted(ted), wing_key="vtail")
        # both sections of the single panel carry both axes
        assert len(per_section[0]) == 2
        signs = sorted(c.sgn_dup for c in per_section[0])
        assert signs == [-1.0, 1.0]
        gains = sorted(c.gain for c in per_section[0])
        assert gains == [0.6, 1.2]

    def test_differential_ratio_never_enters_geometry(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(
            role="aileron", rel_chord_root=0.7, symmetric=False, differential_ratio=2.5
        )
        per_section = _build_controls_for_wing(_wing_with_ted(ted), wing_key="wing")
        for ctrl in per_section[0]:
            assert abs(ctrl.sgn_dup) == 1.0  # never 2.5
        avl_text = repr(per_section[0][0])
        assert "2.5" not in avl_text

    def test_elevon_emits_two_lines(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(role="elevon", rel_chord_root=0.75)
        per_section = _build_controls_for_wing(_wing_with_ted(ted), wing_key="wing")
        assert len(per_section[0]) == 2
        names = {c.name for c in per_section[0]}
        assert len(names) == 2  # distinct names

    def test_single_axis_unchanged_name_and_gain(self):
        ted = schemas.TrailingEdgeDeviceDetailSchema(role="flap", rel_chord_root=0.8)
        per_section = _build_controls_for_wing(_wing_with_ted(ted), wing_key="wing")
        assert len(per_section[0]) == 1
        assert per_section[0][0].name == "[flap]flap"
        assert per_section[0][0].gain == 1.0
        assert per_section[0][0].sgn_dup == 1.0
