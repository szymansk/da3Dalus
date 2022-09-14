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
from mydisplay import *

from abmasse import get_dimensions, get_koordinates


m= myDisplay(0.5,True)
wand=0.1
complete=None
x,y,z= 10,10,10
box2= OPrim.BRepPrimAPI_MakeBox(x, y, z).Shape()
for i in range(0,2):
    print("i:" + str(i) + " i+10: "+ str(i*10))
    box= OPrim.BRepPrimAPI_MakeBox(x, y, z).Shape()
    j=i*10
    wand+=0.2
    moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0, j, 0))
    hollow=create_hollowedsolid(moved_box,wand)
    if i==0:
        complete=hollow
    else:
        complete=OAlgo.BRepAlgoAPI_Fuse(complete,hollow).Shape()
    m.display_this_shape(hollow,"",True)
    m.display.FitAll()

#box= OPrim.BRepPrimAPI_MakeBox(x/2, y*2, z).Shape()
m.display_this_shape(box2)

m.start()

write_stl_file2(complete, "box_test.stl")