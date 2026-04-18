import logging
from math import sqrt, fmod, radians

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.aircraft_topology.components.EngineInformation import EngineInformation


class EngineMountShapeCreator(AbstractShapeCreator):
    """Creates a parametric engine mount with screw holes and mounting cutout.

    Attributes:
        engine_index (int): Index of the engine in the engine information dictionary.
        mount_plate_thickness (float): Thickness of the mount backplate in mm.
        cutout_thickness (float): Thickness of the mount plate cutout in mm.
        engine_screw_hole_circle (float): Diameter of the screw hole circle in mm.
        engine_mount_box_length (float): Length of the engine mount box in mm.
        engine_screw_din_diameter (float): DIN diameter of engine screws (e.g. 4 for M4).
        engine_screw_length (float): Length of the engine mounting screws in mm.
        engine_total_cover_length (float): Total engine cover length in mm.
        engine_down_thrust_deg (float): Down thrust angle in degrees.
        engine_side_thrust_deg (float): Side thrust angle in degrees.

    Returns:
        {id} (Workplane): Engine mount plate with screw holes.
        {id}.cutout (Workplane): Cutout shape for cabling access.
    """

    def __init__(self, creator_id: str, engine_index: int, mount_plate_thickness: float, cutout_thickness,
                 engine_screw_hole_circle: float = None, engine_mount_box_length: float = None,
                 engine_screw_din_diameter: float = None, engine_screw_length: float = None,
                 engine_total_cover_length: float = None, engine_down_thrust_deg: float = None,
                 engine_side_thrust_deg: float = None, engine_information: dict[int, EngineInformation] = None,
                 loglevel=logging.INFO):
        """

        :param engine_index:
        :param creator_id:
        :param mount_plate_thickness: thickness of the mount backplate
        :param engine_screw_hole_circle: the diameter of the screw circle of the engine mount
        :param engine_total_cover_length: the length of the engine from where it touches the mount to the point which should be outside the cape
        :param engine_mount_box_length: length of the box, the engine is screwd onto. (can be used to give place for a shaft)
        :param engine_down_thrust_deg: down thrust in degree
        :param engine_side_thrust_deg: side thrust in degree
        :param engine_screw_din_diameter: diameter of the screws used to fix the engine (e.g. 4 for M4)
        :param engine_screw_length: length of the screws used to fix the engine
        :param cpacs_configuration:
        """
        self.engine_index = engine_index
        self.engine_screw_length = engine_screw_length
        self.engine_screw_hole_circle = engine_screw_hole_circle
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_down_thrust_deg = engine_down_thrust_deg
        self.engine_side_thrust_deg = engine_side_thrust_deg
        self.engine_screw_din_diameter = engine_screw_din_diameter
        self.mount_plate_thickness = mount_plate_thickness
        self.cutout_thickness = cutout_thickness
        self._engine_information = engine_information
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f" creating mount for engine '{self.engine_index}' --> '{self.identifier}'")

        self.engine_down_thrust_deg = self._engine_information[self.engine_index].down_thrust \
            if self.engine_down_thrust_deg is None else self.engine_down_thrust_deg
        self.engine_side_thrust_deg = self._engine_information[self.engine_index].side_thrust \
            if self.engine_side_thrust_deg is None else self.engine_side_thrust_deg
        self.engine_total_cover_length = self._engine_information[self.engine_index].length \
            if self.engine_total_cover_length is None \
            else self.engine_total_cover_length
        self.engine_screw_length = self._engine_information[self.engine_index].engine_screw_length \
            if self.engine_screw_length is None else self.engine_screw_length
        self.engine_screw_hole_circle = self._engine_information[self.engine_index].engine_screw_hole_circle \
            if self.engine_screw_hole_circle is None else self.engine_screw_hole_circle
        self.engine_mount_box_length = self._engine_information[self.engine_index].engine_mount_box_length \
            if self.engine_mount_box_length is None else self.engine_mount_box_length
        self.engine_screw_din_diameter = self._engine_information[self.engine_index].engine_screw_din_diameter \
            if self.engine_screw_din_diameter is None else self.engine_screw_din_diameter

        mount, cutout = self._create_engine_mount(engine_total_cover_length=self.engine_total_cover_length,
                                                             engine_mount_box_length=self.engine_mount_box_length,
                                                             engine_down_thrust_deg=self.engine_down_thrust_deg,
                                                             engine_side_thrust_deg=self.engine_side_thrust_deg,
                                                             engine_screw_hole_circle=self.engine_screw_hole_circle,
                                                             engine_screw_din_diameter=self.engine_screw_din_diameter,
                                                             engine_information=self._engine_information[
                                                                 self.engine_index],
                                                             cutout_thickness=self.cutout_thickness)
        mount.display(name=self.identifier, severity=logging.DEBUG)
        cutout.display(name=f"{self.identifier}.cutout", severity=logging.DEBUG)

        return {str(self.identifier): mount, f"{self.identifier}.cutout": cutout}


    def _create_engine_mount(self, engine_total_cover_length: float, engine_mount_box_length: float, engine_down_thrust_deg: float,
                            engine_side_thrust_deg: float, engine_screw_hole_circle: float, engine_screw_din_diameter: float,
                            engine_information: EngineInformation, cutout_thickness: float) -> tuple[Workplane, Workplane]:

        motor_position = engine_information.position
        origin = (motor_position.get_x(),motor_position.get_y(),motor_position.get_z())
        # Shaft Box
        mount = cq.Workplane("YZ").box(engine_screw_hole_circle, engine_screw_hole_circle, engine_mount_box_length)\
                    .faces(">X").tag('rear').rect(sqrt(0.5)*engine_screw_hole_circle, sqrt(0.5)*engine_screw_hole_circle).cutBlind(-engine_mount_box_length * 1.2)\
                    .faces("<X").transformed(rotate=(engine_down_thrust_deg, fmod(engine_side_thrust_deg, 180.0),0))\
                    .rect(sqrt(0.5)*engine_screw_hole_circle,sqrt(0.5)*engine_screw_hole_circle,forConstruction=True).last()\
                    .vertices().tag('corners').cylinder(engine_mount_box_length*1,(engine_screw_din_diameter+6)/2).faces("<X").tag('cyl')\
                    .vertices(tag='corners').cylinder(engine_mount_box_length*1.2,(engine_screw_din_diameter+6)/2).faces("<X")\
                    .vertices(tag='corners').cylinder(engine_mount_box_length*2,(engine_screw_din_diameter)/2, combine='cut')\
                    .faces(tag='cyl').rect(engine_screw_hole_circle*10,engine_screw_hole_circle*10).extrude(-100, combine='cut')\
                    .faces(tag='rear').workplane().rect(engine_screw_hole_circle*10,engine_screw_hole_circle*10).extrude(100, combine='cut')

        cutout = cq.Workplane().copyWorkplane(mount.faces(tag='rear')).box(
            sqrt(0.5) * (engine_screw_hole_circle-(engine_screw_din_diameter+6)/2),
            sqrt(0.5) * (engine_screw_hole_circle-(engine_screw_din_diameter+6)/2),
            cutout_thickness*2, centered=(True, True, True))

        origin = cq.Vector(motor_position.get_x(),motor_position.get_y(),motor_position.get_z())
        rot_mat = cq.Matrix()
        rot_mat.rotateY(radians(fmod(engine_information.side_thrust,180)))
        rot_mat.rotateZ(radians(engine_information.down_thrust))

        l = cq.Vector(engine_total_cover_length, 0, 0)
        target = rot_mat.multiply(l)
        target.x = engine_total_cover_length  # TODO: this is a little hack!

        mount = mount.translate(target+cq.Vector(engine_mount_box_length/2, 0, 0))
        cutout = cutout.translate(target+cq.Vector(engine_mount_box_length/2, 0, 0))

        if abs(engine_side_thrust_deg) > 90.0:
            mount = mount.rotate((0,0,0),(0,0,1),180)
            cutout = cutout.rotate((0,0,0),(0,0,1),180)
        motor_position = engine_information.position
        mount = mount.translate(origin)
        cutout = cutout.translate(origin)

        return mount, cutout
