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
from stl_exporter.Ausgabeservice import write_stl_file2
from _alt.abmasse import *
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging

def get_tigl_handler(i_cpacs):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    if i_cpacs==0:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
    if i_cpacs==1:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
    #if i_cpacs==2:
        #tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle
    

m= myDisplay.instance(True)


tigl_handle= get_tigl_handler(0)
config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)

wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
wing_loft: TGeo.CNamedShape = wing.get_loft()
wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
w_xmin,w_ymin,w_zmin,w_xmax,w_ymax,w_zmax=get_koordinates(wing_shape)
x,y,z=get_dimensions_from_Shape(wing_shape)
print("Wing", "x", w_xmin,"y",w_ymin,"z",w_zmin,"x",w_xmax,"y",w_ymax,"z",w_zmax )
print("Wing diff", "x", x,"y",y,"z",z)
m.display_in_origin(wing_shape)
#Set up the mirror
#wing1: TConfig.CCPaACSWing= cpacs_configuration.get_wing(3)   
#wing_loft1: TGeo.CNamedShape = wing1.get_loft()
#wing_shape1: OTopo.TopoDS_Shape = wing_loft1.shape()

fuselage: TConfig.CCPACSFuselage= cpacs_configuration.get_fuselage(1)
fuselage_loft: TGeo.CNamedShape= fuselage.get_loft()
fuselage_shape: OTopo.TopoDS_Shape=fuselage_loft.shape()
f_xmin,f_ymin,f_zmin,f_xmax,f_ymax,f_zmax=get_koordinates(fuselage_shape)
print("Fuselage", "x", f_xmin,"y",f_ymin,"z",f_zmin,"x",f_xmax,"y",f_ymax,"z",f_zmax )
m.display_in_origin(fuselage_shape)
m.display.DisplayMessage(point=Ogp.gp_Pnt(w_xmin,(w_ymax/2),w_zmax), text_to_write="o")

print("Done")
    
m.start()


    
