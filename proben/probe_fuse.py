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
import OCC.Core.BRepOffsetAPI as OOff
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
from Extra.mydisplay import myDisplay

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

m=myDisplay.instance(True)
left = OPrim.BRepPrimAPI_MakeBox(10, 10, 10).Shape()
left= OExs.translate_shp(left,Ogp.gp_Vec(-5,-50, -5))
left= create_hollowedsolid(left,0.4)
right: TopoDS_Solid = OPrim.BRepPrimAPI_MakeBox(30, 30, 30).Shape()
right= OExs.translate_shp(right,Ogp.gp_Vec(-25,75, -5))
right= create_hollowedsolid(right,1)
complement: OTopo.TopoDS_Shape= right.Complemented()
complement= OExs.translate_shp(complement,Ogp.gp_Vec(-25,50, -5))
print(type(right))
cylinder= OPrim.BRepPrimAPI_MakeCylinder(2, 100).Shape()
#cylinder= OExs.translate_shp(cylinder,Ogp.gp_Vec(0,0, -50))
#cylinder= rotate_shape(cylinder, Ogp.gp_OX(), 90)

complete=OAlgo.BRepAlgoAPI_Fuse(left,cylinder).Shape()
m.display_fuse(complete, left, cylinder) 
complete2=OAlgo.BRepAlgoAPI_Fuse(complete,right).Shape()
m.display_fuse(complete2, complete, right) 

point:Ogp.gp_Pnt =TGeo.get_center_of_mass(complete)
print(point.X(), point.Y(), point.Z())
center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 3).Shape()

m.start()

#display, start_display, add_menu, add_function_to_menu = init_display()
#display.DisplayShape(center_of_mass, color="BLUE")
#display.DisplayShape(complete) 
#display.DisplayShape(complement) 
#display.DisplayShape(right) 
#display.DisplayShape(cylinder) 


#display.FitAll()
#start_display()

#write_stl_file2(complete, "Box_test.stl")
