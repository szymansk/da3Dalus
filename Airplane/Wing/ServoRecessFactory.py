import logging

import OCP.BRepAlgoAPI as OAlgo
import OCP.BRepPrimAPI as OPrim
import OCP.gp as Ogp
from OCP.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from cadquery import Workplane

class ServoRecessFactory:
    def __init__(self, cpacs_configuration, wingNr):
        self.cpacs_configuration: TConfig.CCPACSConfiguration = cpacs_configuration
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: Workplane = self.wing.get_loft()
        self.wing_shape: TopoDS_Shape = self.wing_loft.shape()
        self.wing_dimensions = PDim.ShapeDimensions(self.wing_loft)
        self.shape: TopoDS_Shape = TopoDS_Shape()
        self.shapes: list = []
        # self.ruder_dimensions=ShapeDimensions(ruder_shape)
        # self.servo_size=servo_size
        self.display = ConstructionStepsViewer.instance()
        logging.info(f"{self.wing_dimensions.__str__()}")

    def create_servoRecess_option1(self, named_ruder, servo_size=(0.0023, 0.0024, 0.0012)) -> Workplane:
        """
        Creates the recces for the given size of a servo
        :param ruder_shape: TopoDS_Shape
        :param servo_size: (float, float, float)
        :return:
        """
        logging.info(f"Creating servo Recess for {servo_size=} for {named_ruder.name()}")
        self.ruder_shape = named_ruder.fuselage()
        self.ruder_dimensions = ShapeDimensions(named_ruder)
        self.servo_size = servo_size
        # Make box for recces
        servo_recess: list[Workplane] = []
        named_servo_recess = Workplane(
            OPrim.BRepPrimAPI_MakeBox(self.servo_size[0], self.servo_size[1], self.servo_size[2]).Shape(),
            "servo_recess")
        servo_recess.append(named_servo_recess)
        servo_recess_dimension = ShapeDimensions(servo_recess[-1])

        # Make box to find y-Positioning
        section_bound_box = Workplane(
            OPrim.BRepPrimAPI_MakeBox(self.wing_dimensions.get_length(), self.servo_size[1],
                                      self.wing_dimensions.get_height()).Shape(), "bounding_box")

        y_pos = self.ruder_dimensions.get_y_min() + (
                self.ruder_dimensions.get_width() / 3) - servo_recess_dimension.get_width()

        section_bound_box.set_shape(
            OExs.translate_shp(section_bound_box.shape(), Ogp.gp_Vec(self.wing_dimensions.get_x_min(), y_pos,
                                                                     self.wing_dimensions.get_z_min())))

        servo_section = Workplane(OAlgo.BRepAlgoAPI_Common(section_bound_box.shape(), self.wing_shape).Shape(),
                                         "servosection")
        self.display.display_common(servo_section, section_bound_box, self.wing_loft, logging.NOTSET)
        section_dimensions = ShapeDimensions(servo_section)

        x_pos = section_dimensions.get_x_mid() + servo_recess_dimension.get_length() * 0.2
        y_pos = self.ruder_dimensions.get_y_min() + (
                self.ruder_dimensions.get_width() / 3) - servo_recess_dimension.get_width()
        height_dif = abs(section_dimensions.get_height() - servo_recess_dimension.get_height()) / 2
        z_pos = section_dimensions.get_z_max() - height_dif - servo_recess_dimension.get_height()
        # TODO calculate z_Position correctly. Recces does not touche the wing border

        # Display
        named_servo_recess.set_shape(OExs.translate_shp(servo_recess[-1].shape(), Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        servo_recess.append(named_servo_recess)

        self.namedshape = servo_recess[-1]
        return servo_recess[-1]

    def get_shape(self) -> Workplane:
        return self.namedshape
