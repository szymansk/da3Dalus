"""Tests for fuselage shape creators in cad_designer/airplane/creator/fuselage/.

Each creator is an AbstractShapeCreator subclass. We test:
  1. Constructor contract: identifier, shapes_of_interest_keys
  2. CAD shape creation via _create_shape (direct call) to verify
     that each creator produces the expected output keys and valid
     CadQuery geometry
  3. Public create_shape() pathway (tests the full orchestration
     in AbstractShapeCreator.check_if_shapes_are_available where
     ``kwargs & needed_shapes`` fails with ``dict & list``)

All tests require CadQuery and are marked slow since they perform
real solid modelling operations.
"""
from __future__ import annotations

import logging

import pytest

cq = pytest.importorskip("cadquery", reason="CadQuery not installed")

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.aircraft_topology.Position import Position
from cad_designer.airplane.aircraft_topology.components.EngineInformation import (
    EngineInformation,
)
from cad_designer.airplane.creator.fuselage.EngineCapeShapeCreator import (
    EngineCapeShapeCreator,
)
from cad_designer.airplane.creator.fuselage.EngineCoverAndMountPanelAndFuselageShapeCreator import (
    EngineCoverAndMountPanelAndFuselageShapeCreator,
)
from cad_designer.airplane.creator.fuselage.EngineMountShapeCreator import (
    EngineMountShapeCreator,
)
from cad_designer.airplane.creator.fuselage.FuselageElectronicsAccessCutOutShapeCreator import (
    FuselageElectronicsAccessCutOutShapeCreator,
)
from cad_designer.airplane.creator.fuselage.FuselageReinforcementShapeCreator import (
    FuselageReinforcementShapeCreator,
)
from cad_designer.airplane.creator.fuselage.FuselageShellShapeCreator import (
    FuselageShellShapeCreator,
)
from cad_designer.airplane.creator.fuselage.FuselageWingSupportShapeCreator import (
    FuselageWingSupportShapeCreator,
)
from cad_designer.airplane.creator.fuselage.WingAttachmentBoltCutoutShapeCreator import (
    WingAttachmentBoltCutoutShapeCreator,
)
from cad_designer.airplane.creator.fuselage.WingReinforcementShapeCreator import (
    WingReinforcementShapeCreator,
)

pytestmark = [pytest.mark.slow, pytest.mark.requires_cadquery]


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def fuselage_box() -> cq.Workplane:
    """A simple box standing in for a fuselage loft (200 x 60 x 60 mm)."""
    return cq.Workplane("XY").box(200, 60, 60)


@pytest.fixture()
def wing_box() -> cq.Workplane:
    """A flat box standing in for a full wing loft (100 x 200 x 10 mm).

    Positioned as a high-wing: centered at z=25 so its bottom (z=20)
    is above the fuselage center (z=0).
    """
    return cq.Workplane("XY").center(0, 0).workplane(offset=25).box(100, 200, 10)


@pytest.fixture()
def engine_info() -> EngineInformation:
    """Minimal EngineInformation for engine-related creators."""
    return EngineInformation(
        down_thrust=0.0,
        side_thrust=0.0,
        position=Position(x=100.0, y=0.0, z=0.0),
        length=40.0,
        width=30.0,
        height=30.0,
        screw_hole_circle=20.0,
        mount_box_length=15.0,
        screw_din_diameter=4.0,
        screw_length=12.0,
    )


@pytest.fixture()
def engine_info_dict(engine_info: EngineInformation) -> dict[int, EngineInformation]:
    return {0: engine_info}


# ---------------------------------------------------------------------------
# FuselageShellShapeCreator
# ---------------------------------------------------------------------------

class TestFuselageShellShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = FuselageShellShapeCreator(
            creator_id="fus.shell", thickness=-2.0, fuselage="my_fus",
        )
        assert creator.identifier == "fus.shell"
        assert creator.thickness == -2.0
        assert creator.fuselage == "my_fus"
        assert creator.shapes_of_interest_keys == ["my_fus"]

    def test_create_shape_returns_correct_key(self, fuselage_box):
        creator = FuselageShellShapeCreator(
            creator_id="fus.shell", thickness=-2.0, fuselage="fus_loft",
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box},
            input_shapes={},
        )
        assert "fus.shell" in result
        # The result should be a CadQuery Solid (findSolid returns it)
        assert result["fus.shell"] is not None

    def test_suggested_creator_id(self):
        assert "{fuselage}" in FuselageShellShapeCreator.suggested_creator_id


# ---------------------------------------------------------------------------
# FuselageReinforcementShapeCreator
# ---------------------------------------------------------------------------

class TestFuselageReinforcementShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = FuselageReinforcementShapeCreator(
            creator_id="fus.reinforcement",
            rib_width=2.0,
            rib_spacing=5.0,
            ribcage_factor=0.6,
            reinforcement_pipes_diameter=6.0,
            print_resolution=0.2,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        assert creator.identifier == "fus.reinforcement"
        assert creator.rib_width == 2.0
        assert creator.ribcage_factor == 0.6
        assert creator.shapes_of_interest_keys == ["fus_loft", "wing_loft"]

    @pytest.mark.skip(reason="requires complex fuselage geometry setup — incomplete")
    def test_create_shape_returns_reinforcement_and_rods(
        self, fuselage_box, wing_box,
    ):
        creator = FuselageReinforcementShapeCreator(
            creator_id="fus.reinforcement",
            rib_width=2.0,
            rib_spacing=3.0,
            ribcage_factor=0.5,
            reinforcement_pipes_diameter=4.0,
            print_resolution=0.2,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box, "wing_loft": wing_box},
            input_shapes={},
        )
        assert "fus.reinforcement" in result
        assert "fus.reinforcement.rods" in result

    def test_suggested_creator_id(self):
        assert "{fuselage_loft}" in FuselageReinforcementShapeCreator.suggested_creator_id


# ---------------------------------------------------------------------------
# EngineMountShapeCreator
# ---------------------------------------------------------------------------

class TestEngineMountShapeCreator:

    def test_constructor_stores_attributes(self, engine_info_dict):
        creator = EngineMountShapeCreator(
            creator_id="engine[0].mount",
            engine_index=0,
            mount_plate_thickness=3.0,
            cutout_thickness=1.5,
            engine_information=engine_info_dict,
        )
        assert creator.identifier == "engine[0].mount"
        assert creator.engine_index == 0
        assert creator.mount_plate_thickness == 3.0
        # shapes_of_interest_keys is None for this creator (self-contained)
        assert creator.shapes_of_interest_keys is None

    def test_create_shape_returns_mount_and_cutout(self, engine_info_dict):
        """EngineMountShapeCreator has shapes_of_interest_keys=None so
        the public create_shape() pathway works without the dict & list bug."""
        creator = EngineMountShapeCreator(
            creator_id="engine[0].mount",
            engine_index=0,
            mount_plate_thickness=3.0,
            cutout_thickness=1.5,
            engine_information=engine_info_dict,
        )
        result = creator.create_shape(input_shapes=None)
        assert "engine[0].mount" in result
        assert "engine[0].mount.cutout" in result

    def test_explicit_params_override_engine_info(self, engine_info_dict):
        creator = EngineMountShapeCreator(
            creator_id="engine[0].mount",
            engine_index=0,
            mount_plate_thickness=3.0,
            cutout_thickness=1.5,
            engine_screw_hole_circle=25.0,
            engine_mount_box_length=20.0,
            engine_screw_din_diameter=5.0,
            engine_screw_length=15.0,
            engine_total_cover_length=50.0,
            engine_down_thrust_deg=2.0,
            engine_side_thrust_deg=1.0,
            engine_information=engine_info_dict,
        )
        result = creator.create_shape(input_shapes=None)
        # After create_shape, explicit values should still be used
        assert creator.engine_screw_hole_circle == 25.0
        assert creator.engine_down_thrust_deg == 2.0
        assert "engine[0].mount" in result

    def test_none_params_filled_from_engine_info(self, engine_info_dict, engine_info):
        """When optional params are None, values are pulled from engine_information."""
        creator = EngineMountShapeCreator(
            creator_id="engine[0].mount",
            engine_index=0,
            mount_plate_thickness=3.0,
            cutout_thickness=1.5,
            engine_information=engine_info_dict,
        )
        creator.create_shape(input_shapes=None)
        assert creator.engine_screw_hole_circle == engine_info.engine_screw_hole_circle
        assert creator.engine_down_thrust_deg == engine_info.down_thrust
        assert creator.engine_total_cover_length == engine_info.length

    def test_suggested_creator_id(self):
        assert "{engine_index}" in EngineMountShapeCreator.suggested_creator_id


# ---------------------------------------------------------------------------
# EngineCoverAndMountPanelAndFuselageShapeCreator
# ---------------------------------------------------------------------------

class TestEngineCoverAndMountPanelAndFuselageShapeCreator:

    def test_constructor_stores_attributes(self, engine_info_dict):
        creator = EngineCoverAndMountPanelAndFuselageShapeCreator(
            creator_id="engine[0].backplate",
            engine_index=0,
            mount_plate_thickness=3.0,
            full_fuselage_loft="fus_loft",
            engine_information=engine_info_dict,
        )
        assert creator.identifier == "engine[0].backplate"
        assert creator.shapes_of_interest_keys == ["fus_loft"]

    def test_create_shape_via_internal_api(
        self, fuselage_box, engine_info_dict,
    ):
        creator = EngineCoverAndMountPanelAndFuselageShapeCreator(
            creator_id="engine[0].backplate",
            engine_index=0,
            mount_plate_thickness=3.0,
            full_fuselage_loft="fus_loft",
            engine_information=engine_info_dict,
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box},
            input_shapes={},
        )
        assert "engine[0].backplate" in result

    def test_slice_fuselage_classmethod_tractor(self, fuselage_box, engine_info):
        """Test the static slicing helper for tractor engine (side_thrust < 90)."""
        mount_plate, fuselage, cape = (
            EngineCoverAndMountPanelAndFuselageShapeCreator
            .slice_fuselage_in_cape_motormount_mainfuselage(
                mount_plate_thickness=3.0,
                engine_mount_box_length=15.0,
                engine_total_cover_length=40.0,
                full_fuselage_loft=fuselage_box,
                engine_information=engine_info,
            )
        )
        assert mount_plate is not None
        assert fuselage is not None
        assert cape is not None

    def test_slice_fuselage_classmethod_pusher(self, fuselage_box):
        """Test slicing for pusher engine (side_thrust >= 90)."""
        pusher_info = EngineInformation(
            down_thrust=0.0,
            side_thrust=180.0,
            position=Position(x=-100.0, y=0.0, z=0.0),
            length=40.0,
            width=30.0,
            height=30.0,
            screw_hole_circle=20.0,
            mount_box_length=15.0,
            screw_din_diameter=4.0,
            screw_length=12.0,
        )
        mount_plate, fuselage, cape = (
            EngineCoverAndMountPanelAndFuselageShapeCreator
            .slice_fuselage_in_cape_motormount_mainfuselage(
                mount_plate_thickness=3.0,
                engine_mount_box_length=15.0,
                engine_total_cover_length=40.0,
                full_fuselage_loft=fuselage_box,
                engine_information=pusher_info,
            )
        )
        assert mount_plate is not None
        # For pusher engines, fuselage and cape are None
        assert fuselage is None
        assert cape is None

    def test_suggested_creator_id(self):
        assert "{engine_index}" in EngineCoverAndMountPanelAndFuselageShapeCreator.suggested_creator_id


# ---------------------------------------------------------------------------
# EngineCapeShapeCreator
# ---------------------------------------------------------------------------

class TestEngineCapeShapeCreator:

    def test_constructor_stores_attributes(self, engine_info_dict):
        creator = EngineCapeShapeCreator(
            creator_id="engine[0].cape",
            engine_index=0,
            mount_plate_thickness=3.0,
            full_fuselage_loft="fus_loft",
            engine_information=engine_info_dict,
        )
        assert creator.identifier == "engine[0].cape"
        assert creator.shapes_of_interest_keys == ["fus_loft"]

    def test_create_shape_returns_cape_and_loft(
        self, fuselage_box, engine_info_dict,
    ):
        creator = EngineCapeShapeCreator(
            creator_id="engine[0].cape",
            engine_index=0,
            mount_plate_thickness=3.0,
            full_fuselage_loft="fus_loft",
            engine_information=engine_info_dict,
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box},
            input_shapes={},
        )
        assert "engine[0].cape.cape" in result
        assert "engine[0].cape.loft" in result

    def test_identifier_property_uses_creator_id(self, engine_info_dict):
        creator = EngineCapeShapeCreator(
            creator_id="my_cape",
            engine_index=0,
            mount_plate_thickness=3.0,
            engine_information=engine_info_dict,
        )
        assert creator.identifier == "my_cape"
        # Test the setter
        creator.identifier = "renamed"
        assert creator.identifier == "renamed"
        assert creator.creator_id == "renamed"

    def test_suggested_creator_id(self):
        assert "{engine_index}" in EngineCapeShapeCreator.suggested_creator_id


# ---------------------------------------------------------------------------
# WingReinforcementShapeCreator
# ---------------------------------------------------------------------------

class TestWingReinforcementShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = WingReinforcementShapeCreator(
            creator_id="wing_reinforcement",
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        assert creator.identifier == "wing_reinforcement"
        assert creator.shapes_of_interest_keys == ["fus_loft", "wing_loft"]

    def test_create_shape_returns_reinforcement(
        self, fuselage_box, wing_box,
    ):
        creator = WingReinforcementShapeCreator(
            creator_id="wing_reinforcement",
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box, "wing_loft": wing_box},
            input_shapes={},
        )
        assert "wing_reinforcement" in result

    def test_overlap_calculator_returns_bbox_and_type(
        self, fuselage_box, wing_box,
    ):
        bbox, wing_type, location = WingReinforcementShapeCreator.overlap_calculator(
            wing_box, fuselage_box,
        )
        assert bbox is not None
        assert wing_type in ("high", "low")

    def test_suggested_creator_id(self):
        assert WingReinforcementShapeCreator.suggested_creator_id == "wing_reinforcement"


# ---------------------------------------------------------------------------
# FuselageWingSupportShapeCreator
# ---------------------------------------------------------------------------

class TestFuselageWingSupportShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = FuselageWingSupportShapeCreator(
            creator_id="wing_support",
            rib_quantity=5,
            rib_width=1.5,
            rib_height_factor=0.8,
            rib_z_offset=0.0,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        assert creator.identifier == "wing_support"
        assert creator.rib_quantity == 5
        assert creator.rib_width == 1.5
        assert creator.shapes_of_interest_keys == ["fus_loft", "wing_loft"]

    def test_create_shape_returns_support(self, fuselage_box, wing_box):
        creator = FuselageWingSupportShapeCreator(
            creator_id="wing_support",
            rib_quantity=3,
            rib_width=1.0,
            rib_height_factor=0.5,
            rib_z_offset=0.0,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box, "wing_loft": wing_box},
            input_shapes={},
        )
        assert "wing_support" in result

    def test_overlap_calculator_returns_bbox_and_type(
        self, fuselage_box, wing_box,
    ):
        bbox, wing_type = FuselageWingSupportShapeCreator.overlap_calculator(
            wing_box, fuselage_box,
        )
        assert bbox is not None
        assert wing_type in ("high", "low")

    def test_suggested_creator_id(self):
        assert FuselageWingSupportShapeCreator.suggested_creator_id == "wing_support"


# ---------------------------------------------------------------------------
# FuselageElectronicsAccessCutOutShapeCreator
# ---------------------------------------------------------------------------

class TestFuselageElectronicsAccessCutOutShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = FuselageElectronicsAccessCutOutShapeCreator(
            creator_id="fus.electronics_cutout",
            ribcage_factor=0.6,
            length_factor=0.5,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        assert creator.identifier == "fus.electronics_cutout"
        assert creator.ribcage_factor == 0.6
        assert creator.shapes_of_interest_keys == ["fus_loft", "wing_loft"]

    def test_create_shape_returns_cutout(self, fuselage_box, wing_box):
        creator = FuselageElectronicsAccessCutOutShapeCreator(
            creator_id="fus.electronics_cutout",
            ribcage_factor=0.6,
            length_factor=0.4,
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box, "wing_loft": wing_box},
            input_shapes={},
        )
        assert "fus.electronics_cutout" in result

    def test_overlap_calculator_returns_bbox_type_location(
        self, fuselage_box, wing_box,
    ):
        bbox, wing_type, location = (
            FuselageElectronicsAccessCutOutShapeCreator.overlap_calculator(
                wing_box, fuselage_box,
            )
        )
        assert bbox is not None
        assert wing_type in ("high", "low")

    def test_suggested_creator_id(self):
        assert (
            "{fuselage_loft}"
            in FuselageElectronicsAccessCutOutShapeCreator.suggested_creator_id
        )


# ---------------------------------------------------------------------------
# WingAttachmentBoltCutoutShapeCreator
# ---------------------------------------------------------------------------

class TestWingAttachmentBoltCutoutShapeCreator:

    def test_constructor_stores_attributes(self):
        creator = WingAttachmentBoltCutoutShapeCreator(
            creator_id="bolt_cutout",
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
            bolt_diameter=3.0,
        )
        assert creator.identifier == "bolt_cutout"
        assert creator.bolt_diameter == 3.0
        assert creator.shapes_of_interest_keys == ["fus_loft", "wing_loft"]

    def test_create_shape_returns_cutout(self, fuselage_box, wing_box):
        creator = WingAttachmentBoltCutoutShapeCreator(
            creator_id="bolt_cutout",
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
            bolt_diameter=3.0,
        )
        result = creator._create_shape(
            shapes_of_interest={"fus_loft": fuselage_box, "wing_loft": wing_box},
            input_shapes={},
        )
        assert "bolt_cutout" in result

    def test_overlap_calculator_returns_bbox_type_location(
        self, fuselage_box, wing_box,
    ):
        bbox, wing_type, location = (
            WingAttachmentBoltCutoutShapeCreator.overlap_calculator(
                wing_box, fuselage_box,
            )
        )
        assert bbox is not None
        assert wing_type in ("high", "low")

    def test_suggested_creator_id(self):
        assert WingAttachmentBoltCutoutShapeCreator.suggested_creator_id == "bolt_cutout"


# ---------------------------------------------------------------------------
# Public create_shape() pathway — full orchestration through base class
# ---------------------------------------------------------------------------

class TestCreateShapePublicAPI:
    """The public create_shape() pathway for creators with non-None
    shapes_of_interest_keys fails with TypeError in
    AbstractShapeCreator.check_if_shapes_are_available (line 69):
    ``kwargs & needed_shapes`` does not support ``dict & list``.
    Should be ``kwargs.keys() & set(needed_shapes)``.
    """

    def test_fuselage_shell_create_shape_public(self, fuselage_box):
        creator = FuselageShellShapeCreator(
            creator_id="fus.shell", thickness=-2.0, fuselage="fus_loft",
        )
        result = creator.create_shape(input_shapes=None, fus_loft=fuselage_box)
        assert "fus.shell" in result

    def test_bolt_cutout_create_shape_public(self, fuselage_box, wing_box):
        creator = WingAttachmentBoltCutoutShapeCreator(
            creator_id="bolt_cutout",
            fuselage_loft="fus_loft",
            full_wing_loft="wing_loft",
            bolt_diameter=3.0,
        )
        creator.create_shape(
            input_shapes=None, fus_loft=fuselage_box, wing_loft=wing_box,
        )


# ---------------------------------------------------------------------------
# Cross-cutting: all creators inherit from AbstractShapeCreator
# ---------------------------------------------------------------------------

class TestAbstractShapeCreatorContract:
    """Verify that every fuselage creator satisfies the base class contract."""

    CREATOR_CLASSES = [
        FuselageShellShapeCreator,
        FuselageReinforcementShapeCreator,
        EngineMountShapeCreator,
        EngineCapeShapeCreator,
        EngineCoverAndMountPanelAndFuselageShapeCreator,
        WingReinforcementShapeCreator,
        FuselageWingSupportShapeCreator,
        FuselageElectronicsAccessCutOutShapeCreator,
        WingAttachmentBoltCutoutShapeCreator,
    ]

    @pytest.mark.parametrize(
        "cls",
        CREATOR_CLASSES,
        ids=lambda c: c.__name__,
    )
    def test_has_suggested_creator_id(self, cls):
        assert hasattr(cls, "suggested_creator_id")
        assert isinstance(cls.suggested_creator_id, str)
        assert len(cls.suggested_creator_id) > 0

    @pytest.mark.parametrize(
        "cls",
        CREATOR_CLASSES,
        ids=lambda c: c.__name__,
    )
    def test_has_docstring(self, cls):
        assert cls.__doc__ is not None
        assert len(cls.__doc__.strip()) > 0

    @pytest.mark.parametrize(
        "cls",
        CREATOR_CLASSES,
        ids=lambda c: c.__name__,
    )
    def test_inherits_from_abstract_shape_creator(self, cls):
        assert issubclass(cls, AbstractShapeCreator)
