import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BOl
import Extra.patterns as pat
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class FuselageRibFactory:
    """
    This class is used to create the Ribs for the given wing_index.
    After initializing the class, call one of the create methods
    """

    def __init__(self, fuselage_loft, wing_loft):
        logging.info(f"Initializing FuselageRibFactory")

        self.display = myDisplay.instance()
        self.fuselage_loft = fuselage_loft
        self.fuselage_coordinates = PDim.ShapeDimensions(self.fuselage_loft)

        self.wing_loft = wing_loft
        self.wing_coordinates = PDim.ShapeDimensions(self.wing_loft)

        self.rib_width = None
        self.factor = None

        self.shape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list[TGeo.CNamedShape] = []

    def create_sharp_ribs(self, rib_width, y_max, y_min, z_max, z_min) -> TGeo.CNamedShape:
        """
        Create a rib cage with a # profile
        :param rib_width: describes the width of the rib
        :param y_max: postion of the first vertikal rib
        :param y_min: postion of the second vertikal rib
        :param z_max: postion of the first horizontal rib
        :param z_min: postion of the first horizontal rib
        :return: namedshape of the created ribs
        """
        logstr = f"Quadrat ribs: x_pos=0 y_max={y_max:.3f} y_min={y_min:.3f} z_max={z_max:.3f} z_min={z_min:.3f}"
        logging.info(logstr)

        # Factor to make the ribs length and height bigger, to ensure that they are big enough
        factor = 1.2
        rib_length = self.fuselage_coordinates.get_length() * factor
        rib_height = self.fuselage_coordinates.get_height() * factor
        box = OPrim.BRepPrimAPI_MakeBox(rib_length, rib_width, rib_height).Shape()

        # move to the front by 10% and center on y-axis
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(-rib_length * 0.1, -rib_width / 2, 0))

        # vertical ribs
        logging.info(f"Creating vertikal ribs")
        ver_rib = moved_box
        ver_rib_right = TGeo.CNamedShape(
            OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_max, self.fuselage_coordinates.get_z_min())),
            f"{self.fuselage_loft.name()}_vertikal_rib_1")
        ver_rib_left = TGeo.CNamedShape(
            OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_min, self.fuselage_coordinates.get_z_min())),
            f"{self.fuselage_loft.name()}_vertikal_rib_2")

        # Horizontal ribs
        logging.info(f"Creating Horizontal ribs")
        hor_rib = OExs.rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_top = TGeo.CNamedShape(OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, rib_height / 2, z_max)),
                                       f"{self.fuselage_loft.name()}_horizontal_rib_1")
        hor_rib_bottom = TGeo.CNamedShape(OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, rib_height / 2, z_min)),
                                          f"{self.fuselage_loft.name()}_horizontal_rib_2")

        # Fuse all ribs
        ribs: list[TGeo.CNamedShape] = [ver_rib_right, ver_rib_left, hor_rib_top, hor_rib_bottom]
        fused_ribs = BOl.fuse_list_of_namedshapes(ribs)
        self.shape = fused_ribs
        return fused_ribs

    def get_shape(self) -> TGeo.CNamedShape:
        return self.shape

    def create_wing_support_ribs(self, overlap_dimensions) -> TGeo.CNamedShape:

        rib_quantity = 6
        rib_length = self.wing_coordinates.get_length() * 1.2
        rib_width = 0.0008
        rib_height = overlap_dimensions.get_height() + 0.004

        complete_distance = self.fuselage_coordinates.get_width() * 0.8
        single_distance = complete_distance / rib_quantity

        single_rib = OPrim.BRepPrimAPI_MakeBox(rib_length, rib_width, rib_height).Shape()
        named_single_rib = TGeo.CNamedShape(single_rib, "single_rib")
        rib_pattern = pat.create_linear_pattern(named_single_rib, rib_quantity, single_distance, "y")
        rib_pattern_dimensions = PDim.ShapeDimensions(rib_pattern)

        x_pos = overlap_dimensions.get_x_mid() - rib_pattern_dimensions.get_x_mid()
        y_pos = overlap_dimensions.get_y_mid() - rib_pattern_dimensions.get_y_mid()
        z_pos = overlap_dimensions.get_z_min() - rib_pattern_dimensions.get_z_min()

        rib_pattern.set_shape(OExs.translate_shp(rib_pattern.shape(), Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        self.display.display_this_shape(rib_pattern)

        return rib_pattern
