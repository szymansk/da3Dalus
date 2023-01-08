import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Wing.WingFactory as wf
import Extra.ConstructionStepsViewer as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

import logging
from Airplane.Configuration import Configuration
CPACS_FILE_NAME = "aircombat_v13"

if __name__ == "__main__":
    logging.debug(f"Start test for Wing Factory with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.ConstructionStepsViewer.instance(True, 1.5, True)
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
    m.display_in_origin(fuselage_loft, logging.NOTSET, "", True)

    test_class = wf.WingFactory(wing, fuselage)
    my_wing = test_class.create_wing_with_inbuilt_servo(rib_cage_shape, self._wing_information[self.wing_index],
                                                        "wing_offset")

    logging.debug("Test finished. Display results")
    m.start()
