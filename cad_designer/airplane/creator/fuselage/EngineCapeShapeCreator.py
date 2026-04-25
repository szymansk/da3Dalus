import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import CreatorId, ShapeId
from cad_designer.airplane.aircraft_topology.components.EngineInformation import EngineInformation
from cad_designer.airplane.creator.fuselage.EngineCoverAndMountPanelAndFuselageShapeCreator import EngineCoverAndMountPanelAndFuselageShapeCreator


class EngineCapeShapeCreator(AbstractShapeCreator):
    """Creates an engine cape and the remaining fuselage loft without the cape section.

    Attributes:
        engine_index (int): Index of the engine in the engine information dictionary.
        mount_plate_thickness (float): Thickness of the engine mount backplate in mm.
        engine_mount_box_length (float): Length of the engine mount box in mm.
        engine_total_cover_length (float): Total length the engine cover extends in mm.
        full_fuselage_loft (str): Key of the full fuselage loft shape to slice.

    Returns:
        {id}.cape (Workplane): Detachable engine cover section.
        {id}.loft (Workplane): Remaining fuselage loft without the cape.
    """

    suggested_creator_id = "engine[{engine_index}].cape"

    def __init__(self, creator_id: CreatorId, engine_index: int, mount_plate_thickness: float,
                 engine_mount_box_length: float = None, engine_total_cover_length: float = None,
                 full_fuselage_loft: ShapeId = None, engine_information: dict[int, EngineInformation] = None,
                 loglevel=logging.INFO):
        self.full_fuselage_loft = full_fuselage_loft
        self.mount_plate_thickness = mount_plate_thickness
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_index = engine_index
        self._engine_information = engine_information
        super().__init__(creator_id, shapes_of_interest_keys=[self.full_fuselage_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating engine cape and loft --> '{self.identifier}.cape, {self.identifier}.loft'")

        self.engine_total_cover_length = self._engine_information[self.engine_index].length \
            if self.engine_total_cover_length is None \
            else self.engine_total_cover_length
        self.engine_mount_box_length = self._engine_information[self.engine_index].engine_mount_box_length \
            if self.engine_mount_box_length is None else self.engine_mount_box_length

        mount_plate, fuselage, cape = EngineCoverAndMountPanelAndFuselageShapeCreator.slice_fuselage_in_cape_motormount_mainfuselage(
            mount_plate_thickness=self.mount_plate_thickness,
            engine_mount_box_length=self.engine_mount_box_length,
            engine_total_cover_length=self.engine_total_cover_length,
            full_fuselage_loft=shapes_of_interest[
                self.full_fuselage_loft], engine_information=self._engine_information[
                self.engine_index])

        cape.display(name=f"{self.identifier}.cape", severity=logging.DEBUG)
        fuselage.display(name=f"{self.identifier}.loft", severity=logging.DEBUG)
        return {f"{self.identifier}.cape": cape, f"{self.identifier}.loft": fuselage}

    @property
    def identifier(self) -> str:
        return self.creator_id

    @identifier.setter
    def identifier(self, value) -> str:
        self.creator_id = value
