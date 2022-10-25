from __future__ import print_function
from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored, name


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
from stl_exporter.Ausgabeservice import write_stl_file2, write_stls_srom_list
from _alt.abmasse import get_dimensions_from_Shape
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging

from Extra.ShapeSlicer import ShapeSlicer

def get_tigl_handler(i_cpacs):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    
    if i_cpacs==0:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
    if i_cpacs==1:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
    if i_cpacs==2:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_new.xml")
    if i_cpacs==3:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
    if i_cpacs==4:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\test_fuselage_v2.xml")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle
    

m= myDisplay.instance(True)

tigl_handle= get_tigl_handler(0)
config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()

cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
name2= fuselage.get_name()
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
x,y,z=get_dimensions_from_Shape(fuselage_shape)
msg= f"stest {name2}  {x:.3f} {y:.3f} {z:.3f} "
m.display_this_shape(fuselage_shape, msg)
m.display_in_origin(fuselage_shape, True)
name2= name2 + str(0) + ".stl"
box = OPrim.BRepPrimAPI_MakeBox(x*.6,y,z).Shape()
box = OExs.translate_shp(box,Ogp.gp_Vec(0.0,-y/2,0.0))
m.display_in_origin(box)
fuselage_done=OAlgo.BRepAlgoAPI_Cut(fuselage_shape, box).Shape()
m.display_cut(fuselage_done, fuselage_shape, box)
spliter=ShapeSlicer(fuselage_done,5,"test_fuselage")
spliter.slice()
write_stls_srom_list(spliter.parts_list)
#write_stl_file2(fuselage_shape,name2)
print("Done")
    
m.start()

    #wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
    #wing_loft: TGeo.CNamedShape = wing.get_loft()
    #wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    #Set up the mirror
    #wing1: TConfig.CCPACSWing= cpacs_configuration.get_wing(3)   
    #wing_loft1: TGeo.CNamedShape = wing1.get_loft()
    #wing_shape1: OTopo.TopoDS_Shape = wing_loft1.shape()
    
