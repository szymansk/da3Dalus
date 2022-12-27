import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
import OCC.Core.BRepPrimAPI as OPrim

import Airplane.AirplaneFactory as ap
import Airplane.ReinforcementPipeFactory as rpf
import Airplane.Wing.CablePipeFactory as cp
import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.ServoRecessFactory as srf
import Airplane.Wing.WingFactory as wf
import Airplane.Wing.WingRibFactory as wrf
import Airplane.Fuselage.FuselageFactory as ff
import Airplane.Fuselage.EngineMountFactory as em
import Extra.ConstructionStepsViewer as myDisplay
import Extra.tigl_extractor as tg
import Extra.ShapeSlicer as ss
import Extra.ShellCreator as cs
import Extra.CollisionDetector as cd
import stl_exporter.Exporter as exp
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.ConstructionStepsViewer.instance(True, 1)
    tigl_h = tg.get_tigl_handler("aircombat_v13")
    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_h._handle.value)
    fuselage: TConfig.CCPACSWing = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)

    wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    wing_dimensions = ShapeDimensions(wing_loft)

    m.display_in_origin(wing_shape, logging.NOTSET)
    m.display_in_origin(fuselage_shape, logging.NOTSET)

    test_class_name = ""
    if test_class_name == "":
        pass
    if test_class_name == "WingFactory":
        test_class = wf.WingFactory(tigl_h, 1)
        my_wing = test_class.create_wing_with_inbuilt_servo()
        my_slicer = ss.ShapeSlicer(my_wing, 5, "Wing_v2_")
        my_slicer.slice_by_cut()
        # my_exporter = exp.exporter()
        # my_exporter.write_step_from_list(my_slicer.parts_list, "Wing_v2_")
        # my_exporter.write_stls_from_list(my_slicer.parts_list, "Wing_v2_")
    if test_class_name == "WingRibFactory":
        test_class = wrf.WingRibFactory(tigl_h, 1)
        test_class.create_ribcage()
    if test_class_name == "RuderFactory":
        test_class = rf.RuderFactory(tigl_h, 1)
        test_class.get_trailing_edge_cutout()
    if test_class_name == "Ruder":
        config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_h._handle.value)
        wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)
        wing_loft: TGeo.CNamedShape = wing.get_loft()
        wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()

        compseg: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(1)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(1)
        loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
        shape = loft.shape()

        m.display_in_origin(shape, logging.NOTSET)
        m.display_in_origin(wing_shape, logging.NOTSET, "", True)
    if test_class_name == "ReinforcementPipeFactory":
        test_class = rpf.ReinforcementePipeFactory(tigl_h, 1)
        radius = 0.003
        thickness = 0.0004
        quantity = 5
        pipe_position = [0, 1]
        pipe = test_class.create_reinforcemente_pipe_wing(radius, thickness, quantity, pipe_position)
        m.display_in_origin(pipe, logging.NOTSET)
        m.display_in_origin(test_class.wing_shape, logging.NOTSET, "", True)
    if test_class_name == "ServoRecessFactory":
        # servo_size=(0.0023,0.0024,0.0012)
        servo_size = (0.024, 0.024, 0.012)
        ruder_factory = rf.RuderFactory(tigl_h, 1)
        ruder = ruder_factory.get_trailing_edge_cutout(offset=0.002)
        test_class = srf.ServoRecessFactory(tigl_h, 1)
        test_class.create_servoRecess_option1(ruder, servo_size=servo_size)
        m.display_in_origin(test_class.wing_shape, logging.NOTSET, "", True)
        m.display_in_origin(ruder, logging.NOTSET)
    if test_class_name == "CablePipeFactory":
        ruder_factory = rf.RuderFactory(tigl_h, 1)
        ruder = ruder_factory.get_create_trailing_edge_shape()
        r_d = ShapeDimensions(ruder)
        m.display_in_origin(ruder, logging.NOTSET, "", True)
        servo_size = (0.15, 0.15, 0.05)
        ruder_factory = rf.RuderFactory(tigl_h, 1)
        servo_factory = srf.ServoRecessFactory(tigl_h, 1)
        servo_factory.create_servoRecess_option1(ruder, servo_size=servo_size)
        servo = servo_factory.get_shape()
        servo_dimension = ShapeDimensions(servo, "servo")
        servo_points = servo_dimension.get_points()
        '''
        for p in servo_points:
            m.display_point_in_origin(p)
        wing_dim=servo_factory.wing_dimensions
        '''
        config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_h._handle.value)
        fuselage: TConfig.CCPACSWing = cpacs_configuration.get_fuselage(1)
        fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
        fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
        fuselage_dimensions = ShapeDimensions(fuselage_shape, "fuselage")
        fuselage_mid_point: Ogp.gp_Pnt = fuselage_dimensions.get_point(0)

        points = []
        # Point0
        p: Ogp.gp_Pnt = servo_dimension.get_point(0)
        point0: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X(), p.Y(), p.Z())
        points.append(point0)

        # point1
        p1: Ogp.gp_Pnt = servo_dimension.get_point(1)
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(p1.X() - 0.04, p1.Y() - 0.05, p1.Z())
        points.append(point1)

        # point2
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X() - 0.05, fuselage_dimensions.get_y_max() / 2, p.Z())
        points.append(point2)

        # point3
        point3: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_mid_point.X(), fuselage_mid_point.Y(), fuselage_mid_point.Z())
        points.append(point3)

        test_class = cp.CabelPipeFactory(tigl_h, 1, points, 0.001)
        test_class.create_complete_pipe()
    if test_class_name == "RightWing":
        test_class = ap.AirplaneFactory(tigl_h)
        test_class.create_right_main_wing(1, "right_wing")
    if test_class_name == "FuselageFactory":
        test_class = ff.FuselageFactory(tigl_h, 1)
        test_class.create_fuselage_option1()
    if test_class_name == "AirplaneFactory":
        test_class = ap.AirplaneFactory(tigl_h, True)
        test_class.create_airplane()
    if test_class_name == "EngineMount":
        test_class = em.EngineMountFactory()
        motor_lenght = 0.043
        shaft_lenght = 0.03
        mount_width = 0.035
        mount_hole_dim = 0.004
        alpha_angle = 5
        beta_angle = 5
        test_class.create_engine_mount(motor_lenght, 0.034, self.engine_total_cover_length,
                                       self.engine_mount_box_length, self.engine_down_thrust_deg,
                                       self.engine_side_thrust_deg, self.engine_screw_din_diameter,
                                       self.engine_srew_length, self.fuselage_index, 1, cpacs_configuration)
    if test_class_name == "ShellCreator":
        wing_f = wf.WingFactory(tigl_h, 1)
        test_class = cs.ShellCreator(wing_f.wing_shape)
        my_shape = test_class.create_shell(0.001, "Y", "min")
        m.display_in_origin(my_shape, logging.NOTSET)
    if test_class_name == "CollisionCreator":
        collision_detector = cd.CollisionDetector()
        if collision_detector.check_colission(fuselage_shape, wing_shape, "Fuselage", "Wing", True):
            print("test1:erfolgreich")
        else:
            print("test1:fehlgeschlagen")

        moved_wing = OExs.translate_shp(wing_shape, Ogp.gp_Vec(0, 0, 0.5))
        if collision_detector.check_colission(fuselage_shape, moved_wing, "Fuselage", "Moved_Wing", False):
            print("test2:erfolgreich")
        else:
            print("test2:fehlgeschlagen")
    if test_class_name == "CollisionCreator2":
        collision_detector = cd.CollisionDetector()
        moved_wing: OTopo.TopoDS_Shape = OExs.translate_shp(wing_shape, Ogp.gp_Vec(0, 0, 0.2))
        named_moved_wing: TGeo.CNamedShape = TGeo.CNamedShape(moved_wing, "moved_wing")
        box = OPrim.BRepPrimAPI_MakeBox(wing_dimensions.get_point(0), wing_dimensions.get_length() / 2,
                                        wing_dimensions.get_width() / 2, 0.3).Shape()
        named_box: TGeo.CNamedShape = TGeo.CNamedShape(box, "box")

        fuselage_testcases = [(wing_loft, False), (named_moved_wing, True), (named_box, False)]
        wing_testcases = [(named_moved_wing, False), (named_box, True)]
        moved_wing_testcases = [(named_box, True)]
        test_cases = {fuselage_loft: fuselage_testcases, wing_loft: wing_testcases,
                      named_moved_wing: moved_wing_testcases}

        collision_detector.multiple_collision_check(test_cases)

    # shape = test_class.get_shape()
    # m.display_in_origin(shape)
    m.start()
