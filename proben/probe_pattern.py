import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs

from Extra.mydisplay import myDisplay
from _alt.shape_verschieben import rotate_shape


def create_linear_pattern(shape, quantity, distance):
    pattern=shape
    list=[]
    for i in range(1,quantity):
        x= i*distance
        moved_shape= OExs.translate_shp(shape,Ogp.gp_Vec(x,0.0,0.0))
        newpattern= OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
        list.append(moved_shape)
        #m.display_fuse(newpattern, pattern, moved_shape)
        pattern=newpattern
        
    
    print(-1)
    test= list[-1]
    return list

def fuse_list_of_shapes(list, msg=""):
    fused=[]
    shape=None
    for shape in list:
        if not fused:
            fused.append(shape)
        else:
            fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1],shape).Shape())
            m.display_fuse(fused[-1],fused[-2], shape,msg)
    return fused[-1]






#testCylinder=OPrim.BRepPrimAPI_MakeCylinder(radius,self.fuselage_widht).Shape()
#self.m.display_this_shape(testCylinder)
m=myDisplay.instance(True)

cylinder= OPrim.BRepPrimAPI_MakeCylinder(1,5).Shape()
cylinder2= rotate_shape(cylinder, Ogp.gp_OX(), 90)
cylinder_pattern= create_linear_pattern(cylinder2, 5, 5)
fused= fuse_list_of_shapes(cylinder_pattern)

#m.display_in_origin(test)
#m.display_this_shape(cylinder_pattern)
m.display.FitAll()
m.start()
        
    


