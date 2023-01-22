import logging

import OCP.BRepPrimAPI as OPrim
import OCP.gp as Ogp
import OCP.ShapeFactory as OExs
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BOl
import Extra.patterns as pat
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class FuselageRibFactory:
    """
    This class is used to create the Ribs for the given wing_index.
    After initializing the class, call one of the create methods
    """

    @staticmethod
    def create_sharp_ribs(rib_width, y_max, y_min, z_max, z_min,
                          fuselage_loft: TGeo.CNamedShape) -> TGeo.CNamedShape:
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
        logging.debug(logstr)

        # Factor to make the ribs length and height bigger, to ensure that they are big enough
        factor = 0
        rib_length = PDim.ShapeDimensions(fuselage_loft).get_length() * (1.+2*factor)
        rib_height = PDim.ShapeDimensions(fuselage_loft).get_height() * (1.+2*factor)
        box = OPrim.BRepPrimAPI_MakeBox(rib_length, rib_width, rib_height).Shape()

        # move to the front by factor% and center on y-axis
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(-rib_length * factor/2, -rib_width / 2, 0))

        # vertical ribs
        x_pos = PDim.ShapeDimensions(fuselage_loft).get_x_min()
        logging.debug(f"Creating vertikal ribs")
        ver_rib = moved_box
        ver_rib_right = TGeo.CNamedShape(
            OExs.translate_shp(ver_rib, Ogp.gp_Vec(x_pos, y_max, PDim.ShapeDimensions(fuselage_loft).get_z_min())),
            f"{fuselage_loft.name()}_vertikal_rib_1")
        ver_rib_left = TGeo.CNamedShape(
            OExs.translate_shp(ver_rib, Ogp.gp_Vec(x_pos, y_min, PDim.ShapeDimensions(fuselage_loft).get_z_min())),
            f"{fuselage_loft.name()}_vertikal_rib_2")

        # Horizontal ribs
        logging.debug(f"Creating Horizontal ribs")
        hor_rib = OExs.rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_top = TGeo.CNamedShape(OExs.translate_shp(hor_rib, Ogp.gp_Vec(x_pos, rib_height / 2, z_max)),
                                       f"{fuselage_loft.name()}_horizontal_rib_1")
        hor_rib_bottom = TGeo.CNamedShape(OExs.translate_shp(hor_rib, Ogp.gp_Vec(x_pos, rib_height / 2, z_min)),
                                          f"{fuselage_loft.name()}_horizontal_rib_2")

        # Fuse all ribs
        ribs: list[TGeo.CNamedShape] = [ver_rib_right, ver_rib_left, hor_rib_top, hor_rib_bottom]
        fused_ribs = BOl.BooleanCADOperation.fuse_list_of_named_shapes(ribs)
        return fused_ribs

    @classmethod
    def create_wing_support_ribs(cls, overlap_dimensions, fuselage_loft: TGeo.CNamedShape,
                                 full_wing_loft: TGeo.CNamedShape, rib_quantity: int, rib_width: float,
                                 rib_height_factor: float) -> TGeo.CNamedShape:

        rib_length = PDim.ShapeDimensions(full_wing_loft).get_length() * 1.2
        rib_height = (overlap_dimensions.get_height()) + 0.004

        complete_distance = PDim.ShapeDimensions(fuselage_loft).get_width() * 0.8
        single_distance = complete_distance / rib_quantity

        single_rib = OPrim.BRepPrimAPI_MakeBox(rib_length, rib_width, rib_height * rib_height_factor).Shape()
        named_single_rib = TGeo.CNamedShape(single_rib, "single_rib")
        rib_pattern = pat.create_linear_pattern(named_single_rib, rib_quantity, single_distance, "y")
        rib_pattern_dimensions = PDim.ShapeDimensions(rib_pattern)

        x_pos = overlap_dimensions.get_x_mid() - rib_pattern_dimensions.get_x_mid()
        y_pos = overlap_dimensions.get_y_mid() - rib_pattern_dimensions.get_y_mid()
        z_pos = overlap_dimensions.get_z_min() - rib_pattern_dimensions.get_z_min() \
                                               - ((rib_height * rib_height_factor) - rib_height) / 2.0

        rib_pattern.set_shape(OExs.translate_shp(rib_pattern.shape(), Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        ConstructionStepsViewer.instance().display_this_shape(rib_pattern, severity=logging.NOTSET)

        return rib_pattern
