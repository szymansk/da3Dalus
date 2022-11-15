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
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
import Extra.ShapeSlicer as ss
import Extra.ShellCreator as cs
import Extra.CollisionDetector as cd
import stl_exporter.Ausgabeservice as exp
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 1.5)
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

    m.display_in_origin(wing_loft, "", True)
    m.display_in_origin(fuselage_loft, "", True)

    ruder_factory = rf.RuderFactory(tigl_h, 1)
    ruder = ruder_factory.get_trailing_edge_shape()
    r_d = ShapeDimensions(ruder)
    m.display_in_origin(ruder, "", True)
    servo_size = (0.024, 0.024, 0.012)
    ruder_factory = rf.RuderFactory(tigl_h, 1)
    servo_factory = srf.ServoRecessFactory(tigl_h, 1)
    servo_recces = servo_factory.create_servoRecess_option1(ruder, servo_size=servo_size)
    servo_dimension = ShapeDimensions(servo_recces)
    servo_points = servo_dimension.get_points()

    fuselage_mid_point: Ogp.gp_Pnt = fuselage_dimensions.get_point(0)

    test_class = cp.CablePipeFactory(tigl_h, 1)
    points = test_class.points_route_thru(servo_dimension, fuselage_dimensions)
    pipe = test_class.create_complete_pipe(points, 0.005)
    m.display_in_origin(pipe)
    m.display_in_origin(servo_recces)
    m.start()
