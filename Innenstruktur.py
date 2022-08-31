#!/usr/bin/env python
# coding: utf-8

# In[2]:


from __future__ import print_function

from tigl3.tigl3wrapper import Tigl3, TiglBoolean
from tixi3.tixi3wrapper import Tixi3
import sys

from tigl3.geometry import CTiglTransformation

import tigl3.configuration, tigl3.geometry, tigl3.boolean_ops, tigl3.exports
from OCC.Core.Quantity import Quantity_NOC_RED
import os

import tigl3.curve_factories
import tigl3.surface_factories
from OCC.Core.gp import gp_Pnt, gp_OX, gp_OY,gp_OZ, gp_Vec, gp_Trsf, gp_DZ, gp_Ax2, gp_Ax3, gp_Pnt2d, gp_Dir2d, gp_Ax2d, gp_Dir
from OCC.Core.gp import gp_Ax1, gp_Pnt, gp_Dir, gp_Trsf
from OCC.Display.SimpleGui import init_display

from OCC.Display.WebGl.jupyter_renderer import JupyterRenderer
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeEdge
from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism, BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeBox

from OCC.Core.BRep import BRep_Tool_Surface, BRep_Builder
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCC.Core.TopoDS import topods, TopoDS_Edge, TopoDS_Compound
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopTools import TopTools_ListOfShape

from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume

from OCC.Core.BRepOffset import BRepOffset_Skin
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeThickSolid, BRepOffsetAPI_ThruSections

from OCC.Core.BRepFeat import (
    BRepFeat_MakePrism,
    BRepFeat_MakeDPrism,
    BRepFeat_SplitShape,
    BRepFeat_MakeLinearForm,
    BRepFeat_MakeRevol,
)

from OCC.Core.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Surface
from OCC.Core.Geom2d import Geom2d_TrimmedCurve, Geom2d_Ellipse, Geom2d_Curve

from OCC.Core.TopoDS import TopoDS_Shell, TopoDS_Solid, TopoDS_Wire, TopoDS_Edge
from OCC.Core import StlAPI

import numpy as np

from OCC.Core.BRepAlgoAPI import (
    BRepAlgoAPI_Fuse,
    BRepAlgoAPI_Common,
    BRepAlgoAPI_Section,
    BRepAlgoAPI_Cut,
)

from OCC.Extend.TopologyUtils import TopologyExplorer
from OCC.Extend.ShapeFactory import translate_shp

from OCC.Core.GProp import GProp_GProps
from OCC.Core.BRepGProp import brepgprop_VolumeProperties, brepgprop_SurfaceProperties

from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.configuration, tigl3.geometry, tigl3.boolean_ops, tigl3.exports

from tigl3.geometry import CTiglTransformation

from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box

from OCC.Core.Quantity import Quantity_NOC_RED
import os

from math import radians

builder = BRep_Builder()
shell = TopoDS_Shell()
builder.MakeShell(shell)


# In[3]:


#class rippen:
def make_ribs(hoehe,breite,dicke,extrude):
    import math
    #hoehe=0.03
    #breite=0.03
    #dicke=0.015

    gesamt_x = 0.0+math.tan(45)*hoehe+dicke
    mitte_x = gesamt_x*0.5
    mitte_lx= (gesamt_x-dicke)*0.5
    mitte_rx= (gesamt_x+dicke)*0.5
    mitte_yl= hoehe*0.5
    mitte_yo= (hoehe+dicke)*0.5
    mitte_yu= (hoehe-dicke)*0.5

    mkw = BRepBuilderAPI_MakeWire()

    ## Pkt 1 nach 2
    mkw.Add(
        BRepBuilderAPI_MakeEdge(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(mitte_lx,mitte_yl, 0.0)).Edge()
    )

    ## Pkt 2 nach 3
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(mitte_lx,mitte_yl, 0.0), gp_Pnt(0.0, hoehe, 0.0)
        ).Edge()
    )
    ## Pkt 3 nach 4
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(0.0, hoehe, 0.0), gp_Pnt(dicke, hoehe, 0.0)
        ).Edge()
    )
    ## Pkt 4 nach 5
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(dicke, hoehe, 0.0), gp_Pnt(mitte_x, mitte_yo, 0.0)
        ).Edge()
    )

    ##  Pkt5 nach 6
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_x, mitte_yo, 0.0), gp_Pnt(gesamt_x-dicke,hoehe , 0.0)
        ).Edge()
    )

    ## Pkt6 nach 7
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(gesamt_x-dicke,hoehe , 0.0), gp_Pnt(gesamt_x, hoehe, 0.0)
        ).Edge()
    )

    ## Pkt 7 nach 8
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(gesamt_x, hoehe, 0.0), gp_Pnt(mitte_rx,mitte_yl, 0.0)
        ).Edge()
    )

    ## Pkt 8 nach 9
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(mitte_rx,mitte_yl, 0.0), gp_Pnt(gesamt_x, 0.0, 0.0)
        ).Edge()
    )

    ## Pk 9 nach 10
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(gesamt_x, 0.0, 0.0), gp_Pnt(gesamt_x-dicke, 0.0, 0.0)
        ).Edge()
    )

    ## Pk 10 nach 11
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(gesamt_x-dicke, 0.0, 0.0), gp_Pnt(mitte_x, mitte_yu, 0.0)
        ).Edge()
    )

    ## Pk 11 nach 12
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(mitte_x, mitte_yu, 0.0), gp_Pnt(dicke, 0.0, 0.0)
        ).Edge()
    )

    ## Pk 12 nach 1
    mkw.Add(
        BRepBuilderAPI_MakeEdge(
            gp_Pnt(dicke, 0.0, 0.0), gp_Pnt(0.0, 0.0, 0.0)
        ).Edge()
    )

    #neu=mirrow_shape_y(mkw)
    #neu2 =mirrow_shape_x(mkw)

    S = BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, extrude)),
        )

    ## verschieben damit gesamtes Modell drinnen ist
    ########################  z    y   z 
    #S2=verschieben(S.Shape(),0.0,0.0,0.0)
    #S2=rotate_shape(S.Shape(),gp_OY,90)

    return S

def move_rippen_neu(rippen_gesamt,xmin,ymin,zmin):
    from tigl3.geometry import CTiglTransformation
    #help(CTiglTransformation)

    trafo = CTiglTransformation()
    trafo.add_translation(xmin,ymin,zmin)
    moved_rippen=trafo.transform(rippen_gesamt)

    return moved_rippen

def move_rippen(self,rippen_gesamt,xmin,ymin,zmin):
    from tigl3.geometry import CTiglTransformation
    #help(CTiglTransformation)

    trafo = CTiglTransformation()
    trafo.add_translation(xmin,ymin,zmin)

    self.moved_rippen=[]
    anzahl=35
    for a in range(anzahl-1):
        self.moved_rippen.append(trafo.transform(rippen_gesamt[a]))
        #display.DisplayShape(moved_rippen[a])

    return self.moved_rippen

def fuse_shapes_common(Commonsurface):
    i=0
    fertig=Commonsurface[i]
    while (i+1)<(len(Commonsurface)-1):
        for i in range(len(Commonsurface)-1):
            #common=BRepAlgoAPI_Fuse(Commonsurface[i],Commonsurface[i+1]).Shape()
            common=BRepAlgoAPI_Fuse(fertig,Commonsurface[i]).Shape()
            fertig=common
                                    
    return fertig






# %%
