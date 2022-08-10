#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function
from unicodedata import mirrored

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

#import sys

#sys.path.append("C:/Users/motto/Downloads/tigl-examples-master/tigl-examples-master/tigl/python/geometry-modeling")
#sys.path.append("C:/Users/motto/cad-modelling-service")

from Wand_erstellen import Wandstaerke
from Aussparungen import Aussparung
from Innenstruktur import rippen
from shape_verschieben import verschieben
from abmasse import abmessungen
from Ausgabeservice import ausgabe


# In[2]:


w2=Wandstaerke()
a2=Aussparung()
r2=rippen()
v2=verschieben()
am2=abmessungen()
aus=ausgabe()


class fluegel:
    
    def make_fluegel(self,tigl_h):
        self.tigl_h=tigl_h
        # display, start_display, add_menu, add_function_to_menu = init_display()
        '''
        tixi_h = tixi3wrapper.Tixi3()
        tigl_h = tigl3wrapper.Tigl3()


        tixi_h.open("C:/Users/motto/Downloads/tigl-master/tigl-master/tests/unittests/TestData/D150_v30.xml")

        tigl_h.open(tixi_h, "")
        '''
        # get the configuration manager
        mgr = tigl3.configuration.CCPACSConfigurationManager_get_instance()

        # get the CPACS configuration, defined by the tigl handle
        # we need to access the underlying tigl handle (that is used in the C/C++ API)
        config = mgr.get_configuration(tigl_h._handle.value)


        #for iwing in range(1, config.get_wing_count() + 1):
        for iwing in range(1, 2):

            wing = config.get_wing(iwing)
            wing_shape = wing.get_loft().shape()
            xmin,ymin,zmin,xmax,ymax,zmax = am2.get_koordinates(wing_shape)

            mirrored_shape = wing.get_mirrored_loft()
            

            wing_shape_huelle = w2.create_hollowedsolid(wing_shape)
            xdiff,zdiff,ydiff = am2.get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax)


            #S=make_ribs(xdiff*0.5,ydiff,zdiff,2.0)
            S= r2.make_ribs(xdiff,ydiff,0.2,zdiff)
            #anzahl = 200
            anzahl = 10


            #Sneu = make_translation(S,-0.1,anzahl)
            #Sneu = v2.make_translation(S.Shape(),0.1,anzahl)
            Sneu = v2.make_translation_fuse(S.Shape(),-0.9,anzahl)
            m_rippen = r2.move_rippen_neu(Sneu,xmin,ymax,zmin)

            CommonSurface = BRepAlgoAPI_Common(m_rippen,wing_shape).Shape()
            verbunden= BRepAlgoAPI_Fuse(wing_shape_huelle,CommonSurface).Shape()

            if mirrored_shape is not None:
                # Set up the mirror
                aTrsf= gp_Trsf()
                aTrsf.SetMirror(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(0,1,0)))
                # Apply the mirror transformation
                aBRespTrsf = BRepBuilderAPI_Transform(verbunden, aTrsf)

                # Get the mirrored shape back out of the transformation and convert back to a wire
                aMirroredShape = aBRespTrsf.Shape()
                
                fluegelgesamt=BRepAlgoAPI_Fuse(verbunden,aMirroredShape).Shape()
                aus.write_stl_file2(fluegelgesamt,"fluegel.stl")
                # display.DisplayShape(fluegelgesamt,transparency=0.8)
                

            else:
                # display.DisplayShape(verbunden,transparency=0.8)
                aus.write_stl_file2(verbunden,"fluegel.stl")
                


        # display.FitAll()

        # start_display()
        
