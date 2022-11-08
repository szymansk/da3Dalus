from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.boolean_ops as TBo
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories


import OCC.Core.BRep as OBrep
import OCC.Core.Bnd as OBnd
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import Extra.mydisplay as md
import Extra.tigl_extractor as tg
import Extra.ShapeSlicer as ss
import OCC.Extend.ShapeFactory as OExs
from stl_exporter.Ausgabeservice import *
import _alt.Wand_erstellen as we

import Dimensions.ShapeDimensions as PDim
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape

from _alt.abmasse import get_dimensions, get_koordinates

if __name__ == "__main__":
    tigl_handle = tg.get_tigl_handler("aircombat_v12")
    m = md.myDisplay.instance(True, 1)
    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)

    wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    wing_dimensions = PDim.ShapeDimensions(wing_shape)

    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = PDim.ShapeDimensions(fuselage_shape, fuselage_loft.name())

    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = PDim.ShapeDimensions(fuselage_shape, fuselage_loft.name())

    box = OPrim.BRepPrimAPI_MakeBox(fuselage_dimensions.get_point(1), fuselage_dimensions.get_length() * 0.05,
                                    fuselage_dimensions.get_width(), fuselage_dimensions.get_height()).Shape()
    named_box: TGeo.CNamedShape = TGeo.CNamedShape(box, "cutout_box")

    named_cuted_fuselage: TGeo.CNamedShape = TBo.CCutShape(fuselage_loft, named_box).named_shape()

    cuted_shape = named_cuted_fuselage.shape()

    wand = we.Wandstaerke()
    holow_shape = wand.create_hollowedsolid(cuted_shape, 0.0004)

    my_slicer = ss.ShapeSlicer(wing_shape, 3, "Wing")
    my_slicer.slice_by_cut()

    ##fuselage_done=OAlgo.BRepAlgoAPI_Fuse(fuselage_hollow,rippen_cuted).Shape()
    # box= OPrim.BRepPrimAPI_MakeBox(10, 100, 100).Shape()
    # moved_box= OExs.translate_shp(box,Ogp.gp_Vec(31, -30, -50))
    # fuselage_cuted=  OAlgo.BRepAlgoAPI_Cut(fuselage_shape, moved_box).Shape()
    # fuselage_shape= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,complete_wing).Shape()
    # fuselage_hollowed=create_hollowedsolid(fuselage_shape,0.004)
    # fuselage_hollowed=create_hollow(fuselage_shape, 0.004)

    # fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(fuselage_shape,0.0004,0.0001).Shape()

    # merge= OAlgo.BRepAlgoAPI_Fuse(fuselage_hollowed,mybox).Shape()
    # cut= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,fuselage_hollowed).Shape()

    # m.display_this_shape(fuselage_shape, fuselage_loft.name() )
    # m.display_this_shape(cuted_shape)
    # m.display_this_shape(holow_shape,"this is face?")
    # m.display_in_origin(fuselage_shape)
    # m.display_in_origin(box,"box")

    m.start()
