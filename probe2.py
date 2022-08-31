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
from Ausgabeservice import *
from Wand_erstellen import *
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape

from abmasse import get_dimensions, get_koordinates

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

i_cpacs=2
tixi_h = tixi3wrapper.Tixi3()

tigl_handle = tigl3wrapper.Tigl3()
if i_cpacs==1:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
if i_cpacs==2:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
if i_cpacs==3:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat.xml")
if i_cpacs==4:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_rumpf.xml") 
tigl_handle.open(tixi_h, "")

config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
#bnd_box: OBnd.Bnd_Box= fuselage.get_bounding_box()
#xmin, ymin, zmin, xmax,ymax,zmax=bnd_box.Get()

fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
xmin, ymin, zmin, xmax,ymax,zmax= get_koordinates(fuselage_shape)
mylenght, myheight, fuselage_widht= get_dimensions(xmin, ymin, zmin, xmax,ymax,zmax)



fuselage_hollow= create_hollowedsolid(fuselage_shape, 0.01)
display, start_display, add_menu, add_function_to_menu = init_display()
#myheight= 5
mywidth= 0.4
#mylenght= 50

box = OPrim.BRepPrimAPI_MakeBox(mylenght, mywidth, myheight).Shape()
moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-mywidth/2,-myheight/2))
cylinder= OPrim.BRepPrimAPI_MakeCylinder((myheight-1)/2,100).Shape()
cylinder= rotate_shape(cylinder, Ogp.gp_OY(), 90)
named_cylinder= TGeo.CNamedShape(cylinder, "CutOut")

rib_quantity=2
d_angle= 180/rib_quantity
for i in range(rib_quantity):     
    angle=i*d_angle
    print(i, angle) 
    sbox= rotate_shape(moved_box, Ogp.gp_OX(), angle)
    if i==0:
        rippen=sbox
    else:
        rippen=OAlgo.BRepAlgoAPI_Fuse(rippen,sbox).Shape()
              
#rippen= OAlgo.BRepAlgoAPI_Cut(rippen, cylinder).Shape()
    
display.DisplayShape(rippen, transparency=.8) 
display.DisplayShape(fuselage_hollow) 
#display.DisplayShape(box)
    

#display, start_display, add_menu, add_function_to_menu = init_display()
#display.DisplayShape(moved_box, transparency=.8)
#display.DisplayShape(sbox, transparency=.8)
display.FitAll()
start_display()