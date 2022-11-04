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
import OCC.Extend.ShapeFactory as OExs
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape


# from Extra.mydisplay import myDisplay

def rotate_shape(shape, axis, angle):
    """Rotate a shape around an axis, with a given angle.
    @param shape : the shape to rotate
    @point : the origin of the axis
    @vector : the axis direction
    @angle : the value of the rotation
    @return: the rotated shape.
    """
    # assert_shape_not_null(shape)
    # if unite == "deg":  # convert angle to radians
    angle = radians(angle)
    trns = Ogp.gp_Trsf()
    trns.SetRotation(axis, angle)
    brep_trns = OBui.BRepBuilderAPI_Transform(shape, trns, False)
    brep_trns.Build()
    shp = brep_trns.Shape()

    return shp


display, start_display, add_menu, add_function_to_menu = init_display()
# m=myDisplay.instance(True)

'''
point=OPrim.BRepPrimAPI_MakeSphere(1).Shape()
left = OPrim.BRepPrimAPI_MakeBox(10, 10, 10).Shape()
display.DisplayShape(point)
display.DisplayShape(left,transparency=0.8)
left= OExs.rotate_shape(left,Ogp.gp_OX(),90)
display.DisplayShape(left)
start_display()
'''

'''
left= OExs.translate_shp(left,Ogp.gp_Vec(-5,-50, -5))
#left= create_hollowedsolid(left,0.4)
right: OTopo.TopoDS_Solid = OPrim.BRepPrimAPI_MakeBox(30, 30, 30).Shape()
right= OExs.translate_shp(right,Ogp.gp_Vec(-25,75, -5))
#right= create_hollowedsolid(right,1)
complement: OTopo.TopoDS_Shape= right.Complemented()
complement= OExs.translate_shp(complement,Ogp.gp_Vec(-25,50, -5))
print(type(right))
'''
print("1")
point = OPrim.BRepPrimAPI_MakeSphere(3).Shape()
print("2")
cylinder = OPrim.BRepPrimAPI_MakeCylinder(2, 50).Shape()
print("3")
display.DisplayShape(cylinder, transparency=0.8)
print("4")
# cylinder= OExs.translate_shp(cylinder,Ogp.gp_Vec(0,0, -50))
cylinder = OExs.rotate_shape(cylinder, Ogp.gp_OX(), 90)
print("5")
display.DisplayShape(cylinder)
print("6")
display.DisplayShape(point)
print("7")

display.FitAll()
start_display()

'''
complete=OAlgo.BRepAlgoAPI_Fuse(left,cylinder).Shape()
m.display_fuse(complete, left, cylinder) 
complete2=OAlgo.BRepAlgoAPI_Fuse(complete,right).Shape()
m.display_fuse(complete2, complete, right) 

point:Ogp.gp_Pnt =TGeo.get_center_of_mass(complete)
print(point.X(), point.Y(), point.Z())
center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 3).Shape()
'''

# display, start_display, add_menu, add_function_to_menu = init_display()
# display.DisplayShape(center_of_mass, color="BLUE")
# display.DisplayShape(complete)
# display.DisplayShape(complement)
# display.DisplayShape(right)
# display.DisplayShape(cylinder)


# display.FitAll()
# start_display()

# write_stl_file2(complete, "Box_test.stl")
