import logging

from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.aircraft_topology.EngineInformation import EngineInformation
from Airplane.creator.fuselage.EngineCoverAndMountPanelAndFuselageShapeCreator import EngineCoverAndMountPanelAndFuselageShapeCreator


class EngineCapeShapeCreator(AbstractShapeCreator):
    """
    Creates an engine cape <identifier>.cape and fuselage loft without the cape <identifier>.loft, by cutting the cape
    of the full fuselage loft.
    """

    def __init__(self, creator_id: str, engine_index: int, mount_plate_thickness: float,
                 engine_mount_box_length: float = None, engine_total_cover_length: float = None,
                 full_fuselage_loft: str = None, engine_information: dict[int, EngineInformation] = None,
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
