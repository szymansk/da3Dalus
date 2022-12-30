from typing import Union

import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
from Airplane.Fuselage.FuselageCutouts import FuselageCutouts
from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory
from Extra.BooleanOperationsForLists import *


class FuselageFactory:
    @classmethod
    def create_wing_support_shape(cls, rib_quantity: int, rib_width: float, rib_height_factor: float,
                                  fuselage_loft: TGeo.CNamedShape, full_wing_loft: TGeo.CNamedShape) \
            -> TGeo.CNamedShape:
        overlap_dimensions = FuselageFactory.overlap_fuselage_wing_dimensions(fuselage_loft, full_wing_loft)
        shape__wing_support = FuselageRibFactory.create_wing_support_ribs(overlap_dimensions=overlap_dimensions,
                                                                          fuselage_loft=fuselage_loft,
                                                                          full_wing_loft=full_wing_loft,
                                                                          rib_quantity=rib_quantity,
                                                                          rib_width=rib_width,
                                                                          rib_height_factor=rib_height_factor)
        return shape__wing_support

    @classmethod
    def create_hardware_cutout(cls, ribcage_factor: float, fuselage_loft: TGeo.CNamedShape,
                               full_wing_loft: TGeo.CNamedShape, position: str = Union["top", "middle", "bottom"]) \
            -> TGeo.CNamedShape:
        # Hardware Opening for inserting akku, rc, ... from the bottom
        position = position if position is not None else FuselageFactory._calc_wing_position(fuselage_loft,
                                                                                             full_wing_loft)
        shape__hardware_cutout: TGeo.CNamedShape = FuselageCutouts.create_hardware_cutout(
            PDim.ShapeDimensions(fuselage_loft), PDim.ShapeDimensions(full_wing_loft), ribcage_factor, position)
        return shape__hardware_cutout

    @classmethod
    def create_wing_support(cls, overlap_dimensions, fuselage_loft: TGeo.CNamedShape, wing_loft: TGeo.CNamedShape) -> TGeo.CNamedShape:
        # Wing Support ribs
        shape__wing_support: TGeo.CNamedShape = FuselageRibFactory.create_wing_support_ribs(
            overlap_dimensions=overlap_dimensions, fuselage_loft=fuselage_loft, full_wing_loft=wing_loft,
            rib_quantity=6, rib_width=0.0008, rib_height_factor=1.0)
        return shape__wing_support

    @classmethod
    def create_fuselage_reinforcement(cls, reinforcement_pipes_radius: float, rib_width: float, rib_spacing: float, ribcage_factor: float,
                                      fuselage_loft: TGeo.CNamedShape, full_wing_loft: TGeo.CNamedShape) -> TGeo.CNamedShape:
        internal_structure: list[TGeo.CNamedShape] = []
        # Calculate the positions for the rib
        y_max, y_min, z_max, z_min = FuselageFactory._calc_rib_positions(ribcage_factor, fuselage_loft, full_wing_loft,
                                                                         spacing=rib_spacing)

        fuselage_dimensions = PDim.ShapeDimensions(fuselage_loft);

        # Ribs
        ribs: TGeo.CNamedShape = FuselageRibFactory.create_sharp_ribs(rib_width, y_max, y_min, z_max, z_min,
                                                                      fuselage_loft)
        internal_structure.append(ribs)

        # Reinforcement Pipes
        from Airplane.ReinforcementPipeFactory import ReinforcementePipeFactory
        reinforcement_pipes: TGeo.CNamedShape = ReinforcementePipeFactory.create_reinforcement_pipe_fuselage(
            reinforcement_pipes_radius, y_max, y_min, z_max, z_min, fuselage_dimensions)
        internal_structure.append(reinforcement_pipes)

        # Fuse internal structure
        fused_internal_structure: TGeo.CNamedShape = BooleanCADOperation.fuse_list_of_namedshapes(internal_structure)

        # Create Reduction recces
        cutouts: list[TGeo.CNamedShape] = \
            FuselageFactory._create_recces_cutouts_for_fuselage_reinforcement(y_max, y_min, z_max, z_min,
                                                                              fuselage_loft=fuselage_loft)
        # cut Internal Structure
        shape__fuselage_reinforcement = BooleanCADOperation.cut_list_of_shapes(fused_internal_structure, cutouts)
        return shape__fuselage_reinforcement

    @classmethod
    def _offset_fuselage(cls, fuselage_loft: TGeo.CNamedShape, offset=0.001) -> TGeo.CNamedShape:
        """
        """
        offset_maker: OOff.BRepOffsetAPI_MakeOffsetShape = OOff.BRepOffsetAPI_MakeOffsetShape()
        offset_maker.PerformBySimple(fuselage_loft.shape(), offset)
        result = TGeo.CNamedShape(offset_maker.Shape(), f"{fuselage_loft.name()}_offset")
        msg = f"Fuselage with {str(offset)=} meters"
        ConstructionStepsViewer.instance().display_this_shape(result, severity=logging.NOTSET, msg=msg)
        return result

    @classmethod
    def _is_high_wing(cls, overlapdimension, fuselage_loft: TGeo.CNamedShape) -> bool:
        """
        :param fuselage_loft:
        :return: True if wing is on top
        """
        logging.warning(
            f"{overlapdimension.get_z_min()=} < {PDim.ShapeDimensions(fuselage_loft).get_z_max()}")
        if overlapdimension.get_z_max() > PDim.ShapeDimensions(fuselage_loft).get_z_mid():
            logging.info(f"High wing aircraft")
            return True
        else:
            return False

    @classmethod
    def _is_low_wing(cls, overlapdimension, fuselage_loft: TGeo.CNamedShape) -> bool:
        """
        return: True if wing is on bottom
        :param fuselage_loft:
        """
        logging.warning(
            f"{overlapdimension.get_z_max()=} > {PDim.ShapeDimensions(fuselage_loft).get_z_min()}")
        if overlapdimension.get_z_min() < PDim.ShapeDimensions(fuselage_loft).get_z_mid():
            logging.info(f"Low wing aircraft")
            return True
        else:
            return False

    @classmethod
    def _is_mid_wing(cls, overlapdimension, fuselage_loft: TGeo.CNamedShape, toleranz_factor=0.25) -> bool:
        """
        :param fuselage_loft:
        :param toleranz_factor: factor to determine if the wing is close to the middle default is set 0.25 (25%)
        :return: True if the Wing is near the middle of the fuselage +- tolerance
        """
        toleranz = PDim.ShapeDimensions(fuselage_loft).get_height() * toleranz_factor

        if PDim.ShapeDimensions(fuselage_loft).get_z_mid() + toleranz >= overlapdimension.get_z_mid() \
                >= PDim.ShapeDimensions(fuselage_loft).get_z_mid() - toleranz:
            return True
        else:
            return False

    @classmethod
    def overlap_fuselage_wing_dimensions(cls, fuselage_loft: TGeo.CNamedShape, full_wing_loft: TGeo.CNamedShape) -> PDim.ShapeDimensions:
        """
        Creates an overlap shape using the Opencascade function Common between wing and fuselage
        :param full_wing_loft:
        :param fuselage_loft:
        :return: the shape dimensions of the overlap shape
        """
        overlap = BooleanCADOperation.intersect_shape_with_shape(
            fuselage_loft,
            full_wing_loft,
            "Overlap")
        result0 = PDim.ShapeDimensions(overlap)
        ConstructionStepsViewer.instance().display_common(overlap,
                                                          fuselage_loft,
                                                          full_wing_loft,
                                                          logging.FATAL)
        result = PDim.ShapeDimensions(overlap)
        return result

    @classmethod
    def create_engine_cape(cls, mount_plate_thickness: float, motor_cutout_length: float,
                           full_fuselage_loft: TGeo.CNamedShape) -> list[TGeo.CNamedShape]:
        '''
        Cut the fuselage tip, so the motor can be positioned there. Fuselage loft is updated and returns the Engine cape Shape
        :param full_fuselage_loft:
        :param mount_plate_thickness:
        :param motor_cutout_length: length of the motor
        '''
        fuselage_loft: TGeo.CNamedShape = full_fuselage_loft

        fuselage_dimensions = PDim.ShapeDimensions(fuselage_loft)

        cutout_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(fuselage_dimensions.get_point(1), motor_cutout_length,
                                      fuselage_dimensions.get_width(),
                                      fuselage_dimensions.get_height()).Shape(), "cape_cut_out")
        cutout_box2 = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(fuselage_dimensions.get_point(1), motor_cutout_length+mount_plate_thickness,
                                      fuselage_dimensions.get_width(),
                                      fuselage_dimensions.get_height()).Shape(), "cape_cut_out")

        engine_cape = OAlgo.BRepAlgoAPI_Common(fuselage_loft.shape(), cutout_box.shape()).Shape()
        named_engine_cape = TGeo.CNamedShape(engine_cape, "engine_cape")

        cut_fuselage = OAlgo.BRepAlgoAPI_Cut(fuselage_loft.shape(), cutout_box2.shape()).Shape()
        named_cut_fuselage = TGeo.CNamedShape(cut_fuselage, "cut_fuselage")

        ConstructionStepsViewer.instance().display_this_shape(named_cut_fuselage, severity=logging.NOTSET)
        parts = [named_engine_cape, named_cut_fuselage]
        ConstructionStepsViewer.instance().display_slice_x(parts, logging.NOTSET)

        return [named_engine_cape, named_cut_fuselage]

    @classmethod
    def _calc_rib_positions(cls, factor, fuselage_loft: TGeo.CNamedShape, full_wing_loft: TGeo.CNamedShape,
                            spacing: float = 0.003) -> tuple[float, float, float, float]:
        y_max: float = (PDim.ShapeDimensions(fuselage_loft).get_width() * factor) / 2
        y_min: float = -y_max

        overlap_dimension: PDim.ShapeDimensions = FuselageFactory.overlap_fuselage_wing_dimensions(fuselage_loft,
                                                                                                   full_wing_loft)

        # Check if high wing or low wing
        if FuselageFactory._is_high_wing(overlap_dimension, fuselage_loft):
            z_max_below_overlap: float = overlap_dimension.get_z_min() - spacing
            z_max_calculated_with_factor: float = PDim.ShapeDimensions(fuselage_loft).get_z_mid() + (
                                                          (PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)

            # z_max can not collide with wing, and may not be smaller than the height of the fuselage * factor
            z_max: float = min(z_max_below_overlap, z_max_calculated_with_factor)
            z_min: float = PDim.ShapeDimensions(
                fuselage_loft).get_z_mid() - ((PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)
        elif FuselageFactory._is_low_wing(overlap_dimension, fuselage_loft):
            z_min_over_overlap: float = overlap_dimension.get_z_max() + spacing
            z_min_calculated_with_factor: float = PDim.ShapeDimensions(
                fuselage_loft).get_z_mid() - ((PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)

            # z_max can not collide with wing, and schould not be smaller than the height of the fuselage * factor
            z_min: float = max(z_min_over_overlap, z_min_calculated_with_factor)
            z_max = PDim.ShapeDimensions(fuselage_loft).get_z_mid() + ((PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)
        else:
            z_max = PDim.ShapeDimensions(fuselage_loft).get_z_mid() + ((PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)
            z_min = PDim.ShapeDimensions(fuselage_loft).get_z_mid() - ((PDim.ShapeDimensions(fuselage_loft).get_height() * factor) / 2)
            logging.error(f"Ribs will collide")

        return y_max, y_min, z_max, z_min

    @classmethod
    def _calc_wing_position(cls, fuselage_loft: TGeo.CNamedShape, full_wing_loft: TGeo.CNamedShape) -> str:
        overlap_dimension: PDim.ShapeDimensions = FuselageFactory.overlap_fuselage_wing_dimensions(fuselage_loft,
                                                                                                   full_wing_loft)
        position = None
        # Check if high wing or low wing
        if FuselageFactory._is_high_wing(overlap_dimension, fuselage_loft):
            position = "top"
        elif FuselageFactory._is_low_wing(overlap_dimension, fuselage_loft):
            position = "bottom"
        logging.debug(f"Plane with {position} wing")
        return position

    @classmethod
    def _create_recces_cutouts_for_fuselage_reinforcement(cls, y_max, y_min, z_max, z_min,
                                                          fuselage_loft: TGeo.CNamedShape):
        cutouts = []
        radius_factor = 0.8
        radius_with_z = ((z_max - z_min) / 2) * radius_factor
        radius_with_y = ((y_max - y_min) / 2) * radius_factor
        radius = min(radius_with_z, radius_with_y)

        distance: float = radius * 3
        quantity: int = round(PDim.ShapeDimensions(fuselage_loft).get_length() / distance) + 1
        cylinder_height = PDim.ShapeDimensions(fuselage_loft).get_height()

        cylinder_pattern: TGeo.CNamedShape = FuselageCutouts.create_cylinder_pattern(radius, cylinder_height,
                                                                                     quantity, distance)
        cylinder_pattern_ver: TGeo.CNamedShape = TGeo.CNamedShape(
            OExs.translate_shp(cylinder_pattern.shape(),
                               Ogp.gp_Vec(distance / 2, 0, PDim.ShapeDimensions(fuselage_loft).get_z_min())),
            f"{cylinder_pattern.name()}_vertikal")

        ConstructionStepsViewer.instance().display_this_shape(cylinder_pattern_ver, severity=logging.NOTSET,
                                                              msg=cylinder_pattern_ver.name())
        cutouts.append(cylinder_pattern_ver)

        cylinder_pattern_hor: TGeo.CNamedShape = TGeo.CNamedShape(
            OExs.rotate_shape(cylinder_pattern.shape(), Ogp.gp_OX(), 90), f"{cylinder_pattern.name()}_horizontal")
        z_pos: float = (z_max + z_min) / 2
        cylinder_pattern_hor.set_shape(OExs.translate_shp(cylinder_pattern_hor.shape(),
                                                          Ogp.gp_Vec(distance / 2,
                                                                     PDim.ShapeDimensions(fuselage_loft).get_height() / 2,
                                                                     z_pos)))

        ConstructionStepsViewer.instance().display_this_shape(cylinder_pattern_hor, severity=logging.NOTSET,
                                                              msg=cylinder_pattern_hor.name())
        cutouts.append(cylinder_pattern_hor)

        return cutouts
