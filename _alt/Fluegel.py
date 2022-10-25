#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored

from tigl3.tigl3wrapper import Tigl3, TiglBoolean
from tixi3.tixi3wrapper import Tixi3
import sys

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
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
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

from _alt.Wand_erstellen import Wandstaerke
from _alt.Aussparungen import Aussparung
from _alt.Innenstruktur import rippen
from _alt.shape_verschieben import verschieben
from _alt.abmasse import abmessungen
from stl_exporter.Ausgabeservice import ausgabe

from _alt.abmasse import *
from stl_exporter.Ausgabeservice import *
from _alt.Aussparungen import *
from _alt.Innenstruktur import *
from _alt.shape_verschieben import *
from _alt.Wand_erstellen import *

# In[2]:

# FIXME dont "initialize" the class, import Funktions
'''
w2=Wandstaerke()
a2=Aussparung()
r2=rippen()
v2=verschieben()
am2=abmessungen()
aus=ausgabe()
'''

class fluegel:
    
    def make_fluegel(self,tigl_h):
        #FIXME  unpack configuration 1 time and give it as paramater to the other function
        self.tigl_h=tigl_h
        # display, start_display, add_menu, add_function_to_menu = init_display()
        # get the configuration manager
        #mgr: config3.CCPACSConfigurationManager  = tigl3.configuration.CCPACSConfigurationManager_get_instance()
        mgr: TConfig.CCPACSConfigurationManager  = tigl3.configuration.CCPACSConfigurationManager_get_instance()
        
        # get the CPACS configuration, defined by the tigl handle
        # we need to access the underlying tigl handle (that is used in the C/C++ API)
        #config: config3.CCPACSConfiguration = mgr.get_configuration(tigl_h._handle.value)
        config: TConfig.CCPACSConfiguration = mgr.get_configuration(tigl_h._handle.value)

        #FIXME grid_spacing
        rasterabstand=2

        # Geometrie des Akkus anlegen
        akku = a2.make_akku_schacht(3,3,3,0.8)

        for iwing in range(1, config.get_wing_count() + 1):
        
            wing = config.get_wing(iwing)

            ############# AUSSPARUNG #############
            # Aussparung platzieren
            trafo=CTiglTransformation()
            trafo.add_translation(2,3,0)
            moved_box = trafo.transform(akku)
            #Aussparung als CNamedShape bennen
            namedBox = CNamedShape(moved_box, "CutOut")
            #Ausschneiden
            cutter = CCutShape(wing.get_loft(),namedBox)
            cutted_wing_shape = cutter.named_shape()
            #Dem Wing hinzufügen
            wing.get_loft().Set(cutted_wing_shape)
            ########################################


            wing_shape = wing.get_loft().shape()
            
            xmin,ymin,zmin,xmax,ymax,zmax = am2.get_koordinates(wing_shape)
            xdiff,zdiff,ydiff = am2.get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax)
         
            wing_shape_huelle = w2.create_hollowedsolid(wing_shape,0.04)
            # Ausgehoelter Fluegel als neues Shape setzten
            winghuelle=CNamedShape(wing_shape_huelle,"winghuelle")
            wing.get_loft().Set(winghuelle)


            #S=make_ribs(xdiff*0.5,ydiff,zdiff,2.0)
            S= r2.make_ribs(xdiff,ydiff,0.02,zdiff*2)
            #anzahl = 10
            anzahl=int(xdiff/rasterabstand)


            #Sneu = make_translation(S,-0.1,anzahl)
            #Sneu = v2.make_translation(S.Shape(),0.1,anzahl)
            #Sneu = v2.make_translation_fuse(S.Shape(),-0.9,anzahl)
            Sneu = v2.make_translation_fuse(S.Shape(),-rasterabstand,anzahl,rasterabstand)
            m_rippen = r2.move_rippen_neu(Sneu,xmin,ymax,zmin)

            #Ueberschneidung zwischen Rippen und Fluegel
            CommonSurface = BRepAlgoAPI_Common(m_rippen,wing_shape).Shape()
            ueberschneidung = CNamedShape(CommonSurface, "Rippen")

            #Rippen und Fluegel verbinden
            merger= CMergeShapes(wing.get_loft(), ueberschneidung)
            merger_wing_shape = merger.named_shape()
            wing.get_loft().Set(merger_wing_shape)
            #display.DisplayShape(wing.get_loft().shape())

            mirrored_shape = wing.get_mirrored_loft()

            #exluced vertikal wing
            #creates mirrored wing
            #fuses both wings to a set_of_wings
            #FIXME return Left, RIght and set of Wings
            #FIXME outsource the export funktion
            if mirrored_shape is not None:
                fused_wings = CFuseShapes(wing.get_loft(),wing.get_mirrored_loft()).named_shape()
                wing.get_loft().Set(fused_wings)
                #display.DisplayShape(wing.get_loft().shape(),transparency=0.8)

                #in STL exportieren
                aus.write_stl_file(wing.get_loft().shape(),"fluegel_neu")

                '''
                # Set up the mirror
                aTrsf= Ogp.gp_Trsf()
                aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
                # Apply the mirror transformation
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(verbunden, aTrsf)

                # Get the mirrored shape back out of the transformation and convert back to a wire
                aMirroredShape = aBRespTrsf.Shape()
                aMirroredShape
                
                fluegelgesamt=OAlgo.BRepAlgoAPI_Fuse(verbunden,aMirroredShape).Shape()
                write_stl_file2(fluegelgesamt,"fluegel.stl")
                # display.DisplayShape(fluegelgesamt,transparency=0.8)
                '''

            else:
                #display.DisplayShape(wing.get_loft(),transparency=0.8)
                aus.write_stl_file(wing.get_loft(),"fluegel_neu")

                '''
                display.DisplayShape(verbunden,transparency=0.8)
                aus.write_stl_file2(verbunden,"fluegel.stl")
                '''


        # display.FitAll()

        # start_display()
        
