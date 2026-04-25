import logging
from math import radians, fmod

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import ShapeId
from cad_designer.airplane.aircraft_topology.components.EngineInformation import EngineInformation


class EngineCoverAndMountPanelAndFuselageShapeCreator(AbstractShapeCreator):
    """Creates an engine mount backplate by slicing a section from the fuselage.

    Attributes:
        engine_index (int): Index of the engine in the engine information dictionary.
        mount_plate_thickness (float): Thickness of the mount backplate in mm.
        engine_screw_hole_circle (float): Diameter of the engine screw hole circle in mm.
        engine_mount_box_length (float): Length of the engine mount box in mm.
        engine_total_cover_length (float): Total engine cover length in mm.
        engine_side_thrust_deg (float): Side thrust angle in degrees.
        engine_down_thrust_deg (float): Down thrust angle in degrees.
        full_fuselage_loft (str): Key of the full fuselage loft shape.

    Returns:
        {id} (Workplane): Engine mount backplate sliced from fuselage.
    """

    suggested_creator_id = "engine[{engine_index}].backplate"

    def __init__(self, creator_id: str, engine_index: int, mount_plate_thickness: float,
                 engine_screw_hole_circle: float = None, engine_mount_box_length: float = None,
                 engine_total_cover_length: float = None, engine_side_thrust_deg: float = None,
                 engine_down_thrust_deg: float = None, full_fuselage_loft: ShapeId = None,
                 engine_information: dict[int, EngineInformation] = None, loglevel=logging.INFO):
        """
        Cuts a slice of the fuselage to use as a backplate for the engine mount. A hole is
        added behinde the engine mount for cabels.

        :param engine_index:
        :param creator_id:
        :param mount_plate_thickness: thickness of the mount backplate
        :param engine_screw_hole_circle: the diameter of the screw circle of the engine mount
        :param engine_total_cover_length: the length of the engine from where it touches the mount to the point which should be outside the cape
        :param engine_mount_box_length: length of the box, the engine is screwd onto. (can be used to give place for a shaft)
        :param engine_down_thrust_deg: down thrust in degree
        :param engine_side_thrust_deg: side thrust in degree
        """
        self.full_fuselage_loft = full_fuselage_loft
        self.engine_index = engine_index
        self.engine_screw_hole_circle = engine_screw_hole_circle
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_down_thrust_deg = engine_down_thrust_deg
        self.engine_side_thrust_deg = engine_side_thrust_deg
        self.mount_plate_thickness = mount_plate_thickness
        self._engine_information = engine_information
        super().__init__(creator_id, shapes_of_interest_keys=[self.full_fuselage_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f" creating mount panel for engine '{self.engine_index}' --> '{self.identifier}'")

        self.engine_down_thrust_deg = self._engine_information[self.engine_index].down_thrust \
            if self.engine_down_thrust_deg is None else self.engine_down_thrust_deg
        self.engine_side_thrust_deg = self._engine_information[self.engine_index].side_thrust \
            if self.engine_side_thrust_deg is None else self.engine_side_thrust_deg
        self.engine_total_cover_length = self._engine_information[self.engine_index].length \
            if self.engine_total_cover_length is None \
            else self.engine_total_cover_length
        self.engine_mount_box_length = self._engine_information[self.engine_index].engine_mount_box_length \
            if self.engine_mount_box_length is None else self.engine_mount_box_length

        mount_plate, _, _ = EngineCoverAndMountPanelAndFuselageShapeCreator.slice_fuselage_in_cape_motormount_mainfuselage(
            mount_plate_thickness=self.mount_plate_thickness,
            engine_mount_box_length=self.engine_mount_box_length,
            engine_total_cover_length=self.engine_total_cover_length,
            full_fuselage_loft=shapes_of_interest[
                self.full_fuselage_loft], engine_information=self._engine_information[
                self.engine_index])

        mount_plate.display(name=f"{self.identifier}", severity=logging.DEBUG)

        return {f"{self.identifier}": mount_plate}

    @classmethod
    def slice_fuselage_in_cape_motormount_mainfuselage(cls, mount_plate_thickness: float,
                                                       engine_mount_box_length: float,
                                                       engine_total_cover_length: float,
                                                       full_fuselage_loft: Workplane,
                                                       engine_information: EngineInformation) \
            -> tuple[Workplane, Workplane, Workplane]:
        '''
        Cuts a slice of the Fuselage to use as a backplate for the engine mount
        '''
        motor_position = engine_information.position
        origin = cq.Vector(motor_position.get_x(),motor_position.get_y(),motor_position.get_z())
        rot_mat = cq.Matrix()
        rot_mat.rotateY(radians(fmod(engine_information.side_thrust,180)))
        rot_mat.rotateZ(radians(engine_information.down_thrust))

        l = cq.Vector(engine_total_cover_length, 0, 0)
        target = rot_mat.multiply(l)

        fuselage: Workplane|None = None
        engine_cape: Workplane|None = None
        if abs(engine_information.side_thrust) < 90:
            mount_plate = full_fuselage_loft.faces("<X").workplane(origin=origin, invert=True, offset=engine_total_cover_length + engine_mount_box_length+mount_plate_thickness)
            fuselage = mount_plate.split(keepTop=True)
            mount_plate = mount_plate.split(keepBottom=True)
            mount_plate = mount_plate.faces(">X").workplane(invert=True, offset=mount_plate_thickness)
            engine_cape = mount_plate.split(keepTop=True)
            mount_plate = mount_plate.split(keepBottom=True)
        else: # pusher engine at the tail
            mount_plate = full_fuselage_loft.faces(">X").workplane(origin=origin, invert=True, offset=engine_total_cover_length + engine_mount_box_length+mount_plate_thickness)\
                .split(keepBottom=True).faces("<X").workplane(invert=True, offset=mount_plate_thickness).split(keepBottom=True)

        return mount_plate, fuselage, engine_cape
