import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs

import Extra.BooleanOperationsForLists as bof
from Extra.ConstructionStepsViewer import ConstructionStepsViewer

if __name__ == "__main__":
    m = ConstructionStepsViewer.instance(True, 12)

    point = OPrim.BRepPrimAPI_MakeSphere(2).Shape()
    point2 = point
    point2 = OExs.translate_shp(point2, Ogp.gp_Vec(0, 2, 3))
    left = OPrim.BRepPrimAPI_MakeBox(10, 10, 10).Shape()

    list_tu_cut = [point, point2]
    m.display_in_origin(point)
    m.display_in_origin(point2)
    m.display_in_origin(left, True)

    # cuted= OAlgo.BRepAlgoAPI_Cut(left,point).Shape()
    cuted = bof.cut_list_of_shapes(left, list_tu_cut)
    m.display_this_shape(cuted)
    m.display_cut(cuted, left, point)
    m.start()

'''
left= OExs.translate_shp(left,Ogp.gp_Vec(-5,-50, -5))
#left= create_hollowedsolid(left,0.4)
right: OTopo.TopoDS_Solid = OPrim.BRepPrimAPI_MakeBox(30, 30, 30).Shape()
right= OExs.translate_shp(right,Ogp.gp_Vec(-25,75, -5))
#right= create_hollowedsolid(right,1)
complement: OTopo.TopoDS_Shape= right.Complemented()
complement= OExs.translate_shp(complement,Ogp.gp_Vec(-25,50, -5))
print(type(right))

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
