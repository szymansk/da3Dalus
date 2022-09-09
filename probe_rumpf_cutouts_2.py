from re import M
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
from mydisplay import myDisplay

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


m=myDisplay.instance()
i_cpacs=2
tixi_h = tixi3wrapper.Tixi3()

tigl_handle = tigl3wrapper.Tigl3()
if i_cpacs==1:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
if i_cpacs==2:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
if i_cpacs==3:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38.xml")
if i_cpacs==4:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinywing_skaliert.xml") 
 
tigl_handle.open(tixi_h, "")



config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)

###
#Creates Wing
###
wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
wing_loft: TGeo.CNamedShape = wing.get_loft()
wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
m.display_this_shape(wing_shape)
# Set up the mirror
aTrsf= Ogp.gp_Trsf()
aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
transformed_wing = OBuilder.BRepBuilderAPI_Transform(wing_shape, aTrsf)
mirrored_wing= transformed_wing.Shape()
complete_wing= OAlgo.BRepAlgoAPI_Fuse(wing_shape,mirrored_wing).Shape()
m.display_this_shape(complete_wing)
#Named Shape for Cutout
named_wings_shape: TGeo.CNamedShape= TGeo.CNamedShape(complete_wing, "CutOut_Wings")
print("complete:" ,type(complete_wing))
#Hollow Wing
facesToRemove = TopTools_ListOfShape()
hollow_complete_wing= OOff.BRepOffsetAPI_MakeThickSolid(wing_shape, facesToRemove, 0.02, 0.001)

###
#Creates Fuselage
###
fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
xmin, ymin, zmin, xmax,ymax,zmax= get_koordinates(fuselage_shape)
fuselage_lenght, fuselage_height, fuselage_widht= get_dimensions(xmin, ymin, zmin, xmax,ymax,zmax)
print(fuselage_lenght, fuselage_height, fuselage_widht)
m.display_this_shape(fuselage_shape)

# Fuselage cutout wing       
#cutter= TBoo.CCutShape(fuselage_loft, named_wings_shape)
#cutted_fuselage_shape:TGeo.CNamedShape= cutter.named_shape()
cutted_fuselage_shape= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,complete_wing).Shape()
m.display_this_shape(cutted_fuselage_shape)

facesToRemove = TopTools_ListOfShape()
# Fuselage Hollow, walls for wings 
fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(cutted_fuselage_shape, facesToRemove, 0.2, 0.001).Shape()
m.display_this_shape(fuselage_hollow, True)

###
#Creates Ribs
###
rib_width= 0.2
mybox = OPrim.BRepPrimAPI_MakeBox(1, 1, 1).Shape()
box = OPrim.BRepPrimAPI_MakeBox(fuselage_lenght, rib_width, fuselage_height).Shape()
moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-rib_width/2,-fuselage_height/2))

#Cut Out for Hardware
hardware_box_height=fuselage_height*0.4+rib_width
hardware_box_lenght= fuselage_lenght*0.4
hardware_box_widht= fuselage_widht*0.8
hardware_box= OPrim.BRepPrimAPI_MakeBox(hardware_box_lenght, hardware_box_widht, hardware_box_height).Shape()
moved_hardware_box= OExs.translate_shp(hardware_box,Ogp.gp_Vec(0,-hardware_box_widht/2, -hardware_box_height+ rib_width))
m.display_this_shape(moved_hardware_box)

#Cutout for Extra Ribs
cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*0.8)/2,40).Shape()
cylinder= rotate_shape(cylinder, Ogp.gp_OY(), 90)
m.display_this_shape(cylinder)

###
#Create tunnel for carbon reinforcement
###
reinforcement_tunnel_in= OPrim.BRepPrimAPI_MakeCylinder(0.2,40).Shape()
reinforcement_tunnel_in= rotate_shape(reinforcement_tunnel_in, Ogp.gp_OY(), 90)
reinforcement_tunnel_out= OPrim.BRepPrimAPI_MakeCylinder(0.3,40).Shape()
reinforcement_tunnel_out= rotate_shape(reinforcement_tunnel_out, Ogp.gp_OY(), 90)
#reinforcement_tunnel=OAlgo.BRepAlgoAPI_Cut(reinforcement_tunnel_out,reinforcement_tunnel_in).Shape()
#named_reinforcement_tunnel: TGeo.CNamedShape= TGeo.CNamedShape(complete_wing, "CutOut_Reinforcement")
m.display_this_shape(reinforcement_tunnel_out)

rib_quantity=2
# Extraribs
d_angle=180/(rib_quantity*2)
for i in range(rib_quantity*2):
    angle=i*d_angle
    print(i, angle) 
    sbox= rotate_shape(moved_box, Ogp.gp_OX(), angle)
    if i==0:
        rippen_ver=sbox
    else:
        rippen_ver=OAlgo.BRepAlgoAPI_Fuse(rippen_ver,sbox).Shape()
m.display_this_shape(rippen_ver)
        

# Fuselage CutOut reinfurceennt tunnel
#cutter= TBoo.CCutShape(cutted_fuselage_shape, named_reinforcement_tunnel)
        
rippen_ver= OAlgo.BRepAlgoAPI_Cut(rippen_ver, cylinder).Shape()
m.display_this_shape(rippen_ver)

rippen_ver= OAlgo.BRepAlgoAPI_Common(cutted_fuselage_shape, rippen_ver).Shape()
m.display_this_shape(rippen_ver)

# Cross ribs
d_angle= 180/rib_quantity
for i in range(rib_quantity):     
    angle=i*d_angle
    print(i, angle) 
    sbox= rotate_shape(moved_box, Ogp.gp_OX(), angle)
    if i==0:
        rippen=sbox
    else:
        rippen=OAlgo.BRepAlgoAPI_Fuse(rippen,sbox).Shape()
m.display_this_shape(rippen)

rippen_cuted=  OAlgo.BRepAlgoAPI_Cut(rippen, moved_hardware_box).Shape()
m.display_this_shape(rippen_cuted)

rippen_cuted= OAlgo.BRepAlgoAPI_Fuse(rippen_cuted,reinforcement_tunnel_out).Shape()
m.display_this_shape(rippen_cuted)

#rippen_cuted= OAlgo.BRepAlgoAPI_Cut(rippen_cuted, reinforcement_tunnel_in).Shape()
rippen_cuted=OAlgo.BRepAlgoAPI_Common(cutted_fuselage_shape, rippen_cuted).Shape()
m.display_this_shape(rippen_cuted)

rippen_gesamt=OAlgo.BRepAlgoAPI_Fuse(rippen_cuted, rippen_ver).Shape()
m.display_this_shape(rippen_gesamt)

point:Ogp.gp_Pnt =TGeo.get_center_of_mass(rippen_cuted)
print(point.X(), point.Y(), point.Z())
center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 1).Shape()
#center_mass_box= OExs.translate_shp(mybox,Ogp.gp_Vec(point.XYZ()))
print("Starting las Fuse: Wait...")
#fuselage_done=OAlgo.BRepAlgoAPI_Fuse(fuselage_hollow,rippen_cuted).Shape()
#fuselage_done= OAlgo.BRepAlgoAPI_Cut(fuselage_done, reinforcement_tunnel_in).Shape()
try:
    write_stl_file2(fuselage_done, "Fuselage_Done.stl")
except:
    print("No export")
'''
display, start_display, add_menu, add_function_to_menu = init_display()
#display.DisplayShape(reinforcement_tunnel_out) 
display.DisplayShape(center_of_mass, color="BLUE") 
display.DisplayShape(rippen_ver) 
display.DisplayShape(rippen_cuted) 
#display.DisplayShape(mybox) 
display.DisplayShape(fuselage_hollow, transparency=.8) 
#display.DisplayShape(cutted_fuselage_shape, transparency=.8)
#display.DisplayShape(fuselage_done, transparency=0.8)

#display, start_display, add_menu, add_function_to_menu = init_display()
#display.DisplayShape(moved_box, transparency=.8)
#display.DisplayShape(sbox, transparency=.8)
display.FitAll()
start_display()
'''
m.start()