import logging

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO)
# logger.setLevel(logging.INFO)

import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.Fuselage.FuselageFactory as ff
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
import Extra.ShapeSlicer as ss
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 5)
    tigl_h = tg.get_tigl_handler("aircombat_v14")
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

    test_class = ff.FuselageFactory(tigl_h, 1)
    f = test_class.create_fuselage_with_sharp_ribs()
    my_slicer = ss.ShapeSlicer(f, 5)

    # my_slicer.slice_by_cut()

    # parts_list2= test_class.fuselage_parts+my_slicer.parts_list
    # m.display_slice_x(parts_list2)

    # my_exporter = exp.exporter()
    # my_exporter.write_stls_from_list(parts_list2, "fuselage")

    m.start()
