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
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import Extra.BooleanOperationsForLists as bof
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape

from Extra.mydisplay import myDisplay

if __name__ == "__main__":
    m = myDisplay.instance(True, 12)

    point = OPrim.BRepPrimAPI_MakeSphere(2).Shape()
    point2 = point
    point2 = OExs.translate_shp(point2, Ogp.gp_Vec(0, 2, 3))
    left = OPrim.BRepPrimAPI_MakeBox(10, 10, 10).Shape()

    list_tu_cut = [point, point2]
    m.display_in_origin(point)
    m.display_in_origin(point2)
    m.display_in_origin(left, True)

    # cuted= OAlgo.BRepAlgoAPI_Cut(left,point).Shape()
    cuted = bof.cut_list_of_shapes(left, list_tu_cut)
    m.display_this_shape(cuted)
    m.display_cut(cuted, left, point)
    m.start()
