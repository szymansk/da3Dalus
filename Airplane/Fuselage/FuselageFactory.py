import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig
from OCC.Core.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Airplane.Fuselage.FuselageCutouts import FuselageCutouts
from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory
from Airplane.ReinforcementPipeFactory import ReinforcementePipeFactory
from Extra.BooleanOperationsForLists import *


# import logging
# import OCC.Core.TopoDS as OTopo
# from Extra.mydisplay import myDisplay


class FuselageFactory:
    def __init__(self, tigl_handle, index=1) -> None:
        self.md = myDisplay.instance()
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.fuselage: TConfig.CCPACSFuselage = self.cpacs_configuration.get_fuselage(index)
        logstr = f"Creating Fuselage Shape: {self.fuselage.get_name()}"
        logging.info(logstr)
        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        self.fuselage_dimensions = PDim.ShapeDimensions(self.fuselage_loft)
        self.fuselage_shape_offset = self._offset_fuselage()

        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(1)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: TopoDS_Shape = self.wing_loft.shape()
        self.wing_shape_complete: TGeo.CNamedShape = self._create_complete_wing_shape()
        self.wing_dimensions = PDim.ShapeDimensions(self.wing_loft)

        self.rib_factory = FuselageRibFactory(self.fuselage_loft, self.wing_loft)
        self.reinforcement_pipe_factory = ReinforcementePipeFactory(self.tigl_handle, 1)
        self.cutouts = FuselageCutouts()

        self.shape = None
        self.shapes = []

    def create_fuselage_option1(self, factor=0.5) -> TopoDS_Shape:
        """
        Creates the Fuselage, with sharp ribs, reinforcementpipes, weightreduktion recces,hardwareopening
        :param factor: smaller than 1, describes the size of the ribcage inside the fuselage
        :return:
        """

        motor_lenght = 0.04
        motor_schaft = 0.02
        motor_cutout_leght = motor_lenght + motor_schaft
        self._cut_front_fuselage_for_motor(motor_cutout_leght)

        internal_strukture: list[TGeo.CNamedShape] = []

        y_max: float = (self.fuselage_dimensions.get_width() * factor) / 2
        y_min: float = -y_max

        overlap_dimmension: PDim.ShapeDimensions = self._overlap_fuselage_wing_dimmensions()
        position = None
        # Check if high wing or low wing
        if self._is_high_wing():
            z_max_1: float = overlap_dimmension.get_zmin() - 0.003
            z_max_2: float = self.fuselage_dimensions.get_zmid() + (
                    (self.fuselage_dimensions.get_height() * factor) / 2)
            z_max: float = min(z_max_1, z_max_2)
            z_min: float = self.fuselage_dimensions.get_zmid() - ((self.fuselage_dimensions.get_height() * factor) / 2)
            position = "top"
        elif self._is_low_wing():
            z_min_1: float = overlap_dimmension.get_zmin() - 0.003
            z_min_2: float = self.fuselage_dimensions.get_zmid() + (
                    (self.fuselage_dimensions.get_height() * factor) / 2)
            z_max: float = max(z_min_1, z_min_2)
            z_max = self.fuselage_dimensions.get_zmid() + ((self.fuselage_dimensions.get_height() * factor) / 2)
            z_min = overlap_dimmension.get_zmax() + 0.003
            position = "bottom"
        else:
            z_max = self.fuselage_dimensions.get_zmid() + ((self.fuselage_dimensions.get_height() * factor) / 2)
            z_min = self.fuselage_dimensions.get_zmid() - ((self.fuselage_dimensions.get_height() * factor) / 2)
            logging.error(f"Ribs will colide")
        logging.info(f"Plane with {position} wing")
        # Ribs
        rib_width: float = 0.002
        ribs: TGeo.CNamedShape = self.rib_factory.create_sharp_ribs(rib_width, y_max, y_min, z_max, z_min)
        internal_strukture.append(ribs)

        # ReinforcementPipes
        radius: float = 0.002
        reinforcement_pipes: TGeo.CNamedShape = self.reinforcement_pipe_factory.create_reinforcement_pipe_option1_fuselage(
            radius, y_max,
            y_min, z_max,
            z_min)
        internal_strukture.append(reinforcement_pipes)
        fused_internal_strukture: TGeo.CNamedShape = fuse_list_of_namedshapes(internal_strukture)

        cutouts_list: list[TGeo.CNamedShape] = []
        # Vertikal reduktion recces
        radius1 = ((z_max - z_min) / 2) * 0.8
        radius2 = ((y_max - y_min) / 2) * 0.8
        radius = min(radius1, radius2)
        distance: float = radius * 3
        quantity: int = round(self.fuselage_dimensions.get_length() / distance) + 1
        cylinder_pattern: TGeo.CNamedShape = self.cutouts.create_cylinder_pattern(radius,
                                                                                  self.fuselage_dimensions.get_height(),
                                                                                  quantity,
                                                                                  distance)
        cylinder_pattern_ver: TGeo.CNamedShape = TGeo.CNamedShape(OExs.translate_shp(cylinder_pattern.shape(),
                                                                                     Ogp.gp_Vec(distance / 2, 0,
                                                                                                self.fuselage_dimensions.get_zmin())),
                                                                  f"{cylinder_pattern.name()}_vertikal")
        self.md.display_this_shape(cylinder_pattern_ver, cylinder_pattern_ver.name())
        cutouts_list.append(cylinder_pattern_ver)

        cylinder_pattern_hor: TGeo.CNamedShape = TGeo.CNamedShape(
            OExs.rotate_shape(cylinder_pattern.shape(), Ogp.gp_OX(), 90), f"{cylinder_pattern.name()}_horizontal")
        z_pos: float = (z_max + z_min) / 2
        cylinder_pattern_hor.set_shape(OExs.translate_shp(cylinder_pattern_hor.shape(),
                                                          Ogp.gp_Vec(distance / 2,
                                                                     self.fuselage_dimensions.get_height() / 2,
                                                                     z_pos)))
        self.md.display_this_shape(cylinder_pattern_hor, cylinder_pattern_hor.name())
        cutouts_list.append(cylinder_pattern_hor)

        # Hardware Oppening
        hardware_oppening: TGeo.CNamedShape = self.cutouts.create_hardware_cutout(self.fuselage_dimensions,
                                                                                  self.wing_dimensions, factor,
                                                                                  position)
        cutouts_list.append(hardware_oppening)

        # cuted Internal Strcture
        cuted_internal_strukture: list[TGeo.CNamedShape] = []
        cuted_internal_strukture.append(cut_list_of_shapes(fused_internal_strukture, cutouts_list))

        # Shape the internalt strukture
        cuted_internal_strukture.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(self.fuselage_loft.shape(), cuted_internal_strukture[-1].shape()).Shape(),
            "Shaped_internalestrukture"))
        self.md.display_common(cuted_internal_strukture[-1], self.fuselage_loft, cuted_internal_strukture[-2])

        # Inverse internal Strukture
        logging.info(f"Cuting internatl strukture form Fuselage")
        self.shapes.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape_offset.shape(), cuted_internal_strukture[-1].shape()).Shape(),
            f"{self.fuselage_loft.name()}"))
        self.md.display_cut(self.shapes[-1], self.fuselage_shape_offset, cuted_internal_strukture[-1])

        # Cutout WIngs from Fuselage
        logging.info(f"Cuting wings form Fuselage")
        self.shapes.append(TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Cut(self.shapes[-1].shape(), self.wing_shape_complete.shape()).Shape(),
            f"{self.fuselage_loft.name()}"))
        self.md.display_cut(self.shapes[-1], self.shapes[-1], self.wing_shape_complete)
        return self.shapes[-1]

    def get_shape(self) -> OTopo.TopoDS_Shape:
        return self.shapes[-1]

    def _offset_fuselage(self, offset=0.0005) -> TGeo.CNamedShape:
        """
        """
        result = TGeo.CNamedShape(OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, offset, 0.0001).Shape(),
                                  f"{self.fuselage_loft.name()}_offset")
        msg = f"Fuselage with {str(offset)=} meters"
        self.md.display_this_shape(result, msg)
        return result

    def _is_high_wing(self) -> bool:
        """
        :return: True if wing is on top
        """
        if self.wing_dimensions.get_zmax() > self.fuselage_dimensions.get_zmax():
            logging.info(f"High wing aircraft")
            return True
        else:
            return False

    def _is_low_wing(self) -> bool:
        """
        return: True if wing is on bottom
        """
        if self.wing_dimensions.get_zmin() < self.fuselage_dimensions.get_zmin():
            logging.info(f"Low wing aircraft")
            return True
        else:
            return False

    def _is_mid_wing(self, toleranz_factor=0.25) -> bool:
        """
        :param toleranz_factor:
        :return: True if the WIng is near the middle of the fuselage +- tolerance
        """
        toleranz = self.fuselage_dimensions.get_height() * toleranz_factor
        if self.wing_dimensions.get_zmid() <= self.fuselage_dimensions.get_zmid() + toleranz and \
                self.wing_dimensions.get_zmid() >= self.fuselage_dimensions.get_zmid() - toleranz:
            return True
        else:
            return False

    def _overlap_fuselage_wing_dimmensions(self) -> PDim.ShapeDimensions:
        """
        :return:
        """
        overlap = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, self.wing_shape_complete.shape()).Shape(), "Overlap")
        self.md.display_common(overlap, self.fuselage_loft, self.wing_shape_complete)
        result = PDim.ShapeDimensions(overlap)
        return result

    def _create_complete_wing_shape(self) -> TGeo.CNamedShape:
        # Set up the mirror
        atrsf = Ogp.gp_Trsf()
        atrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))
        # transformed_wing = OBuilder.BRepBuilderAPI_Transform(self.wing_shape, atrsf)
        # mirrored_wing = transformed_wing.Shape()
        mirrored_wing_loft: TGeo.CNamedShape = self.wing.get_mirrored_loft()
        complete_wing: TGeo.CNamedShape = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Fuse(self.wing_shape, mirrored_wing_loft.shape()).Shape(), "Complete wing")
        self.md.display_fuse(complete_wing, self.wing_loft, mirrored_wing_loft)
        return complete_wing

    def _cut_front_fuselage_for_motor(self, motor_cutout_leght):
        cutout_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(self.fuselage_dimensions.get_point(1), motor_cutout_leght,
                                      self.fuselage_dimensions.get_width(),
                                      self.fuselage_dimensions.get_height()).Shape(), "motor_cut_out")
        cuted_fuselage = OAlgo.BRepAlgoAPI_Cut(self.fuselage_loft.shape(), cutout_box.shape()).Shape()
        self.fuselage_loft.set_shape(cuted_fuselage)
        self.md.display_cut(self.fuselage_loft, self.fuselage_loft, cutout_box)
