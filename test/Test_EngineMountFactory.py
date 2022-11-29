import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Fuselage.EngineMountFactory as em
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

import logging

from Airplane.Configuration import Configuration

CPACS_FILE_NAME = "aircombat_v14"
PLATE_THICKNESS = 0.005

if __name__ == "__main__":
    logging.info(f"Start test for Engine Mount Factory with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.myDisplay.instance(True, 0.5)
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

    m.display_in_secondfloor(wing_loft, "", True)
    m.display_in_secondfloor(fuselage_loft, "", True)

    test_class = em.EngineMountFactory(tigl_h)
    my_engine_mount = test_class.create_engine_mount(PLATE_THICKNESS)

    m.display_in_secondfloor(my_engine_mount)
    logging.info("Test finished. Display results")

    m.start()
