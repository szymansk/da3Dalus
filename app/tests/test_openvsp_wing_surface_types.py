"""gh-1187: role proposal for imported OpenVSP wings (``propose_import_surface_types``)."""

from __future__ import annotations

from types import SimpleNamespace

from app.converters.openvsp_wing_handler import (
    _assign_surface_types,
    propose_import_surface_types,
)
from app.schemas.aeroplaneschema import (
    AeroplaneSchema,
    AsbWingSchema,
    SurfaceType,
    WingXSecSchema,
)


def _wing(
    name: str,
    *,
    half_span: float,
    chord: float,
    x_le: float = 0.0,
    symmetric: bool = True,
) -> AsbWingSchema:
    return AsbWingSchema(
        name=name,
        surface_type=SurfaceType.MAIN_WING,  # provisional, as the handler sets it
        symmetric=symmetric,
        x_secs=[
            WingXSecSchema(xyz_le=[x_le, 0.0, 0.0], chord=chord, twist=0.0, airfoil="naca0012"),
            WingXSecSchema(
                xyz_le=[x_le, half_span, 0.0], chord=chord, twist=0.0, airfoil="naca0012"
            ),
        ],
    )


class TestProposeImportSurfaceTypes:
    def test_empty_dict_gives_empty_proposal(self):
        assert propose_import_surface_types({}) == {}

    def test_single_wing_is_main_wing(self):
        wings = {"W": _wing("W", half_span=1.0, chord=0.3)}
        assert propose_import_surface_types(wings) == {"W": SurfaceType.MAIN_WING}

    def test_largest_planform_is_main_wing_regardless_of_order(self):
        wings = {
            "Tail": _wing("Tail", half_span=0.4, chord=0.1, x_le=1.0),
            "Wing": _wing("Wing", half_span=2.0, chord=0.4),
        }
        proposal = propose_import_surface_types(wings)
        assert proposal["Wing"] == SurfaceType.MAIN_WING
        assert proposal["Tail"] != SurfaceType.MAIN_WING

    def test_non_symmetric_secondary_wing_is_vertical_tail(self):
        wings = {
            "Wing": _wing("Wing", half_span=2.0, chord=0.4),
            "Fin": _wing("Fin", half_span=0.3, chord=0.1, x_le=1.0, symmetric=False),
        }
        assert propose_import_surface_types(wings)["Fin"] == SurfaceType.VERTICAL_TAIL

    def test_symmetric_wing_ahead_of_main_root_is_canard(self):
        wings = {
            "Wing": _wing("Wing", half_span=2.0, chord=0.4, x_le=0.5),
            "Canard": _wing("Canard", half_span=0.4, chord=0.1, x_le=-0.3),
        }
        assert propose_import_surface_types(wings)["Canard"] == SurfaceType.CANARD

    def test_symmetric_wing_behind_main_root_is_horizontal_tail(self):
        wings = {
            "Wing": _wing("Wing", half_span=2.0, chord=0.4, x_le=0.0),
            "HTP": _wing("HTP", half_span=0.5, chord=0.1, x_le=1.2),
        }
        assert propose_import_surface_types(wings)["HTP"] == SurfaceType.HORIZONTAL_TAIL

    def test_exactly_one_main_wing_for_conventional_layout(self):
        wings = {
            "HTP": _wing("HTP", half_span=0.5, chord=0.1, x_le=1.2),
            "VTP": _wing("VTP", half_span=0.3, chord=0.1, x_le=1.2, symmetric=False),
            "Wing": _wing("Wing", half_span=2.0, chord=0.4),
        }
        proposal = propose_import_surface_types(wings)
        assert list(proposal.values()).count(SurfaceType.MAIN_WING) == 1
        assert proposal == {
            "HTP": SurfaceType.HORIZONTAL_TAIL,
            "VTP": SurfaceType.VERTICAL_TAIL,
            "Wing": SurfaceType.MAIN_WING,
        }


class TestAssignSurfaceTypesPostPass:
    def test_overwrites_provisional_roles_and_records_one_warning(self):
        plane = AeroplaneSchema(name="X")
        plane.wings = {
            "HTP": _wing("HTP", half_span=0.5, chord=0.1, x_le=1.2),
            "Wing": _wing("Wing", half_span=2.0, chord=0.4),
        }
        warnings: list[dict] = []
        ctx = SimpleNamespace(add_warning=lambda **kw: warnings.append(kw))

        _assign_surface_types(plane, ctx, None)

        assert plane.wings["HTP"].surface_type == SurfaceType.HORIZONTAL_TAIL
        assert plane.wings["Wing"].surface_type == SurfaceType.MAIN_WING
        assert len(warnings) == 1
        assert warnings[0]["component_type"] == "WING"

    def test_no_wings_records_no_warning(self):
        plane = AeroplaneSchema(name="X")
        warnings: list[dict] = []
        ctx = SimpleNamespace(add_warning=lambda **kw: warnings.append(kw))

        _assign_surface_types(plane, ctx, None)

        assert warnings == []
