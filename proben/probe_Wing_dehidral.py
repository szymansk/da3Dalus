import logging

import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 1.5)
    # try:
    tigl_h = tg.get_tigl_handler("aircombat_v14")
    tixi_h = tg.get_tixi_handler("aircombat_v14")
    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_h._handle.value)
    fuselage: TConfig.CCPACSWing = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)
    m.display_in_origin(fuselage_loft, "", True)

    for i in range(1, cpacs_configuration.get_wing_count() + 1):

        wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(i)
        wing_loft: TGeo.CNamedShape = wing.get_loft()
        wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
        wing_dimensions = ShapeDimensions(wing_loft)
        m.display_in_origin(wing_loft, "", True)
        try:
            mirroered_loft = wing.get_mirrored_loft()
            m.display_in_origin(mirroered_loft, "", True)
        except:
            logging.warning(f"No mirrored {wing_loft.name()}")

    wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)
    wing_cutout = TGeo.CNamedShape(wing.get_loft_with_cutouts(), "cutout")

    section1: TConfig.CCPACSWingSection = wing.get_section(1)
    transformation: TGeo.CTiglTransformation = section1.get_section_transformation()

    for i in range(0, 3):
        for j in range(0, 3):
            try:
                print(transformation.get_value(i, j))
            except:
                print(f"No value in {i=} {j=}")

    m.start()
