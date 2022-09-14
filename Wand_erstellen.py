#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

import os
import sys
from math import radians

import numpy as np
import OCC.Core.TopoDS as OTopo
import tigl3.boolean_ops
import tigl3.configuration
import tigl3.curve_factories
import tigl3.exports
import tigl3.geometry
import tigl3.surface_factories
from OCC.Core import StlAPI
from OCC.Core.Bnd import Bnd_Box
import OCC.Core.Geom as OGeom
import OCC.Core.BRepOffsetAPI as OBrepOffset
from OCC.Core.BOPAlgo import BOPAlgo_MakerVolume
from OCC.Core.BRep import BRep_Builder, BRep_Tool_Surface
from OCC.Core.BRepAlgoAPI import (BRepAlgoAPI_Common, BRepAlgoAPI_Cut,
                                  BRepAlgoAPI_Fuse, BRepAlgoAPI_Section)
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                     BRepBuilderAPI_MakeFace,
                                     BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_Transform)
from OCC.Core.BRepFeat import (BRepFeat_MakeDPrism, BRepFeat_MakeLinearForm,
                               BRepFeat_MakePrism, BRepFeat_MakeRevol,
                               BRepFeat_SplitShape)
from OCC.Core.BRepGProp import (brepgprop_SurfaceProperties,
                                brepgprop_VolumeProperties)
from OCC.Core.BRepOffset import BRepOffset_Skin
from OCC.Core.BRepOffsetAPI import (BRepOffsetAPI_MakeThickSolid,
                                    BRepOffsetAPI_ThruSections)
from OCC.Core.BRepPrimAPI import (BRepPrimAPI_MakeBox,
                                  BRepPrimAPI_MakeCylinder,
                                  BRepPrimAPI_MakePrism)
from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Surface
from OCC.Core.Geom2d import Geom2d_Curve, Geom2d_Ellipse, Geom2d_TrimmedCurve
from OCC.Core.gp import (gp_Ax1, gp_Ax2, gp_Ax2d, gp_Ax3, gp_Dir, gp_Dir2d,
                         gp_DZ, gp_OX, gp_OY, gp_OZ, gp_Pnt, gp_Pnt2d, gp_Trsf,
                         gp_Vec)
from OCC.Core.GProp import GProp_GProps
from OCC.Core.Quantity import Quantity_NOC_RED
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import (TopoDS_Compound, TopoDS_Edge, TopoDS_Shell,
                             TopoDS_Solid, TopoDS_Wire, topods)
from OCC.Core.TopTools import TopTools_ListOfShape
from OCC.Display.SimpleGui import init_display
from OCC.Display.WebGl.jupyter_renderer import JupyterRenderer
from OCC.Extend.ShapeFactory import translate_shp
from OCC.Extend.TopologyUtils import TopologyExplorer
from tigl3 import tigl3wrapper
from tigl3.geometry import CTiglTransformation
from tigl3.tigl3wrapper import Tigl3, TiglBoolean
from tixi3 import tixi3wrapper
from tixi3.tixi3wrapper import Tixi3

from mydisplay import myDisplay



#class Wandstaerke:
def face_is_plane(face):

    #Returns True if the TopoDS_Shape is a plane, False otherwise
    hs: OGeom.Geom_Surface = BRep_Tool_Surface(face)
    downcast_result= OGeom.Geom_Plane.DownCast(hs)
    print(type(downcast_result))

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
    print("Starting Create Hollow")
    # We have to work our way through all the faces to find the highest Z face so we can remove it for the shell
    aFaceExplorer = TopExp_Explorer(shape, TopAbs_FACE)
    while aFaceExplorer.More():
        aFace: OTopo.TopoDS_Face = topods.Face(aFaceExplorer.Current())

        if face_is_plane(aFace):
            aPlane = geom_plane_from_face(aFace)

            # We want the highest Z face, so compare this to the previous faces
            aPnt = aPlane.Location()
            aZ = aPnt.Z()
            print(aZ)
            if aZ > zMax:
                zMax = aZ
                faceToRemove = aFace
        aFaceExplorer.Next()

    facesToRemove: TopTools_ListOfShape = TopTools_ListOfShape()
    print("--------Faces to remove Size:" + str(facesToRemove.Size())) 
    if faceToRemove != None:
        print("Faces to remove is not empty")
        facesToRemove.Append(faceToRemove)
    myBody= BRepOffsetAPI_MakeThickSolid(shape, facesToRemove, thickness, 0.001)
    #else:
        #solidmaker= OBrepOffset.BRepOffsetAPI_MakeThickSolid()
        #myBody= OBrepOffset.BRepOffsetAPI_MakeThickSolid.MakeThickSolidBySimple(shape, thickness)
        #print(type(myBody))
        #myBody= BRepOffsetAPI_MakeThickSolid.MakeThickSolidBySimple(shape, thickness, thickness)
    #myBody = BRepOffsetAPI_MakeThickSolid(myBody, facesToRemove, -thickness / 50.0, 0.001)

    #print("--------------------IsDone:", myBody.IsDone())
    myBody=myBody.Shape()

    return myBody

