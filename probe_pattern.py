import logging
from re import M
from turtle import position
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

from abmasse import get_dimensions, get_koordinate, get_koordinates
from mydisplay import myDisplay
from shape_verschieben import rotate_shape
from shapeslicer.ShapeSlicer import ShapeSlicer
import Zipfolder as myZip

 
def create_linear_pattern(shape, quantity, distance):
    pattern=shape
    for i in range(1,quantity):
        x= i*distance
        moved_shape= OExs.translate_shp(shape,Ogp.gp_Vec(x,0.0,0.0))
        newpattern= OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
        m.display_fuse(newpattern, pattern, moved_shape)
        pattern=newpattern
    return pattern


#testCylinder=OPrim.BRepPrimAPI_MakeCylinder(radius,self.fuselage_widht).Shape()
#self.m.display_this_shape(testCylinder)
m=myDisplay.instance(True)
cylinder= OPrim.BRepPrimAPI_MakeCylinder(1,5).Shape()
cylinder2= rotate_shape(cylinder, Ogp.gp_OX(), 90)
cylinder_pattern= create_linear_pattern(cylinder2, 5, 5)


m.display_this_shape(cylinder_pattern)
m.display.FitAll()
m.start()
        
    


