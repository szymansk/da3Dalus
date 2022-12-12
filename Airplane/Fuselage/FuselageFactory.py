import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig
from OCC.Core.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Airplane.Fuselage.FuselageCutouts import FuselageCutouts
from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory
from Airplane.ReinforcementPipeFactory import ReinforcementePipeFactory
from Extra.BooleanOperationsForLists import *


class FuselageFactory:
    def __init__(self, cpacs_configuration, fuselage_index: int = 1, right_main_wing_index: int = 1) -> None:
        self.md = myDisplay.instance()
        self.cpacs_configuration = cpacs_configuration

        self.fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(fuselage_index)
        logging.info(f"Creating Fuselage Shape: {self.fuselage.get_name()}")

        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_dimensions = PDim.ShapeDimensions(self.fuselage_loft)

        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(right_main_wing_index)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: TopoDS_Shape = self.wing_loft.shape()
        self.wing_shape_complete: TGeo.CNamedShape = self._create_complete_wing_shape()
        self.wing_dimensions = PDim.ShapeDimensions(self.wing_loft)

        self.rib_factory = FuselageRibFactory(self.fuselage_loft, self.wing_loft)
        self.reinforcement_pipe_factory = ReinforcementePipeFactory(self.wing, self.fuselage)
        self.cutouts = FuselageCutouts()
        self._calc_motor_dimensions()

        self.shape = None
        self.shapes = []
        self.fuselage_parts: list[TGeo.CNamedShape] = []

    def create_fuselage_with_sharp_ribs(self, engine_mount_factory: EngineMountFactory, factor=0.5) -> TGeo.CNamedShape:
        """
        Creates the Fuselage, with sharp ribs, reinforcement pipes, weight reduction recces,hardwareopening
        :param factor: smaller than 1, describes the size of the ribcage inside the fuselage
        :return:
        """

        # Create Motor cape and shorten fuselage
        plate_thickness = 0.005
        motor_cutout_length = self.engine_length + self.engine_length + plate_thickness
        engine_cape = self._create_engine_cape(motor_cutout_length)
        self.fuselage_parts.append(engine_cape)

        # Create Motor mount
        engine_mount = engine_mount_factory.create_engine_mount(plate_thickness)
        self.fuselage_parts.append(engine_mount)

        internal_structure: list[TGeo.CNamedShape] = []

        # Calculate the positions for the rib
        y_max, y_min, z_max, z_min = self._calc_rib_positions(factor)

        # Ribs
        rib_width: float = 0.002
        ribs: TGeo.CNamedShape = self.rib_factory.create_sharp_ribs(rib_width, y_max, y_min, z_max, z_min)
        internal_structure.append(ribs)

        # Reinforcement Pipes
        radius: float = 0.003
        reinforcement_pipes: TGeo.CNamedShape = self.reinforcement_pipe_factory.create_reinforcement_pipe_fuselage(
            radius, y_max, y_min, z_max, z_min)
        internal_structure.append(reinforcement_pipes)

        # Fuse internal structure
        fused_internal_structure: TGeo.CNamedShape = fuse_list_of_namedshapes(internal_structure)

        # Create Reduction recces
        cutouts, hardware_cutout = self._create_recces_cutouts(y_max, y_min, z_max, z_min, factor)

        # cuted Internal Structure
        cuted_internal_structure: list[TGeo.CNamedShape] = [cut_list_of_shapes(fused_internal_structure, cutouts)]

        # Wing Support ribs
        overlap_dimensions = self.overlap_fuselage_wing_dimensions()
        wing_support: TGeo.CNamedShape = self.rib_factory.create_wing_support_ribs(overlap_dimensions)
        cuted_internal_structure.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Fuse(cuted_internal_structure[-1].shape(), wing_support.shape()).Shape(),
            "Internalstructure"))
        self.md.display_fuse(cuted_internal_structure[-1], cuted_internal_structure[-2], wing_support)

        # Hardware_cutout
        cuted_internal_structure.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(cuted_internal_structure[-1].shape(), hardware_cutout.shape()).Shape(),
            "Internalstructure"))
        self.md.display_cut(cuted_internal_structure[-1], cuted_internal_structure[-2], hardware_cutout)

        # Shape the internal strukture
        cuted_internal_structure.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(self.fuselage_loft.shape(), cuted_internal_structure[-1].shape()).Shape(),
            "Shaped_internalestrukture"))
        self.md.display_common(cuted_internal_structure[-1], self.fuselage_loft, cuted_internal_structure[-2])

        # Inverse internal Strukture
        logging.info(f"Cuting internatl strukture form Fuselage")
        self.fuselage_shape_offset = self._offset_fuselage()
        self.shapes.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape_offset.shape(), cuted_internal_structure[-1].shape()).Shape(),
            f"{self.fuselage_loft.name()}"))
        self.md.display_cut(self.shapes[-1], self.fuselage_shape_offset, cuted_internal_structure[-1])

        # Cutout Wings from Fuselage
        logging.info(f"Cuting wings form Fuselage")
        self.shapes.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), self.wing_shape_complete.shape()).Shape(),
            f"{self.fuselage_loft.name()}"))
        self.md.display_cut(self.shapes[-1], self.shapes[-1], self.wing_shape_complete)

        # CutOut bolt hole
        bolt_holes = self.cutouts.create_bolt_hole(overlap_dimensions)
        self.shapes.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), bolt_holes.shape()).Shape(),
            f"{self.fuselage_loft.name()}"))
        self.md.display_cut(self.shapes[-1], self.shapes[-1], bolt_holes)

        return self.shapes[-1]

    def get_shape(self) -> TGeo.CNamedShape:
        return self.shapes[-1]

    def _offset_fuselage(self, offset=0.001) -> TGeo.CNamedShape:
        """
        """
        offset_maker: OOff.BRepOffsetAPI_MakeOffsetShape = OOff.BRepOffsetAPI_MakeOffsetShape()
        offset_maker.PerformBySimple(self.fuselage_loft.shape(), offset)
        result = TGeo.CNamedShape(offset_maker.Shape(), f"{self.fuselage_loft.name()}_offset")
        msg = f"Fuselage with {str(offset)=} meters"
        self.md.display_this_shape(result, msg)
        return result

    def _is_high_wing(self, overlapdimension) -> bool:
        """
        :return: True if wing is on top
        """
        logging.warning(f"{overlapdimension.get_z_min()=} < {self.fuselage_dimensions.get_z_max()}")
        if overlapdimension.get_z_max() > self.fuselage_dimensions.get_z_mid():
            logging.info(f"High wing aircraft")
            return True
        else:
            return False

    def _is_low_wing(self, overlapdimension) -> bool:
        """
        return: True if wing is on bottom
        """
        logging.warning(f"{overlapdimension.get_z_max()=} > {self.fuselage_dimensions.get_z_min()}")
        if overlapdimension.get_z_min() < self.fuselage_dimensions.get_z_mid():
            logging.info(f"Low wing aircraft")
            return True
        else:
            return False

    def _is_mid_wing(self, overlapdimension, toleranz_factor=0.25) -> bool:
        """
        :param toleranz_factor: factor to determine if the wing is close to the middle default is set 0.25 (25%)
        :return: True if the Wing is near the middle of the fuselage +- tolerance
        """
        toleranz = self.fuselage_dimensions.get_height() * toleranz_factor

        if self.fuselage_dimensions.get_z_mid() + toleranz >= overlapdimension.get_z_mid() \
                >= self.fuselage_dimensions.get_z_mid() - toleranz:
            return True
        else:
            return False

    def overlap_fuselage_wing_dimensions(self) -> PDim.ShapeDimensions:
        """
        Creates an overlap shape using the Opencascade function Common between wing and fuselage
        :return: the shape dimensions of the overlap shape
        """
        overlap = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(self.fuselage_loft.shape(), self.wing_shape_complete.shape()).Shape(), "Overlap")
        self.md.display_common(overlap, self.fuselage_loft, self.wing_shape_complete)
        result = PDim.ShapeDimensions(overlap)
        return result

    def _create_complete_wing_shape(self) -> TGeo.CNamedShape:
        """
        creates the complete main wing outer shape, by mirroring the right wing and fusing them together
        :return: complete wing shape
        """
        # Set up the mirror
        atrsf = Ogp.gp_Trsf()
        atrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))

        mirrored_wing_loft: TGeo.CNamedShape = self.wing.get_mirrored_loft()
        complete_wing: TGeo.CNamedShape = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Fuse(self.wing_shape, mirrored_wing_loft.shape()).Shape(), "Complete wing")
        self.md.display_fuse(complete_wing, self.wing_loft, mirrored_wing_loft)
        return complete_wing

    def _create_engine_cape(self, motor_cutout_length) -> TGeo.CNamedShape:
        '''
        Cut the fuselage tip, so the motor can be positioned there. Fuselage loft is updated and returns the Engine cape Shape
        :param motor_cutout_length: length of the motor
        '''
        cutout_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(self.fuselage_dimensions.get_point(1), motor_cutout_length,
                                      self.fuselage_dimensions.get_width(),
                                      self.fuselage_dimensions.get_height()).Shape(), "cape_cut_out")

        engine_cape = OAlgo.BRepAlgoAPI_Common(self.fuselage_loft.shape(), cutout_box.shape()).Shape()
        named_engine_cape = TGeo.CNamedShape(engine_cape, "engine_cape")

        cuted_fuselage = OAlgo.BRepAlgoAPI_Cut(self.fuselage_loft.shape(), cutout_box.shape()).Shape()
        named_cuted_fuselage = TGeo.CNamedShape(cuted_fuselage, "cuted_fuselage")
        self.md.display_this_shape(named_cuted_fuselage)
        # self.m.start()

        parts = [named_engine_cape, named_cuted_fuselage]
        self.md.display_slice_x(parts)

        self.fuselage_loft.set_shape(cuted_fuselage)
        return named_engine_cape

    def _calc_motor_dimensions(self):
        all_engines = self.cpacs_configuration.get_engines()

        engine_positions: TConfig.CCPACSEnginePositions = self.cpacs_configuration.get_engine_positions()
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

    def _calc_rib_positions(self, factor):
        y_max: float = (self.fuselage_dimensions.get_width() * factor) / 2
        y_min: float = -y_max

        overlap_dimension: PDim.ShapeDimensions = self.overlap_fuselage_wing_dimensions()
        position = None
        spacing = 0.003
        # Check if high wing or low wing
        if self._is_high_wing(overlap_dimension):
            z_max_below_overlap: float = overlap_dimension.get_z_min() - spacing
            z_max_calculated_with_factor: float = self.fuselage_dimensions.get_z_mid() + (
                    (self.fuselage_dimensions.get_height() * factor) / 2)

            # z_max can not collide with wing, and may not be smaller than the height of the fuselage * factor
            z_max: float = min(z_max_below_overlap, z_max_calculated_with_factor)
            z_min: float = self.fuselage_dimensions.get_z_mid() - ((self.fuselage_dimensions.get_height() * factor) / 2)
            self.position = "top"
        elif self._is_low_wing(overlap_dimension):
            z_min_over_overlap: float = overlap_dimension.get_z_max() + spacing
            z_min_calculated_with_factor: float = self.fuselage_dimensions.get_z_mid() - (
                    (self.fuselage_dimensions.get_height() * factor) / 2)

            # z_max can not collide with wing, and schould not be smaller than the height of the fuselage * factor
            z_min: float = max(z_min_over_overlap, z_min_calculated_with_factor)
            z_max = self.fuselage_dimensions.get_z_mid() + ((self.fuselage_dimensions.get_height() * factor) / 2)
            self.position = "bottom"
        else:
            z_max = self.fuselage_dimensions.get_z_mid() + ((self.fuselage_dimensions.get_height() * factor) / 2)
            z_min = self.fuselage_dimensions.get_z_mid() - ((self.fuselage_dimensions.get_height() * factor) / 2)
            logging.error(f"Ribs will collide")

        logging.info(f"Plane with {position} wing")
        return y_max, y_min, z_max, z_min

    def _create_recces_cutouts(self, y_max, y_min, z_max, z_min, factor):
        cutouts = []
        radius_factor = 0.8
        radius_with_z = ((z_max - z_min) / 2) * radius_factor
        radius_with_y = ((y_max - y_min) / 2) * radius_factor
        radius = min(radius_with_z, radius_with_y)

        distance: float = radius * 3
        quantity: int = round(self.fuselage_dimensions.get_length() / distance) + 1
        cylinder_height = self.fuselage_dimensions.get_height()

        cylinder_pattern: TGeo.CNamedShape = self.cutouts.create_cylinder_pattern(radius, cylinder_height, quantity,
                                                                                  distance)
        cylinder_pattern_ver: TGeo.CNamedShape = TGeo.CNamedShape(OExs.translate_shp(cylinder_pattern.shape(),
                                                                                     Ogp.gp_Vec(distance / 2, 0,
                                                                                                self.fuselage_dimensions.get_z_min())),
                                                                  f"{cylinder_pattern.name()}_vertikal")

        self.md.display_this_shape(cylinder_pattern_ver, cylinder_pattern_ver.name())
        cutouts.append(cylinder_pattern_ver)

        cylinder_pattern_hor: TGeo.CNamedShape = TGeo.CNamedShape(
            OExs.rotate_shape(cylinder_pattern.shape(), Ogp.gp_OX(), 90), f"{cylinder_pattern.name()}_horizontal")
        z_pos: float = (z_max + z_min) / 2
        cylinder_pattern_hor.set_shape(OExs.translate_shp(cylinder_pattern_hor.shape(), Ogp.gp_Vec(distance / 2,
                                                                                                   self.fuselage_dimensions.get_height() / 2,
                                                                                                   z_pos)))

        self.md.display_this_shape(cylinder_pattern_hor, cylinder_pattern_hor.name())
        cutouts.append(cylinder_pattern_hor)

        # Hardware Opening
        hardware_opening: TGeo.CNamedShape = self.cutouts.create_hardware_cutout(self.fuselage_dimensions,
                                                                                 self.wing_dimensions, factor,
                                                                                 self.position)

        return cutouts, hardware_opening

