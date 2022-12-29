import logging

import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
from Airplane.aircraft_topology.EngineInformation import EngineInformation
from Extra.patterns import *
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class EngineMountFactory:

    @classmethod
    def create_engine_mount(cls, engine_total_cover_length, engine_mount_box_length, engine_down_thrust_deg,
                            engine_side_thrust_deg, engine_screw_hole_circle: float, engine_screw_din_diameter,
                            engine_screw_length, engine_index, cpacs_configuration):
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
        :param engine_total_cover_length:
        :param engine_index: 
        :param cpacs_configuration:
        :param engine_screw_hole_circle:
        '''

        engine_information = EngineInformation(engine_index=engine_index, cpacs_configuration=cpacs_configuration)

        # Shaft Box
        schaft_box, cylinder = cls._create_schaft_box(screw_hole_circle=engine_screw_hole_circle,
                                                      engine_mount_box_length=engine_mount_box_length)

        engine_mount = [TGeo.CNamedShape, schaft_box]

        # Screwpoints / nuts
        nuts, inner_cylinders = \
            cls._create_nuts(engine_mount_box_length, engine_screw_hole_circle, engine_screw_din_diameter)

        # translate nuts along x
        nuts.set_shape(OExs.translate_shp(nuts.shape(), Ogp.gp_Vec(engine_total_cover_length,
                                                                   0,
                                                                   0)))
        inner_cylinders.set_shape(OExs.translate_shp(inner_cylinders.shape(), Ogp.gp_Vec(engine_total_cover_length,
                                                                                         0,
                                                                                         0)))
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
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(schaft_box.shape(), cutout_angle.shape()).Shape())
        engine_mount.append(new_mount)
        ConstructionStepsViewer.instance().display_cut(engine_mount[-1], schaft_box, cutout_angle, logging.NOTSET)

        # positioning mount

        new_mount = engine_mount[-1]
        # translate along x
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(engine_total_cover_length, 0, 0)))
        engine_mount.append(new_mount)

        # Fusing engine mount and nuts
        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(new_mount.shape(), nuts.shape()).Shape())
        engine_mount.append(new_mount)
        ConstructionStepsViewer.instance().display_fuse(engine_mount[-1], engine_mount[-2], nuts, logging.NOTSET)

        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), inner_cylinders.shape()).Shape())
        # translating mount to the correct position
        motor_position = engine_information.position
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(motor_position.get_x(),
                                                                    motor_position.get_y(),
                                                                    motor_position.get_z())))
        # ###
        # # plate
        # back_plate = cls.create_back_plate(mount_plate_thickness=mount_plate_thickness,
        #                                    engine_mount_box_length=engine_mount_box_length,
        #                                    engine_total_cover_length=engine_total_cover_length,
        #                                    engine_screw_hole_circle=engine_screw_hole_circle,
        #                                    engine_position=motor_position,
        #                                    fuselage_index=fuselage_index,
        #                                    cpacs_configuration=cpacs_configuration)
        #
        #
        # # verbinden mit der Backplate
        # new_mount = engine_mount[-1]
        # new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), back_plate.shape()).Shape())
        # engine_mount.append(new_mount)
        # ConstructionStepsViewer.instance().display_fuse(engine_mount[-1], engine_mount[-2], back_plate, logging.NOTSET)

        return new_mount

    @classmethod
    def create_back_plate(cls, mount_plate_thickness, engine_mount_box_length, engine_total_cover_length,
                          engine_screw_hole_circle, engine_position, fuselage_index, cpacs_configuration):
        '''
        Cuts a slice of the Fuselage to use as a backplate for the engine mount
        :param engine_screw_hole_circle:
        :param engine_position:
        :param engine_total_cover_length:
        :param fuselage_index:
        :param cpacs_configuration: 
        :param engine_mount_box_length:
        :return:
        
        '''

        loft = cpacs_configuration.get_fuselage(fuselage_index).get_loft()
        dimensions = PDim.ShapeDimensions(loft)
        box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(mount_plate_thickness,
                                                         dimensions.get_width(),
                                                         dimensions.get_height())
                               .Shape(), "boud_box")
        panel_x_position = engine_total_cover_length + engine_mount_box_length + engine_position.get_x()
        box.set_shape(OExs.translate_shp(box.shape(), Ogp.gp_Vec(panel_x_position, dimensions.get_y_min(),
                                                                 dimensions.get_z_min())))
        engine_mount_plate = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(loft.shape(), box.shape()).Shape(), "Panel")
        ConstructionStepsViewer.instance().display_cut(engine_mount_plate, loft, box, logging.NOTSET)

        # cut hole in backplate
        radius = engine_screw_hole_circle * 0.7 / 2
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, engine_mount_box_length*3).Shape(),
                                    "throughhole")
        cylinder.set_shape(OExs.rotate_shape(cylinder.shape(), Ogp.gp_OY(), 90))
        cylinder.set_shape(OExs.translate_shp(cylinder.shape(), Ogp.gp_Vec(-engine_mount_box_length, 0, 0)))

        cylinder.set_shape(OExs.translate_shp(cylinder.shape(), Ogp.gp_Vec(engine_total_cover_length, 0, 0)))
        cylinder.set_shape(
            OExs.translate_shp(cylinder.shape(), Ogp.gp_Vec(engine_position.get_x(),
                                                              engine_position.get_y(),
                                                              engine_position.get_z())))
        engine_mount_plate.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount_plate.shape(), cylinder.shape()).Shape())
        ConstructionStepsViewer.instance().display_fuse(engine_mount_plate, engine_mount_plate, cylinder, logging.DEBUG)

        return engine_mount_plate


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
