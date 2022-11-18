from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import Extra.BooleanOperationsForLists as bof
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape
import Extra.tigl_extractor as tg

from Extra.mydisplay import myDisplay


def _create_complete_wing_shape(self) -> TGeo.CNamedShape:
    '''
    creates the comple meinewing outer shpae, by mirroring the right wing and fusing them together
    :return: complet wing shape
    '''
    # Set up the mirror
    atrsf = Ogp.gp_Trsf()
    atrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))

    mirrored_wing_loft: TGeo.CNamedShape = self.wing.get_mirrored_loft()
    complete_wing: TGeo.CNamedShape = TGeo.CNamedShape(
        OAlgo.BRepAlgoAPI_Fuse(self.wing_shape, mirrored_wing_loft.shape()).Shape(), "Complete wing")
    self.m.display_fuse(complete_wing, self.wing_loft, mirrored_wing_loft)
    return complete_wing


if __name__ == "__main__":
    m = myDisplay.instance(True, 0.25)

    tigl_handle = tg.get_tigl_handler("aircombat_v14")

    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)
    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()

    wing: TConfig.CCPACSFuselage = cpacs_configuration.get_wing(1)
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()

    mirrored_wing_loft: TGeo.CNamedShape = wing.get_mirrored_loft()
    complete_wing: TGeo.CNamedShape = TGeo.CNamedShape(
        OAlgo.BRepAlgoAPI_Fuse(wing_shape, mirrored_wing_loft.shape()).Shape(), "Complete wing")
    # m.display_fuse(complete_wing, wing_loft, mirrored_wing_loft)

    cut = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(fuselage_shape, complete_wing.shape()).Shape(), "cut")
    m.display_cut(cut, fuselage_loft, complete_wing)

    m.start()

    m.start()
