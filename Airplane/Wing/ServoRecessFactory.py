import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
from OCC.Core.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class ServoRecessFactory:
    def __init__(self, tigl_handle, wingNr):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_dimensions = PDim.ShapeDimensions(self.wing_shape)
        self.shape: OTopo.TopoDS_Shape = OTopo.TopoDS_Shape()
        self.shapes: list = []
        # self.ruder_dimensions=ShapeDimensions(ruder_shape)
        # self.servo_size=servo_size
        self.display = myDisplay.instance()
        logging.info(f"{self.wing_dimensions.__str__()}")

    def create_servoRecess_option1(self, ruder_shape, servo_size=(0.0023, 0.0024, 0.0012)):
        """
        Creates the recces for the given size of a servo
        :param ruder_shape: TopoDS_Shape
        :param servo_size: (float, float, float)
        :return:
        """
        logging.info(f"Creating servo Recess for {servo_size=}")
        self.ruder_shape = ruder_shape
        self.ruder_dimensions = ShapeDimensions(ruder_shape)
        self.servo_size = servo_size
        # Make box for recces
        servo_recess: list[TopoDS_Shape] = []
        servo_recess.append(
            OPrim.BRepPrimAPI_MakeBox(self.servo_size[0], self.servo_size[1], self.servo_size[2]).Shape())

        # Make box to find y-Positioning
        section_bound_box = OPrim.BRepPrimAPI_MakeBox(self.wing_dimensions.get_length(), self.servo_size[1],
                                                      self.wing_dimensions.get_height()).Shape()
        servo_recess_dimension = ShapeDimensions(servo_recess[-1])

        y_pos = self.ruder_dimensions.get_ymin() + (
                self.ruder_dimensions.get_width() / 3) - servo_recess_dimension.get_width()

        section_bound_box = OExs.translate_shp(section_bound_box, Ogp.gp_Vec(self.wing_dimensions.get_xmin(), y_pos,
                                                                             self.wing_dimensions.get_zmin()))

        section = OAlgo.BRepAlgoAPI_Common(section_bound_box, self.wing_shape).Shape()
        self.display.display_common(section, section_bound_box, self.wing_shape)
        section_dimensions = ShapeDimensions(section)

        x_pos = section_dimensions.get_xmid() - servo_recess_dimension.get_xmid()
        y_pos = self.ruder_dimensions.get_ymin() + (
                self.ruder_dimensions.get_width() / 3) - servo_recess_dimension.get_width()
        height_dif = abs(section_dimensions.get_height() - servo_recess_dimension.get_height()) / 2
        z_pos = section_dimensions.get_zmax() - height_dif - servo_recess_dimension.get_height()
        # TODO calculate z_Position correctly. Recces does not touche the wing border

        # Display
        servo_recess.append(OExs.translate_shp(servo_recess[-1], Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        self.display.display_in_origin(servo_recess[-1], "", True)
        self.display.display_in_origin(section_bound_box, "", True)
        self.display.display_in_origin(self.wing_shape, "", True)

        self.shape = servo_recess[-1]

    def get_shape(self) -> OTopo.TopoDS_Shape:
        return self.shape
