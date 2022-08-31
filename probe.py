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
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo



from Wand_erstellen import *
import logging

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
try:
    wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    # Set up the mirror
    aTrsf= Ogp.gp_Trsf()
    aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
    transformed_wing = OBuilder.BRepBuilderAPI_Transform(wing_shape, aTrsf)
    mirrored_wing= transformed_wing.Shape()
    complete_wing= OAlgo.BRepAlgoAPI_Fuse(wing_shape,mirrored_wing).Shape()

    named_wings_shape: TGeo.CNamedShape= TGeo.CNamedShape(complete_wing, "CutOut")
    print("complete:" ,type(complete_wing))
    facesToRemove = TopTools_ListOfShape()
    hollow_complete_wing= OOff.BRepOffsetAPI_MakeThickSolid(wing_shape, facesToRemove, 0.02, 0.001)
except:
    print("Kein Flügel vorhanden")

fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
facesToRemove = TopTools_ListOfShape()
fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(fuselage_shape, facesToRemove, 0.2, 0.001)



try:
    cutter= TBoo.CCutShape(fuselage_loft, named_wings_shape)
    cutted_fuselage_shape:TGeo.CNamedShape= cutter.named_shape()
    print(type(cutted_fuselage_shape))
    #fuselage.get_loft().Set(cutted_fuselage_shape)
    fuselage_hollow= create_hollowedsolid(fuselage.get_loft().shape() ,0.2)
    facesToRemove = TopTools_ListOfShape()
    #fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(fuselage.get_loft().shape(), facesToRemove, 0.2, 0.001)
    fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(cutted_fuselage_shape.shape(), facesToRemove, 0.2, 0.001).Shape()
except:
    print("kein Rumpfvorhanden")
    
display, start_display, add_menu, add_function_to_menu = init_display()
box = OPrim.BRepPrimAPI_MakeBox(1, 1, 1).Shape()

if fuselage_shape != None:
    display.DisplayShape(box)
    display.DisplayShape(fuselage_hollow, transparency=.8)
#if mirrored_wing != None:
   # display.DisplayShape(mirrored_wing)
#display.DisplayShape(hollow_complete_wing.Shape())
#display.DisplayShape(fuselage.get_loft().shape(), transparency=.8)
#display.DisplayShape(fuselage_hollow.Shape())
#display.DisplayShape(box)

display.FitAll()
start_display()