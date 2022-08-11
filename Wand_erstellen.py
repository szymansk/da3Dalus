#!/usr/bin/env python
# coding: utf-8

# In[1]:


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

from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box

from OCC.Core.Quantity import Quantity_NOC_RED
import os

from math import radians

builder = BRep_Builder()
shell = TopoDS_Shell()
builder.MakeShell(shell)




# In[2]:


#class Wandstaerke:
def face_is_plane(face):

    #Returns True if the TopoDS_Shape is a plane, False otherwise

    hs = BRep_Tool_Surface(face)
    downcast_result= Geom_Plane.DownCast(hs)
    #print(downcast_result)

    if downcast_result is None:
        return False
    else:
        return True

def geom_plane_from_face(aFace):

    #Returns the geometric plane entity from a planar surface

    return Geom_Plane.DownCast(BRep_Tool_Surface(aFace))

def create_hollowedsolid(shape,thickness):
    # Our goal is to find the highest Z face and remove it
    faceToRemove = None
    zMax = -1

    # We have to work our way through all the faces to find the highest Z face so we can remove it for the shell
    aFaceExplorer = TopExp_Explorer(shape, TopAbs_FACE)
    while aFaceExplorer.More():
        aFace = topods.Face(aFaceExplorer.Current())

        if face_is_plane(aFace):
            aPlane = geom_plane_from_face(aFace)

            # We want the highest Z face, so compare this to the previous faces
            aPnt = aPlane.Location()
            aZ = aPnt.Z()
            if aZ > zMax:
                zMax = aZ
                faceToRemove = aFace

        aFaceExplorer.Next()

    facesToRemove = TopTools_ListOfShape()
    facesToRemove.Append(faceToRemove)

    #myBody = BRepOffsetAPI_MakeThickSolid(myBody, facesToRemove, -thickness / 50.0, 0.001)
    myBody = BRepOffsetAPI_MakeThickSolid(shape, facesToRemove, thickness, 0.001)
    myBody=myBody.Shape()

    return myBody

