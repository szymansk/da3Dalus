import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
from Airplane.Fuselage.FuselageCutouts import FuselageCutouts
from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory
from Airplane.ReinforcementPipeFactory import ReinforcementePipeFactory
from Extra.BooleanOperationsForLists import *


class FuselageFactory:
    @classmethod
    def create_fuselage_with_sharp_ribs(cls,
                                        shape__fuselage_loft,
                                        cpacs_configuration,
                                        shape__fuselage_reinforcement_wing_support,
                                        fuselage_index: int = 1,
                                        right_main_wing_index: int = 1,
                                        ribcage_factor: float = 0.5) \
            -> list[TGeo.CNamedShape]:
        """
        Creates the Fuselage, with sharp ribs, reinforcement pipes, weight reduction recces,hardwareopening
        :param reinforcement_pipes_radius:
        :param rib_width:
        :param plate_thickness:
        :param engine_mount_shape: the shape of the engine mount
        :param ribcage_factor: smaller than 1, describes the size of the ribcage inside the fuselage
        :return:
        """

        # ---> create_hardware_cutout
        shape__hardware_cutout = cls.create_hardware_cutout(cpacs_configuration, fuselage_index, ribcage_factor,
                                                            right_main_wing_index)
        # <---

        # --> fuse_shapes(shape__fuselage_reinforcement_wing_support, shape__hardware_cutout) -> shape__fuselage_enf_ws_hw_cutout
        shape__fuselage_enf_ws_hw_cutout = BooleanCADOperation.cut_shape_from_shape(
            shape__fuselage_reinforcement_wing_support, shape__hardware_cutout, "Internalstrucutre")
        # <---

        myDisplay.instance().display_cut(shape__fuselage_enf_ws_hw_cutout,
                                         shape__fuselage_reinforcement_wing_support,
                                         shape__hardware_cutout)

        # shape the internal structure
        # --> intersect_internal_structure_with_fuselage_loft
        shape__internal_reinforcement_in_fuselage = BooleanCADOperation.intersect_shape_with_shape(
            shape__fuselage_loft, shape__fuselage_enf_ws_hw_cutout, "shaped_fuselage_reinforcement")
        # <---

        myDisplay.instance().display_common(shape__internal_reinforcement_in_fuselage,
                                            shape__fuselage_loft,
                                            shape__fuselage_enf_ws_hw_cutout)

        # invert internal structure, as we print solids with 0% filling
        logging.info(f"cutting internal structure from fuselage")

        # ---> create
        shape__fuselage_shape_offset = FuselageFactory._offset_fuselage(shape__fuselage_loft, offset=0.001)
        # <---

        # ---> cut
        shape__inverted_fuselage = BooleanCADOperation.cut_shape_from_shape(shape__fuselage_shape_offset,
                                                                            shape__internal_reinforcement_in_fuselage,
                                                                                f"{shape__fuselage_loft.name()}")
        # <---
        shapes = [shape__inverted_fuselage]
        myDisplay.instance().display_cut(shape__inverted_fuselage,
                                         shape__fuselage_shape_offset,
                                         shape__internal_reinforcement_in_fuselage)

        # Cutout Wings from Fuselage
        logging.info(f"Cuting wings form Fuselage")
        # ---> cut_out_wing_hull_from_shape
        shape__wing_hull = FuselageFactory._create_complete_wing_shape(cpacs_configuration,
                                                                       right_main_wing_index)
        shape__fuselage_wo_wings = BooleanCADOperation.cut_shape_from_shape(shape__inverted_fuselage,
                                                                            shape__wing_hull,
                                                                                f"{shape__fuselage_loft.name()}")
        # <---

        shapes.append(shape__fuselage_wo_wings)
        myDisplay.instance().display_cut(shape__fuselage_wo_wings,
                                         shape__inverted_fuselage,
                                         shape__wing_hull)

        # CutOut bolt hole
        # ---> create_bolt_hole
        overlap_dimensions = FuselageFactory.overlap_fuselage_wing_dimensions(cpacs_configuration, fuselage_index,
                                                                              right_main_wing_index)
        shape__bolt_holes = FuselageCutouts.create_bolt_hole(overlap_dimensions)
        # <---

        # ---> cut
        shape__fuselage_with_bolt_holes = BooleanCADOperation.cut_shape_from_shape(
            shape__fuselage_wo_wings,
            shape__bolt_holes,
            f"{shape__fuselage_loft.name()}")

        shapes.append(shape__fuselage_with_bolt_holes)
        myDisplay.instance().display_cut(shape__fuselage_with_bolt_holes, shape__fuselage_wo_wings, shape__bolt_holes)

        return shape__fuselage_with_bolt_holes

    @classmethod
    def create_wing_support_shape(cls, cpacs_configuration, rib_factory, fuselage_index, right_main_wing_index):
        overlap_dimensions = FuselageFactory.overlap_fuselage_wing_dimensions(cpacs_configuration, fuselage_index,
                                                                              right_main_wing_index)
        shape__wing_support = cls.create_wing_support(rib_factory, overlap_dimensions)
        return shape__wing_support

    @classmethod
    def create_hardware_cutout(cls, cpacs_configuration, fuselage_index, ribcage_factor, right_main_wing_index):
        # Hardware Opening for inserting akku, rc, ... from the bottom
        position = FuselageFactory._calc_wing_position(cpacs_configuration,
                                                       fuselage_index,
                                                       right_main_wing_index)
        shape__hardware_cutout: TGeo.CNamedShape = FuselageCutouts.create_hardware_cutout(
            PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()),
            PDim.ShapeDimensions(cpacs_configuration.get_wing(right_main_wing_index).get_loft()), ribcage_factor,
            position)
        return shape__hardware_cutout

    @classmethod
    def create_wing_support(cls, rib_factory, overlap_dimensions):
        # Wing Support ribs
        shape__wing_support: TGeo.CNamedShape = rib_factory.create_wing_support_ribs(overlap_dimensions)
        return shape__wing_support

    @classmethod
    def create_fuselage_reinforcement(cls, cpacs_configuration, fuselage_index, reinforcement_pipe_factory,
                                    reinforcement_pipes_radius, rib_factory, rib_width, ribcage_factor,
                                    right_main_wing_index):
        internal_structure: list[TGeo.CNamedShape] = []
        # Calculate the positions for the rib
        y_max, y_min, z_max, z_min = FuselageFactory._calc_rib_positions(ribcage_factor,
                                                                         cpacs_configuration,
                                                                         fuselage_index,
                                                                         right_main_wing_index,
                                                                         spacing=0.003)
        # Ribs
        ribs: TGeo.CNamedShape = rib_factory.create_sharp_ribs(rib_width, y_max, y_min, z_max, z_min)
        internal_structure.append(ribs)
        # Reinforcement Pipes
        reinforcement_pipes: TGeo.CNamedShape = reinforcement_pipe_factory.create_reinforcement_pipe_fuselage(
            reinforcement_pipes_radius, y_max, y_min, z_max, z_min)
        internal_structure.append(reinforcement_pipes)
        # Fuse internal structure
        fused_internal_structure: TGeo.CNamedShape = fuse_list_of_namedshapes(internal_structure)
        # Create Reduction recces
        cutouts: list[TGeo.CNamedShape] = \
            FuselageFactory._create_recces_cutouts_for_fuselage_reinforcement(y_max, y_min, z_max, z_min,
                                                                            cpacs_configuration=cpacs_configuration,
                                                                            fuselage_index=fuselage_index)
        # cut Internal Structure
        shape__fuselage_reinforcement = BooleanCADOperation.cut_list_of_shapes(fused_internal_structure, cutouts)
        return shape__fuselage_reinforcement

    @classmethod
    def _offset_fuselage(cls, fuselage_loft, offset=0.001) -> TGeo.CNamedShape:
        """
        """
        offset_maker: OOff.BRepOffsetAPI_MakeOffsetShape = OOff.BRepOffsetAPI_MakeOffsetShape()
        offset_maker.PerformBySimple(fuselage_loft.shape(), offset)
        result = TGeo.CNamedShape(offset_maker.Shape(), f"{fuselage_loft.name()}_offset")
        msg = f"Fuselage with {str(offset)=} meters"
        myDisplay.instance().display_this_shape(result, msg)
        return result

    @classmethod
    def _is_high_wing(cls, overlapdimension, cpacs_configuration, fuselage_index: int = 1) -> bool:
        """
        :return: True if wing is on top
        """
        logging.warning(
            f"{overlapdimension.get_z_min()=} < {PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_max()}")
        if overlapdimension.get_z_max() > PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid():
            logging.info(f"High wing aircraft")
            return True
        else:
            return False

    @classmethod
    def _is_low_wing(cls, overlapdimension, cpacs_configuration, fuselage_index) -> bool:
        """
        return: True if wing is on bottom
        """
        logging.warning(
            f"{overlapdimension.get_z_max()=} > {PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_min()}")
        if overlapdimension.get_z_min() < PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid():
            logging.info(f"Low wing aircraft")
            return True
        else:
            return False

    @classmethod
    def _is_mid_wing(cls, overlapdimension, cpacs_configuration, fuselage_index, toleranz_factor=0.25) -> bool:
        """
        :param toleranz_factor: factor to determine if the wing is close to the middle default is set 0.25 (25%)
        :return: True if the Wing is near the middle of the fuselage +- tolerance
        """
        toleranz = PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_height() * toleranz_factor

        if PDim.ShapeDimensions(cpacs_configuration.get_fuselage(
                fuselage_index).get_loft()).get_z_mid() + toleranz >= overlapdimension.get_z_mid() \
                >= PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() - toleranz:
            return True
        else:
            return False

    @classmethod
    def overlap_fuselage_wing_dimensions(cls, cpacs_configuration, fuselage_index,
                                         right_main_wing_index) -> PDim.ShapeDimensions:
        """
        Creates an overlap shape using the Opencascade function Common between wing and fuselage
        :return: the shape dimensions of the overlap shape
        """
        overlap = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(cpacs_configuration.get_fuselage(fuselage_index).get_loft().shape(),
                                     FuselageFactory._create_complete_wing_shape(cpacs_configuration,
                                     right_main_wing_index).shape()).Shape(),
            "Overlap")
        myDisplay.instance().display_common(overlap, cpacs_configuration.get_fuselage(fuselage_index).get_loft(),
                                            FuselageFactory._create_complete_wing_shape(cpacs_configuration,
                                            right_main_wing_index))
        result = PDim.ShapeDimensions(overlap)
        return result

    @classmethod
    def _create_complete_wing_shape(cls, cpacs_configuration, right_main_wing_index) -> TGeo.CNamedShape:
        """
        creates the complete main wing outer shape, by mirroring the right wing and fusing them together
        :return: complete wing shape
        """
        # Set up the mirror
        atrsf = Ogp.gp_Trsf()
        atrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))

        mirrored_wing_loft: TGeo.CNamedShape = cpacs_configuration.get_wing(right_main_wing_index).get_mirrored_loft()
        complete_wing: TGeo.CNamedShape = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Fuse(cpacs_configuration.get_wing(right_main_wing_index).get_loft().shape(),
                                   mirrored_wing_loft.shape()).Shape(), "Complete wing")
        myDisplay.instance().display_fuse(complete_wing, cpacs_configuration.get_wing(right_main_wing_index).get_loft(),
                                          mirrored_wing_loft)
        return complete_wing

    @classmethod
    def create_engine_cape(cls, cpacs_configuration, fuselage_index, motor_cutout_length) -> list[TGeo.CNamedShape]:
        '''
        Cut the fuselage tip, so the motor can be positioned there. Fuselage loft is updated and returns the Engine cape Shape
        :param motor_cutout_length: length of the motor
        '''
        fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(fuselage_index)
        fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()

        fuselage_dimensions = PDim.ShapeDimensions(fuselage_loft)

        cutout_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(fuselage_dimensions.get_point(1), motor_cutout_length,
                                      fuselage_dimensions.get_width(),
                                      fuselage_dimensions.get_height()).Shape(), "cape_cut_out")

        engine_cape = OAlgo.BRepAlgoAPI_Common(fuselage_loft.shape(), cutout_box.shape()).Shape()
        named_engine_cape = TGeo.CNamedShape(engine_cape, "engine_cape")

        cut_fuselage = OAlgo.BRepAlgoAPI_Cut(fuselage_loft.shape(), cutout_box.shape()).Shape()
        named_cut_fuselage = TGeo.CNamedShape(cut_fuselage, "cut_fuselage")

        myDisplay.instance().display_this_shape(named_cut_fuselage)
        parts = [named_engine_cape, named_cut_fuselage]
        myDisplay.instance().display_slice_x(parts)

        return [named_engine_cape, named_cut_fuselage]

    def _calc_motor_dimensions(self, cpacs_configuration):
        all_engines = cpacs_configuration.get_engines()

        engine_positions: TConfig.CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: TConfig.CCPACSEnginePosition = engine_positions.get_engine_position(1)
        engine_position_transformation: TGeo.CCPACSTransformation = engine_position.get_transformation()

        rotation: TGeo.CTiglPoint = engine_position_transformation.get_rotation()
        self.down_thrust_angle = rotation.y
        self.right_thrust_angle = rotation.z
        logging.info(f"{self.down_thrust_angle=},\t {self.right_thrust_angle=}")

        self.motor_position: TGeo.CCPACSPointAbsRel = engine_position_transformation.get_translation()
        logging.info(
            f"engine position= ({self.motor_position.get_x()},\t {self.motor_position.get_y()},\t {self.motor_position.get_z()})")

        engine_scaling: TGeo.CTiglPoint = engine_position_transformation.get_scaling()
        self.engine_length = engine_scaling.x
        self.engine_width = engine_scaling.y
        self.engine_height = engine_scaling.z
        self.engine_schaft_lenght = self.engine_length / 3
        logging.info(
            f"engine size= length: {self.engine_length},width: {self.engine_width}, height: {self.engine_height},\t")

    @classmethod
    def _calc_rib_positions(cls, factor, cpacs_configuration, fuselage_index,
                            right_main_wing_index, spacing: float = 0.003):
        y_max: float = (PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_width() * factor) / 2
        y_min: float = -y_max

        overlap_dimension: PDim.ShapeDimensions = FuselageFactory.overlap_fuselage_wing_dimensions(cpacs_configuration,
                                                                                                   fuselage_index,
                                                                                                   right_main_wing_index)

        # Check if high wing or low wing
        if FuselageFactory._is_high_wing(overlap_dimension, cpacs_configuration, fuselage_index):
            z_max_below_overlap: float = overlap_dimension.get_z_min() - spacing
            z_max_calculated_with_factor: float = PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() + (
                                                          (PDim.ShapeDimensions(cpacs_configuration.get_fuselage(
                                                              fuselage_index).get_loft()).get_height() * factor) / 2)

            # z_max can not collide with wing, and may not be smaller than the height of the fuselage * factor
            z_max: float = min(z_max_below_overlap, z_max_calculated_with_factor)
            z_min: float = PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() - ((PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_height() * factor) / 2)
        elif FuselageFactory._is_low_wing(overlap_dimension, cpacs_configuration, fuselage_index):
            z_min_over_overlap: float = overlap_dimension.get_z_max() + spacing
            z_min_calculated_with_factor: float = PDim.ShapeDimensions(
                cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() - (
                                                          (PDim.ShapeDimensions(cpacs_configuration.get_fuselage(
                                                              fuselage_index).get_loft()).get_height() * factor) / 2)

            # z_max can not collide with wing, and schould not be smaller than the height of the fuselage * factor
            z_min: float = max(z_min_over_overlap, z_min_calculated_with_factor)
            z_max = PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() + ((
                                                         PDim.ShapeDimensions(
                                                             cpacs_configuration.get_fuselage(
                                                                 fuselage_index).get_loft()).get_height() * factor) / 2)
        else:
            z_max = PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() + ((
                                                         PDim.ShapeDimensions(
                                                             cpacs_configuration.get_fuselage(
                                                                 fuselage_index).get_loft()).get_height() * factor) / 2)
            z_min = PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_mid() - ((
                                                         PDim.ShapeDimensions(
                                                             cpacs_configuration.get_fuselage(
                                                                 fuselage_index).get_loft()).get_height() * factor) / 2)
            logging.error(f"Ribs will collide")

        return y_max, y_min, z_max, z_min

    @classmethod
    def _calc_wing_position(cls, cpacs_configuration, fuselage_index, right_main_wing_index):
        overlap_dimension: PDim.ShapeDimensions = FuselageFactory.overlap_fuselage_wing_dimensions(cpacs_configuration,
                                                                                                   fuselage_index,
                                                                                                   right_main_wing_index)
        position = None
        # Check if high wing or low wing
        if FuselageFactory._is_high_wing(overlap_dimension, cpacs_configuration, fuselage_index):
            position = "top"
        elif FuselageFactory._is_low_wing(overlap_dimension, cpacs_configuration, fuselage_index):
            position = "bottom"
        logging.info(f"Plane with {position} wing")
        return position

    @classmethod
    def _create_recces_cutouts_for_fuselage_reinforcement(cls, y_max, y_min, z_max, z_min, cpacs_configuration, fuselage_index):
        cutouts = []
        radius_factor = 0.8
        radius_with_z = ((z_max - z_min) / 2) * radius_factor
        radius_with_y = ((y_max - y_min) / 2) * radius_factor
        radius = min(radius_with_z, radius_with_y)

        distance: float = radius * 3
        quantity: int = round(PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_length() / distance) + 1
        cylinder_height = PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_height()

        cylinder_pattern: TGeo.CNamedShape = FuselageCutouts.create_cylinder_pattern(radius, cylinder_height,
                                                                                     quantity, distance)
        cylinder_pattern_ver: TGeo.CNamedShape = TGeo.CNamedShape(OExs.translate_shp(cylinder_pattern.shape(),
                                                                                     Ogp.gp_Vec(distance / 2, 0,
                                                                                                PDim.ShapeDimensions(
                                                                                                    cpacs_configuration.get_fuselage(
                                                                                                        fuselage_index).get_loft()).get_z_min())),
                                                                  f"{cylinder_pattern.name()}_vertikal")

        myDisplay.instance().display_this_shape(cylinder_pattern_ver, cylinder_pattern_ver.name())
        cutouts.append(cylinder_pattern_ver)

        cylinder_pattern_hor: TGeo.CNamedShape = TGeo.CNamedShape(
            OExs.rotate_shape(cylinder_pattern.shape(), Ogp.gp_OX(), 90), f"{cylinder_pattern.name()}_horizontal")
        z_pos: float = (z_max + z_min) / 2
        cylinder_pattern_hor.set_shape(OExs.translate_shp(cylinder_pattern_hor.shape(),
                                                          Ogp.gp_Vec(distance / 2,
                                                                     PDim.ShapeDimensions(
                                                                         cpacs_configuration.get_fuselage(
                                                                             fuselage_index).get_loft()).get_height() / 2,
                                                                     z_pos)))

        myDisplay.instance().display_this_shape(cylinder_pattern_hor, cylinder_pattern_hor.name())
        cutouts.append(cylinder_pattern_hor)

        return cutouts
