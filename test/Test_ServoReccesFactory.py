import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.ServoRecessFactory as srf
import Extra.ConstructionStepsViewer as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

import logging
from Airplane.Configuration import Configuration

CPACS_FILE_NAME = "aircombat_v13"

if __name__ == "__main__":
    logging.debug(f"Start test for Servo Recces Factory with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.ConstructionStepsViewer.instance(True, 1.5)
    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    configuration = Configuration(tigl_h)

    fuselage: TConfig.CCPACSWing = configuration.get_fuselage()
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)

    wing: TConfig.CCPACSWing = configuration.get_right_main_wing()
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    wing_dimensions = ShapeDimensions(wing_loft)

    m.display_in_origin(wing_loft, logging.NOTSET, "", True)
    servo_size = (0.024, 0.024, 0.012)
    ruder_factory = rf.RuderFactory(wing)
    ruder = ruder_factory.get_trailing_edge_cutout(offset=0.002)
    test_class = srf.ServoRecessFactory(wing)
    servo = test_class.create_servoRecess_option1(ruder, servo_size=servo_size)
    m.display_in_origin(servo, logging.NOTSET)

    logging.debug("Test finished. Display results")
    m.start()
