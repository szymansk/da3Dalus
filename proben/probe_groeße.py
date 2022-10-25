from __future__ import print_function
from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Extend.ShapeFactory as OExs
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo



from _alt.Wand_erstellen import *
import logging
from _alt.abmasse import get_dimensions_from_Shape, get_koordinates

from Extra.mydisplay import myDisplay

i_cpacs=4
	
tixi_h = tixi3wrapper.Tixi3()
tigl_handle = tigl3wrapper.Tigl3()
#cpacs_path="C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\""
if i_cpacs==1:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
if i_cpacs==2:
    tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
if i_cpacs==3:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat.xml")
if i_cpacs==4:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml") 
if i_cpacs==5:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml") 
tigl_handle.open(tixi_h, "")



m= myDisplay.instance(True)
config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)

wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
wing_loft: TGeo.CNamedShape = wing.get_loft()
wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
#Set up the mirror
wing1: TConfig.CCPACSWing= cpacs_configuration.get_wing(3)   
wing_loft1: TGeo.CNamedShape = wing1.get_loft()
wing_shape1: OTopo.TopoDS_Shape = wing_loft1.shape()

fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()


facesToRemove = TopTools_ListOfShape()
#fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(fuselage_shape, facesToRemove, 0.2, 0.001).Shape()
#fuselage_hollow=create_hollowedsolid(fuselage_shape,0.2)

xmin, ymin, zmin, xmax, ymax, zmax= get_koordinates(wing_shape)
length, width, height= get_dimensions_from_Shape(wing_shape)
box_length, box_width, box_height= length/2, 0.0004, 2*height
print(f"{box_length=:.3f}")
box = OPrim.BRepPrimAPI_MakeBox(box_length, box_width, box_height).Shape()
moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-box_width/2,-box_height/2))
rot_box= OExs.rotate_shape(moved_box, Ogp.gp_OY(), 60)
moved_box= OExs.translate_shp(rot_box,Ogp.gp_Vec(xmin-0.002,0,zmax-0.01 ))
f_length, f_width, f_height= get_dimensions_from_Shape(fuselage_shape)
rib_width= f_width * 0.6
distance= rib_width/5

rib= OExs.translate_shp(moved_box,Ogp.gp_Vec(0,-distance*2,0))
for i in range(0,5):
    movedrib= OExs.translate_shp(rib,Ogp.gp_Vec(0,distance*i,0))
    if i==0:
        ribs=movedrib
    else:
        ribs2= OAlgo.BRepAlgoAPI_Fuse(ribs,movedrib).Shape()
        #m.display_fuse(ribs2, ribs, movedrib)
        ribs=ribs2
box = OPrim.BRepPrimAPI_MakeBox(f_length, f_width, f_height).Shape()
moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-f_width/2, zmax ))
print(f"{zmax=}")
#moved_box= OExs.translate_shp(moved_box,Ogp.gp_Vec(0,0,0)) 
ribs_cut= OAlgo.BRepAlgoAPI_Cut(ribs,moved_box).Shape()
m.display_cut(ribs_cut,ribs, moved_box)


m.display_in_origin(wing_shape)
#m.display_in_origin(wing_shape1)
m.display_in_origin(ribs)
m.display_in_origin(fuselage_shape, True)
m.display.FitAll()
m.start()