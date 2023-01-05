import tigl3.boolean_ops as TBo
import OCC.Core.BRepPrimAPI as OPrim
import tigl3.boolean_ops as TBo
import tigl3.configuration as TConfig

import Dimensions.ShapeDimensions as PDim
import Extra.ShapeSlicer as ss
import Extra.ConstructionStepsViewer as md
import Extra.tigl_extractor as tg
import _alt.Wand_erstellen as we
from stl_exporter.Exporter import *

if __name__ == "__main__":
    tigl_handle = tg.get_tigl_handler("aircombat_v12")
    m = md.ConstructionStepsViewer.instance(True, 1)
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

    my_slicer = ss.ShapeSlicer(wing_shape, self.loglevel, 3)
    my_slicer.slice_by_cut(self.loglevel)

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
