import logging

import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Fuselage.FuselageFactory as ff
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
import Extra.ShapeSlicer as ss
from Dimensions.ShapeDimensions import ShapeDimensions
from Airplane.Configuration import Configuration

CPACS_FILE_NAME = "aircombat_v14"
NUMBER_OF_CUTS = 5

if __name__ == "__main__":
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.myDisplay.instance(True, 5)
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
    m.display_in_origin(fuselage_loft, "", True)

    test_class = ff.FuselageFactory(wing, fuselage)
    constructed_fuselage = test_class.create_fuselage_with_sharp_ribs()
    my_slicer = ss.ShapeSlicer(constructed_fuselage, NUMBER_OF_CUTS)

    logging.info("Test finished. Display results")

    m.start()
