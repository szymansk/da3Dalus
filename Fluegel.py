#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as config3
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as geo
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
'''
from OCC.Core.BRep import BRep_Builder, BRep_Tool_Surface
from OCC.Core.BRepAlgoAPI import (BRepAlgoAPI_Common, BRepAlgoAPI_Cut,
                                  BRepAlgoAPI_Fuse, BRepAlgoAPI_Section)
from OCC.Core.BRepBuilderAPI import (BRepBuilderAPI_MakeEdge,
                                     BRepBuilderAPI_MakeFace,
                                     BRepBuilderAPI_MakeWire,
                                     BRepBuilderAPI_Transform)
                                     
from OCC.Core.BRepFeat import (BRepFeat_MakeDPrism, BRepFeat_MakeLinearForm,
                               BRepFeat_MakePrism, BRepFeat_MakeRevol,
                               BRepFeat_SplitShape)
                               from OCC.Core.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCC.Core.GCE2d import GCE2d_MakeSegment
from OCC.Core.Geom import Geom_CylindricalSurface, Geom_Plane, Geom_Surface
from OCC.Core.Geom2d import Geom2d_Curve, Geom2d_Ellipse, Geom2d_TrimmedCurve
'''
builder = OBrep.BRep_Builder() 
shell = OTopo.TopoDS_Shell()
builder.MakeShell(shell)

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *

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
        mgr = tigl3.configuration.CCPACSConfigurationManager_get_instance()
        
        # get the CPACS configuration, defined by the tigl handle
        # we need to access the underlying tigl handle (that is used in the C/C++ API)
        #config: config3.CCPACSConfiguration = mgr.get_configuration(tigl_h._handle.value)
        config = mgr.get_configuration(tigl_h._handle.value)

        #FIXME grid_spacing
        rasterabstand=2

        for iwing in range(1, config.get_wing_count() + 1):
            #Get wing returns CPACSWing, XML Wing description
            wing = config.get_wing(iwing)

            #Get_loft()-shape() creates a TigleShape out of the Wing
            #3D solid  with Tigl metadata
            wing_shape = wing.get_loft().shape()
                      
            #returns the korditnates from the bound box of the Wing_shape
            #calculate the diferences
            xmin,ymin,zmin,xmax,ymax,zmax = get_koordinates(wing_shape)
            xdiff,zdiff,ydiff = get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax)
            
            #create mirror loft, if not possible return null. 
            #Vertikal wing has no mirrored loft
            mirrored_shape = wing.get_mirrored_loft()
            
            #makes a hollowed shape from wing with a thickness 0.04
            wing_shape_huelle = create_hollowedsolid(wing_shape,0.04)
            
            #creates 1 rib with an X-profile
            #FIXME change names in definition, and remove unused "breite"
            # def make_ribs(self,hoehe,-breite,dicke,extrude):
            S= make_ribs(xdiff,ydiff,0.02,zdiff*2)
            
            #calculate de ammount of ribs that should be created
            anzahl=int(xdiff/rasterabstand)

            #create a shape of a pattern of ribs
            Sneu: OTopo.TopoDS_Shape= make_translation_fuse(S.Shape(),-rasterabstand,anzahl,rasterabstand)
            
            #moves the pattern to a new Position
            m_rippen = move_rippen_neu(Sneu,xmin,ymax,zmin)
            
            #cuts the ribs to the shape of the wing
            CommonSurface = OAlgo.BRepAlgoAPI_Common(m_rippen,wing_shape).Shape()
            #fuses Wing and Ribs to 1 shape
            verbunden= OAlgo.BRepAlgoAPI_Fuse(wing_shape_huelle,CommonSurface).Shape()

            #exluced vertikal wing
            #creates mirrored wing
            #fuses both wings to a set_of_wings
            #FIXME return Left, RIght and set of Wings
            #FIXME outsource the export funktion
            if mirrored_shape is not None:
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
                

            else:
                # display.DisplayShape(verbunden,transparency=0.8)
                write_stl_file2(verbunden,"fluegel.stl")
                


        # display.FitAll()

        # start_display()
        
