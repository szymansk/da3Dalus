import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.ReinforcementPipeFactory as rpf
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

import logging
from Airplane.Configuration import Configuration

CPACS_FILE_NAME = "aircombat_v13"
if __name__ == "__main__":
    logging.info(f"Start test for Reinforcement Pipe Factory with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.myDisplay.instance(True, 1.5)
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

    m.display_in_origin(wing_loft, "", True)

    logging.info("Create Reinforcement Pipe Factory")
    test_class = rpf.ReinforcementePipeFactory(wing, fuselage)

    radius = 0.003
    thickness = 0.0004
    quantity = 5

    pipe_position = [0, 1]
    pipe = test_class.create_reinforcemente_pipe_wing(radius, thickness, quantity, pipe_position)
    m.display_in_origin(pipe)

    logging.info("Test finished. Display results")
    m.start()
