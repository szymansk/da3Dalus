import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig

import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from _alt.Wand_erstellen import *
from stl_exporter.Exporter import *

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 0.5)
    tigl_handle = tg.get_tigl_handler("aircombat_v12")

    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)
    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()

    wing: TConfig.CCPACSFuselage = cpacs_configuration.get_wing(1)
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    m.display_in_origin(wing_shape, "", True)

    wing_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(fuselage_shape, 0.0004, 0.0001).Shape()

    m.display_in_origin(wing_offset)

    m.start()
