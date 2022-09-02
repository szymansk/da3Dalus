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



from Wand_erstellen import *
import logging

i_cpacs=5
	
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
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tiny_bit_skaliert.xml") 
if i_cpacs==5:
	tixi_h.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml") 
tigl_handle.open(tixi_h, "")




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
box = OPrim.BRepPrimAPI_MakeBox(1, 1, 1).Shape()
#moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-2.5,-2.5))
#cutted_fuselage_shape= OAlgo.BRepAlgoAPI_Cut(fuselage_shape,moved_box).Shape()
#fuselage_hollow=create_hollowedsolid(cutted_fuselage_shape,0.2)
    
display, start_display, add_menu, add_function_to_menu = init_display()

display.DisplayShape(wing_shape)
display.DisplayShape(wing_shape1)
display.DisplayShape(box)
display.DisplayShape(fuselage_shape, transparency=.8)
#display.DisplayShape(fuselage_hollow, transparency=.8)
#display.DisplayShape(moved_box, transparency=.8)


display.FitAll()
start_display()