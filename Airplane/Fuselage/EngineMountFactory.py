import logging

import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
from Extra.patterns import *
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class EngineMountFactory:

    @classmethod
    def create_engine_mount(cls, mount_plate_thickness: float, engine_screw_hole_circle: float,
                            engine_total_cover_length, engine_mount_box_length, engine_down_thrust_deg,
                            engine_side_thrust_deg, engine_screw_din_diameter, engine_screw_length, fuselage_index,
                            engine_index, cpacs_configuration):
        '''
        lenght = cls.engine_length
        width = cls.engine_width * 1.1
        height = width
        factor = 0.7
        mount_hole_dim= 0.01
        :param engine_mount_box_length: 
        :param engine_down_thrust_deg: 
        :param engine_side_thrust_deg: 
        :param engine_screw_din_diameter: 
        :param engine_screw_length: 
        :param fuselage_index: 
        :param engine_total_cover_length: 
        :param engine_index: 
        :param cpacs_configuration:
        :param engine_screw_hole_circle:
        '''

        _engine_down_thrust_deg, _engine_side_thrust_deg, motor_position, _engine_total_cover_length, engine_width, engine_height \
            = EngineMountFactory._calc_motor_dimensions(cpacs_configuration, engine_index=engine_index)
        engine_down_thrust_deg = _engine_down_thrust_deg if engine_down_thrust_deg is None else engine_down_thrust_deg
        engine_side_thrust_deg = _engine_side_thrust_deg if engine_side_thrust_deg is None else engine_side_thrust_deg
        engine_total_cover_length = _engine_total_cover_length if engine_total_cover_length is None else engine_total_cover_length

        # Shaft Box
        schaft_box, cylinder = cls._create_schaft_box(screw_hole_circle=engine_screw_hole_circle,
                                                                      engine_mount_box_length=engine_mount_box_length)

        engine_mount = [TGeo.CNamedShape, schaft_box]

        # plate
        back_plate = cls._create_back_plate(mount_plate_thickness, engine_mount_box_length, engine_total_cover_length,
                                             fuselage_index, cpacs_configuration)
        # cut hole in backplate
        cylinder.set_shape(OExs.translate_shp(cylinder.shape(), Ogp.gp_Vec(engine_total_cover_length, 0, 0)))
        back_plate.set_shape(OAlgo.BRepAlgoAPI_Cut(back_plate.shape(), cylinder.shape()).Shape())
        ConstructionStepsViewer.instance().display_fuse(back_plate, back_plate, cylinder, logging.DEBUG)


        # Screwpoints / nuts
        nuts, inner_cylinders = \
            cls._create_nuts(engine_mount_box_length, engine_screw_hole_circle, engine_screw_din_diameter)

        # translate nuts along x
        nuts.set_shape(OExs.translate_shp(nuts.shape(), Ogp.gp_Vec(engine_total_cover_length,
                                                                   motor_position.get_y(),
                                                                   motor_position.get_z())))
        inner_cylinders.set_shape(OExs.translate_shp(inner_cylinders.shape(), Ogp.gp_Vec(engine_total_cover_length,
                                                                                         motor_position.get_y(),
                                                                                         motor_position.get_z())))
        # rotate nuts by down and side thrust
        nuts.set_shape(OExs.rotate_shape(nuts.shape(), Ogp.gp_OY(), engine_down_thrust_deg))
        nuts.set_shape(OExs.rotate_shape(nuts.shape(), Ogp.gp_OZ(), engine_side_thrust_deg))

        inner_cylinders.set_shape(OExs.rotate_shape(inner_cylinders.shape(), Ogp.gp_OY(), engine_down_thrust_deg))
        inner_cylinders.set_shape(OExs.rotate_shape(inner_cylinders.shape(), Ogp.gp_OZ(), engine_side_thrust_deg))

        # cutting engine area
        cutout_angle = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(engine_mount_box_length*2, 2.2 * engine_screw_hole_circle,
                                      2.2 * engine_screw_hole_circle).Shape(), "cutout_angle")
        cutout_angle.set_shape(OExs.translate_shp(cutout_angle.shape(), Ogp.gp_Vec(-engine_mount_box_length*2,
                                                                                   -engine_screw_hole_circle,
                                                                                   -engine_screw_hole_circle)))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OY(), engine_down_thrust_deg))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OZ(), engine_side_thrust_deg))

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), cutout_angle.shape()).Shape())
        engine_mount.append(new_mount)
        ConstructionStepsViewer.instance().display_cut(engine_mount[-1], engine_mount[-2], cutout_angle, logging.NOTSET)

        # positioning mount

        new_mount = engine_mount[-1]
        # translate along x
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(engine_total_cover_length, motor_position.get_y(),
                                                                    motor_position.get_z())))
        engine_mount.append(new_mount)

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), back_plate.shape()).Shape())
        engine_mount.append(new_mount)
        ConstructionStepsViewer.instance().display_fuse(engine_mount[-1], engine_mount[-2], back_plate, logging.NOTSET)

        # Fusing engine mount and nuts
        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(new_mount.shape(), nuts.shape()).Shape())
        engine_mount.append(new_mount)
        ConstructionStepsViewer.instance().display_fuse(engine_mount[-1], engine_mount[-2], nuts, logging.NOTSET)

        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), inner_cylinders.shape()).Shape())

        return new_mount

    @staticmethod
    def _create_back_plate(plate_thickness, outer_schaft_box_length, engine_total_cover_length, fuselage_index,
                           cpacs_configuration):
        '''
        Cuts a slice of the Fuselage to use as a backplate for the engine mount
        :param engine_total_cover_length:
        :param fuselage_index:
        :param cpacs_configuration: 
        :param outer_schaft_box_length: 
        :return:
        
        '''
        panel_x_position = engine_total_cover_length + outer_schaft_box_length
        box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(plate_thickness, 
                                                         PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_width(),
                                                         PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_height())
                               .Shape(), "boud_box")
        x_pos = panel_x_position
        box.set_shape(OExs.translate_shp(box.shape(), Ogp.gp_Vec(x_pos, PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_y_min(),
                                                                 PDim.ShapeDimensions(cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_z_min())))
        panel = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(cpacs_configuration.get_fuselage(fuselage_index).get_loft().shape(), box.shape()).Shape(), "Panel")
        ConstructionStepsViewer.instance().display_cut(panel, cpacs_configuration.get_fuselage(fuselage_index).get_loft(), box, logging.NOTSET)
        return panel

    @staticmethod
    def _front_point(fuselage_index, cpacs_configuration):
        thickness = PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_length() * 0.005
        box = [OPrim.BRepPrimAPI_MakeBox(thickness, PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_width(),
                                         PDim.ShapeDimensions(cpacs_configuration.get_fuselage(
                                             fuselage_index).fuselage.get_loft()).get_height()).Shape()]
        box.append(OExs.translate_shp(box[-1], Ogp.gp_Vec(0, PDim.ShapeDimensions(
            cpacs_configuration.get_fuselage(fuselage_index).get_loft()).get_y_min(),
                                                          PDim.ShapeDimensions(cpacs_configuration.get_fuselage(
                                                              fuselage_index).fuselage.get_loft()).get_z_min())))
        panel = OAlgo.BRepAlgoAPI_Common(cpacs_configuration.get_fuselage(fuselage_index).get_loft().shape(),
                                         box[-1]).Shape()
        ConstructionStepsViewer.instance().display_cut(panel, cpacs_configuration.get_fuselage(
            fuselage_index).get_loft().shape(), box[-1], logging.NOTSET)
        return panel

    @classmethod
    def _calc_motor_dimensions(cls, cpacs_configuration, engine_index):
        all_engines = cpacs_configuration.get_engines()

        engine_positions: TConfig.CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: TConfig.CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: TGeo.CCPACSTransformation = engine_position.get_transformation()

        rotation: TGeo.CTiglPoint = engine_position_transformation.get_rotation()
        down_thrust_angle = rotation.y
        right_thrust_angle = rotation.z
        logging.debug(f"{down_thrust_angle=},\t {right_thrust_angle=}")

        motor_position: TGeo.CCPACSPointAbsRel = engine_position_transformation.get_translation()
        logging.debug(
            f"engine position= ({motor_position.get_x()},\t {motor_position.get_y()},\t {motor_position.get_z()})")

        engine_scaling: TGeo.CTiglPoint = engine_position_transformation.get_scaling()
        engine_length = engine_scaling.x
        engine_width = engine_scaling.y
        engine_height = engine_scaling.z
        logging.debug(
            f"engine size= length: {engine_length},width: {engine_width}, height: {engine_height},\t")
        return down_thrust_angle, right_thrust_angle, motor_position, engine_length, engine_width, engine_height

    @staticmethod
    def _create_schaft_box(screw_hole_circle: float, engine_mount_box_length: float) \
            -> Tuple[TGeo.CNamedShape, TGeo.CNamedShape]:
        """
        Creates the main part of the engine mount. It consists of a Hollowed box with a through hole
        :param engine_mount_box_length: 
        :param screw_hole_circle:
        :return:
        """
        outer_schaft_box_width = screw_hole_circle
        outer_schaft_box_height = outer_schaft_box_width
        outer_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(engine_mount_box_length*2, outer_schaft_box_width,
                                      outer_schaft_box_height).Shape(), "outer_box")
        outer_box.set_shape(OExs.translate_shp(outer_box.shape(), Ogp.gp_Vec(-engine_mount_box_length, -outer_schaft_box_width / 2,
                                                                             -outer_schaft_box_height / 2)))

        factor = 0.7
        x_pos = (1 - factor) * engine_mount_box_length
        inner_schaft_box_lenght = engine_mount_box_length * factor
        inner_schaft_box_width = outer_schaft_box_width * factor
        inner_schaft_box_height = outer_schaft_box_height * factor

        inner_schaft_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(inner_schaft_box_lenght, inner_schaft_box_width, inner_schaft_box_height).Shape(),
            "inner_schaft_box")
        inner_schaft_box.set_shape(
            OExs.translate_shp(inner_schaft_box.shape(),
                               Ogp.gp_Vec(x_pos, -inner_schaft_box_width / 2, -inner_schaft_box_height / 2)))

        # Throughhole
        radius = inner_schaft_box_width / 2
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, engine_mount_box_length*3).Shape(),
                                    "throughhole")
        cylinder.set_shape(OExs.rotate_shape(cylinder.shape(), Ogp.gp_OY(), 90))
        cylinder.set_shape(OExs.translate_shp(cylinder.shape(), Ogp.gp_Vec(-engine_mount_box_length, 0, 0)))

        shapes_to_cut = [inner_schaft_box, cylinder]
        cuted_box = BooleanCADOperation.cut_list_of_shapes(outer_box, shapes_to_cut)
        cuted_box.set_name("engine_mount")
        return cuted_box, cylinder

    @staticmethod
    def _create_nuts(outer_schaft_box_length, engine_screw_hole_circle, engine_screw_din_diameter) \
            -> Tuple[TGeo.CNamedShape, TGeo.CNamedShape]:
        """

        :param engine_screw_din_diameter:
        :param engine_screw_hole_circle:
        :param outer_schaft_box_length: 
        :return:
        """
        mount_hole_diameter = engine_screw_din_diameter + 0.006
        mount_hole_radius = mount_hole_diameter / 2
        cylinder_lenght = outer_schaft_box_length
        outer_cylinder = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeCylinder(mount_hole_radius, cylinder_lenght).Shape(), "outer_cylider")
        outer_cylinder.set_shape(OExs.rotate_shape(outer_cylinder.shape(), Ogp.gp_OY(), 90))

        # from OCC.Core.gp import gp_Ax1, gp_Pnt, gp_Dir
        # feature_origin = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0))
        # from OCC.Core.BRepFeat import BRepFeat_MakeCylindricalHole
        #
        # feature_maker = BRepFeat_MakeCylindricalHole()
        # feature_maker.Init(outer_cylinder.shape(), feature_origin)
        # feature_maker.Build()
        # feature_maker.Perform(mount_hole_radius)
        # outer_cylinder = feature_maker.Shape()

        inner_cylinder = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeCylinder(engine_screw_din_diameter/2, cylinder_lenght*2).Shape(),
            "inner_cylinder")
        inner_cylinder.set_shape(OExs.rotate_shape(inner_cylinder.shape(), Ogp.gp_OY(), 90))

        nut = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(outer_cylinder.shape(), inner_cylinder.shape()).Shape(), "nut")
        nut.set_shape(OExs.translate_shp(nut.shape(), Ogp.gp_Vec(0, engine_screw_hole_circle / 2, 0)))
        nuts = create_circular_pattern_around_xaxis(nut, 4)
        ConstructionStepsViewer.instance().display_this_shape(nuts, severity=logging.NOTSET)

        inner_cylinder.set_shape(OExs.translate_shp(inner_cylinder.shape(), Ogp.gp_Vec(-cylinder_lenght, engine_screw_hole_circle / 2, 0)))
        inner_cylinders = create_circular_pattern_around_xaxis(inner_cylinder, 4)
        return nuts, inner_cylinders
