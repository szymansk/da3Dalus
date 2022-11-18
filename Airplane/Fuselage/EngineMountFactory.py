import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
from Extra.patterns import *
from Extra.mydisplay import myDisplay


class EngineMountFactory:
    def __init__(self, tigl_handle):
        self.m = myDisplay.instance()
        config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(
            tigl_handle._handle.value)
        self.fuselage: TConfig.CCPACSFuselage = self.cpacs_configuration.get_fuselage(1)

        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        self.fuselage_dimensions = PDim.ShapeDimensions(self.fuselage_loft)
        self._calc_motor_dimensions()

    def create_engine_mount(self, plate_thickness):
        '''
        lenght = self.engine_length
        width = self.engine_width * 1.1
        height = width
        factor = 0.7
        mount_hole_dim= 0.01
        '''

        # Shaft Box
        schaft_box = self._create_schaft_box()

        engine_mount = [TGeo.CNamedShape]
        engine_mount.append(schaft_box)

        # plate
        back_plate = self._create_back_plate(plate_thickness)

        # Screwpoints / nuts
        nuts = self._create_nuts()

        # Fusing engine mount and nuts
        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(new_mount.shape(), nuts.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_fuse(engine_mount[-1], engine_mount[-2], nuts)

        # cutting engine area
        cutout_angle = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(self.outer_schaft_box_lenght, 2 * self.outer_schaft_box_width,
                                      2 * self.outer_schaft_box_height).Shape(), "cutout_agle")
        cutout_angle.set_shape(OExs.translate_shp(cutout_angle.shape(), Ogp.gp_Vec(-self.outer_schaft_box_lenght * 0.9,
                                                                                   -self.outer_schaft_box_width,
                                                                                   -self.outer_schaft_box_height)))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OY(), self.down_thrust_angle))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OZ(), self.right_thrust_angle))

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), cutout_angle.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_cut(engine_mount[-1], engine_mount[-2], cutout_angle)

        # positioning mount

        new_mount = engine_mount[-1]
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(self.engine_length, self.motor_position.get_y(),
                                                                    self.motor_position.get_z())))
        engine_mount.append(new_mount)

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), back_plate.shape()).Shape())
        engine_mount.append(new_mount)

        self.m.display_fuse(engine_mount[-1], engine_mount[-2], back_plate)
        return new_mount

    def _create_back_plate(self, plate_thickenss):
        '''
        Cuts a slice of the Fuselage to use as a backplate for the engine mount
        :return:
        '''
        panel_x_position = self.engine_length + self.outer_schaft_box_lenght
        box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(plate_thickenss, self.fuselage_dimensions.get_width(),
                                                         self.fuselage_dimensions.get_height()).Shape(), "boud_box")
        x_pos = panel_x_position
        box.set_shape(OExs.translate_shp(box.shape(), Ogp.gp_Vec(x_pos, self.fuselage_dimensions.get_ymin(),
                                                                 self.fuselage_dimensions.get_zmin())))
        panel = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, box.shape()).Shape(), "Panel")
        self.m.display_cut(panel, self.fuselage_loft, box)
        return panel

    def _front_point(self):
        # self.fuselage.set
        thickness = self.fuselage_dimensions.get_length() * 0.005
        box = [OPrim.BRepPrimAPI_MakeBox(thickness, self.fuselage_dimensions.get_width(),
                                         self.fuselage_dimensions.get_height()).Shape()]
        box.append(OExs.translate_shp(box[-1], Ogp.gp_Vec(0, self.fuselage_dimensions.get_ymin(),
                                                          self.fuselage_dimensions.get_zmin())))
        panel = OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, box[-1]).Shape()
        self.m.display_cut(panel, self.fuselage_shape, box[-1])
        return panel

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
        self.engine_schaft_lenght = self.engine_length * 0.3
        logging.info(
            f"engine size= length: {self.engine_length},width: {self.engine_width}, height: {self.engine_height},\t")

    def _create_schaft_box(self) -> TGeo.CNamedShape:
        '''
        Creates the main part of the enginemount. It consists of a Hollowed box with a through hole
        :return:
        '''
        self.outer_schaft_box_lenght = self.engine_schaft_lenght * 1.2
        self.outer_schaft_box_width = self.engine_width * 1.1
        self.outer_schaft_box_height = self.outer_schaft_box_width
        outer_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(self.outer_schaft_box_lenght, self.outer_schaft_box_width,
                                      self.outer_schaft_box_height).Shape(), "outer_box")
        outer_box.set_shape(OExs.translate_shp(outer_box.shape(), Ogp.gp_Vec(0, -self.outer_schaft_box_width / 2,
                                                                             -self.outer_schaft_box_height / 2)))

        factor = 0.7
        x_pos = (1 - factor) * self.outer_schaft_box_lenght
        inner_schaft_box_lenght = self.outer_schaft_box_lenght * factor
        inner_schaft_box_width = self.outer_schaft_box_width * factor
        inner_schaft_box_height = self.outer_schaft_box_height * factor

        inner_schaft_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(inner_schaft_box_lenght, inner_schaft_box_width, inner_schaft_box_height).Shape(),
            "inner_schaft_box")
        inner_schaft_box.set_shape(
            OExs.translate_shp(inner_schaft_box.shape(),
                               Ogp.gp_Vec(x_pos, -inner_schaft_box_width / 2, -inner_schaft_box_height / 2)))

        # Throughhole
        radius = inner_schaft_box_width / 2
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, self.outer_schaft_box_lenght).Shape(),
                                    "throughhole")
        cylinder.set_shape(OExs.rotate_shape(cylinder.shape(), Ogp.gp_OY(), 90))

        shapes_to_cut = [inner_schaft_box, cylinder]
        cuted_box = cut_list_of_shapes(outer_box, shapes_to_cut)
        cuted_box.set_name("engine_mount")
        return cuted_box

    def _create_nuts(self) -> TGeo.CNamedShape:
        '''

        :return:
        '''
        mount_hole_diameter = 0.01
        mount_hole_radius = mount_hole_diameter / 2
        cylinder_lenght = self.outer_schaft_box_lenght
        outer_cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(mount_hole_radius, cylinder_lenght).Shape(),
                                          "outer_cylider")
        outer_cylinder.set_shape(OExs.rotate_shape(outer_cylinder.shape(), Ogp.gp_OY(), 90))
        inner_cylinder = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeCylinder(mount_hole_radius * .5, cylinder_lenght).Shape(),
            "inner_cylinder")
        inner_cylinder.set_shape(OExs.rotate_shape(inner_cylinder.shape(), Ogp.gp_OY(), 90))

        nut = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(outer_cylinder.shape(), inner_cylinder.shape()).Shape(), "nut")
        nut.set_shape(OExs.translate_shp(nut.shape(), Ogp.gp_Vec(0, self.outer_schaft_box_width / 2, 0)))
        nuts = create_circular_pattern(nut, 4)
        self.m.display_this_shape(nuts)
        return nuts


'''
    def create_engine_mount(self, motor_lenght=0.04, shaft_lenght=0.02, mount_width=0.04,
                            mount_hole_dim=0.002, alpha_angle=-3, beta_angle=2):
   
        lenght = self.engine_length
        width = self.engine_width * 1.1
        height = width
        factor = 0.7
        mount_hole_dim= 0.01
  

        # Panel
        panel = self._create_back_plate(panel_x_position, panel_thickenss)
        panel_dimensions = PDim.ShapeDimensions(panel)

        # Shaft Box
        outer_box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape(), "outer_box")
        outer_box.set_shape(OExs.translate_shp(outer_box.shape(), Ogp.gp_Vec(0, -width / 2, -height / 2)))

        x_pos = (1 - factor) * lenght
        inner_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(lenght * factor, width * factor, height * factor).Shape(), "inner_box")
        inner_box.set_shape(
            OExs.translate_shp(inner_box.shape(), Ogp.gp_Vec(x_pos, -width / 2 * factor, -height / 2 * factor)))

        # Throughhole
        radius = width * factor / 2
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, lenght).Shape(), "throughhole")
        cylinder.set_shape(OExs.rotate_shape(cylinder.shape(), Ogp.gp_OY(), 90))

        shapes_to_cut = [inner_box, cylinder]
        cuted_box = cut_list_of_shapes(outer_box, shapes_to_cut)
        cuted_box.set_name("engine_mount")

        engine_mount = [TGeo.CNamedShape]
        engine_mount.append(cuted_box)
        self.m.display_this_shape(cuted_box)

        # Screwpoints / nuts
        radius = mount_hole_dim / 2
        cylinder_lenght = lenght * 0.4
        outer_cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, cylinder_lenght).Shape(),
                                          "outer_cylider")
        outer_cylinder.set_shape(OExs.rotate_shape(outer_cylinder.shape(), Ogp.gp_OY(), 90))
        inner_cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius * .5, cylinder_lenght).Shape(),
                                          "inner_cylinder")
        inner_cylinder.set_shape(OExs.rotate_shape(inner_cylinder.shape(), Ogp.gp_OY(), 90))

        horizontal_box = OPrim.BRepPrimAPI_MakeBox(lenght * factor, width * factor, height * factor).Shape()
        nut = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(outer_cylinder.shape(), inner_cylinder.shape()).Shape(), "nut")
        nut.set_shape(OExs.translate_shp(nut.shape(), Ogp.gp_Vec(0, width / 2, 0)))
        nuts = create_circular_pattern(nut, 4)
        self.m.display_this_shape(nuts)

        # Fusing engine mount and nuts
        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), nuts.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_fuse(engine_mount[-1], engine_mount[-2], nuts)

        cutout_angle = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(lenght, 2 * width, 2 * height).Shape(), "cutout_agle")
        cutout_angle.set_shape(OExs.translate_shp(cutout_angle.shape(), Ogp.gp_Vec(-lenght * 0.9, -width, -height)))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OY(), self.down_thrust_angle))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OZ(), self.side_angle))

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), cutout_angle.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_cut(engine_mount[-1], engine_mount[-2], cutout_angle)

        engine_mount_dimension = PDim.ShapeDimensions(engine_mount[-1])
        engine_x_pos = panel_dimensions.get_xmin() - engine_mount_dimension.get_length()
        engine_y_pos = 0
        engine_z_pos = panel_dimensions.get_zmid()

        new_mount = engine_mount[-1]
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(engine_x_pos, engine_y_pos, engine_z_pos)))
        engine_mount.append(new_mount)

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), panel.shape()).Shape())
        engine_mount.append(new_mount)
'''
