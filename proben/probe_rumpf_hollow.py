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

import OCC.Core.BRep as OBrep
import OCC.Core.Bnd as OBnd
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Extend.ShapeFactory as OExs
from stl_exporter.Ausgabeservice import *
from _alt.Wand_erstellen import *
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape

from _alt.abmasse import get_dimensions, get_koordinates

def rotate_shape(shape, axis, angle):
    """Rotate a shape around an axis, with a given angle.
    @param shape : the shape to rotate
    @point : the origin of the axis
    @vector : the axis direction
    @angle : the value of the rotation
    @return: the rotated shape.
    """
    #assert_shape_not_null(shape)
    #if unite == "deg":  # convert angle to radians
    angle = radians(angle)
    trns = Ogp.gp_Trsf()
    trns.SetRotation(axis, angle)
    brep_trns = OBui.BRepBuilderAPI_Transform(shape, trns, False)
    brep_trns.Build()
    shp = brep_trns.Shape()

    return shp

def create_hollow(shape, offset=0.0004):
    fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(shape, -offset,0.0001).Shape()
    m.display_this_shape(fuselage_offset)
    hollowed= OAlgo.BRepAlgoAPI_Cut(shape,fuselage_offset).Shape()
    return hollowed
    
    

i_cpacs=3
tixi_h = tixi3wrapper.Tixi3()


tigl_handle = tigl3wrapper.Tigl3()
if i_cpacs==1:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
if i_cpacs==2:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
if i_cpacs==3:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
if i_cpacs==4:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_rumpf.xml") 
tigl_handle.open(tixi_h, "")
m=myDisplay.instance()
config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)

#wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1) 
#wing_loft: TGeo.CNamedShape = wing.get_loft()
#wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
#m.display_this_shape(wing_shape, "Right wing Shape")
# Set up the mirror
#aTrsf= Ogp.gp_Trsf()
#aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
#transformed_wing = OBuilder.BRepBuilderAPI_Transform(wing_shape, aTrsf)
#mirrored_wing= transformed_wing.Shape()
#complete_wing= OAlgo.BRepAlgoAPI_Fuse(wing_shape,mirrored_wing).Shape()
#m.display_this_shape(complete_wing)


fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
x1,y1, z1, x2,y2,z2= get_koordinates(fuselage_shape)
x,y,z=get_dimensions(x1,y1,z1,x2,y2,z2)
print(f"{x}, {y}, {z}")


##fuselage_done=OAlgo.BRepAlgoAPI_Fuse(fuselage_hollow,rippen_cuted).Shape()
#box= OPrim.BRepPrimAPI_MakeBox(10, 100, 100).Shape()
#moved_box= OExs.translate_shp(box,Ogp.gp_Vec(31, -30, -50))
#fuselage_cuted=  OAlgo.BRepAlgoAPI_Cut(fuselage_shape, moved_box).Shape()
#fuselage_shape= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,complete_wing).Shape()
#fuselage_hollowed=create_hollowedsolid(fuselage_shape,0.004)
#fuselage_hollowed=create_hollow(fuselage_shape, 0.004)
fuselage_offset= OOff.BRepOffsetAPI_MakeOffsetShape(fuselage_shape,0.0004,0.0001).Shape()


mybox = OPrim.BRepPrimAPI_MakeBox(x, y*0.2, z).Shape()
mybox=translate_shp(mybox,gp_Vec(0,-y*0.2/2,-z/2))

#merge= OAlgo.BRepAlgoAPI_Fuse(fuselage_hollowed,mybox).Shape()
#cut= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,fuselage_hollowed).Shape()


m.display_this_shape(fuselage_offset,"Offset", True)
m.display_in_origin(fuselage_offset, True)
m.display_this_shape(fuselage_shape, "Shape")
m.display_in_origin(fuselage_shape)
#m.display_this_shape(cut, "cut", True)
#write_stl_file2(fuselage_hollowed, "test_hollowe_shape.stl")
m.start()
