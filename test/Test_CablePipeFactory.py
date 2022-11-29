import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Wing.CablePipeFactory as cp
import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.ServoRecessFactory as srf
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions
from Airplane.Configuration import Configuration

import logging

CPACS_FILE_NAME = "aircombat_v13"

if __name__ == "__main__":

    logging.info("Start test for Cable Pipe Factory")

    m = myDisplay.myDisplay.instance(True, 1.5)
    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    configuration = Configuration(tigl_h)

    logging.info(f"Created configuration for CPCAS file {CPACS_FILE_NAME}")

    # setting fuselage
    fuselage: TConfig.CCPACSWing = configuration.get_fuselage()
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)

    # setting wing
    wing: TConfig.CCPACSWing = configuration.get_right_main_wing()
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    wing_dimensions = ShapeDimensions(wing_loft)

    m.display_in_origin(wing_loft, "", True)
    m.display_in_origin(fuselage_loft, "", True)

    # testing creation of ruder
    ruder_factory = rf.RuderFactory(wing)
    ruder = ruder_factory.get_trailing_edge_shape()
    r_d = ShapeDimensions(ruder)
    m.display_in_origin(ruder, "", True)

    # testing creation of servo
    servo_size = (0.024, 0.024, 0.012)
    ruder_factory = rf.RuderFactory(wing)
    servo_factory = srf.ServoRecessFactory(wing)
    servo_recces = servo_factory.create_servoRecess_option1(ruder, servo_size=servo_size)
    servo_dimension = ShapeDimensions(servo_recces)
    servo_points = servo_dimension.get_points()

    fuselage_mid_point: Ogp.gp_Pnt = fuselage_dimensions.get_point(0)

    test_class = cp.CablePipeFactory(wing)
    points = test_class.points_route_through(servo_dimension, fuselage_dimensions)
    pipe = test_class.create_complete_pipe(points, 0.005)

    logging.info("Test finished. Display results")
    m.display_in_origin(pipe)
    m.display_in_origin(servo_recces)
    m.start()
