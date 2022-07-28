
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

#sys.path.append("C:/Users/motto/cad-modelling-service")

from Wand_erstellen import Wandstaerke
from Aussparungen import Aussparung
from Innenstruktur import rippen
from shape_verschieben import verschieben
from abmasse import abmessungen
from Ausgabeservice import ausgabe


# In[2]:


a1=Aussparung()
w1=Wandstaerke()
v1=verschieben()
i1=rippen()
ab1=abmessungen()
aus=ausgabe()



class profil:
    
    def make_translation_fuse(self,shape,breite,anz):
        self.shape = shape
        self.breite = breite
        self.anz = anz
        for i in range(anz):
            s2=translate_shp(shape,gp_Vec(0.0,breite,0.0))
            rippen=BRepAlgoAPI_Fuse(shape,s2).Shape()
            breite=breite-0.9
            shape=rippen
            
        return shape

    def make_profil(self,tigl_h):
        self.tigl_h=tigl_h
        display, start_display, add_menu, add_function_to_menu = init_display()
        #servo,b1,b2,fertig = a1.make_Servo(0.15,0.2,0.2)

        #display.DisplayShape(servo.Shape(),color="blue")
        #display.DisplayShape(b1)
        #display.DisplayShape(b2)
        '''
        tixi_h = tixi3wrapper.Tixi3()
        tigl_h = tigl3wrapper.Tigl3()

        #dir_path = os.path.dirname(os.path.realpath(__file__))
        tixi_h.open("C:/Users/motto/Downloads/tigl-master/tigl-master/tests/unittests/TestData/D150_v30.xml")
        #tixi_h.open("C:/Program Files/TIGL-3.2.3-win64 (1)/TIGL-3.2.3-win64/share/doc/tigl3/examples/simpletest.cpacs.xml")
        tigl_h.open(tixi_h, "")
        '''
        # get the configuration manager
        mgr = tigl3.configuration.CCPACSConfigurationManager_get_instance()

        # get the CPACS configuration, defined by the tigl handle
        # we need to access the underlying tigl handle (that is used in the C/C++ API)
        config = mgr.get_configuration(tigl_h._handle.value)
        
        CommonSurface=[]
        for ifuse in range(1, config.get_fuselage_count() + 1):
            fuselage = config.get_fuselage(ifuse)
            fuselage_shape = fuselage.get_loft().shape()

            #display.DisplayShape(fuselage_shape)

            xmin,ymin,zmin,xmax,ymax,zmax = ab1.get_koordinates(fuselage_shape)
            xdiff,zdiff,ydiff = ab1.get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax)
            #print(xdiff,zdiff,ydiff,xmax)
            #print(xmax,ymax,zmax)

            #S=make_ribs(ydiff,xdiff,0.1,xmax)
            # hoehe,breite,dicke,extrude
            S=i1.make_ribs(zdiff,ydiff,0.1,xmax*2)
            Srotate=v1.rotate_shape(S.Shape(),gp_OY(),90)
            anzahl = 3
            #Sneu = make_translation(Srotate,-0.1,anzahl)
            Sskdl= self.make_translation_fuse(Srotate,-0.9,anzahl)
            #display.DisplayShape(Sskdl)
            
            m_rippen = i1.move_rippen_neu(Sskdl,0,0,zdiff*0.5)
          
            #m_rippen = move_rippen_neu(Sskdl,0,0,0)
            #display.DisplayShape(m_rippen)
            #CommonSurface2=BRepAlgoAPI_Common(m_rippen,fuselage_shape).Shape()
            #display.DisplayShape(CommonSurface2)
            #verbunden=BRepAlgoAPI_Fuse(neu)

            #neu=[]
            #verbunden=[]
            profile=[]
            #CommonSurface3=[]
            #CS=[]

            for isegment in range(1, fuselage.get_segment_count() + 1):
            #for isegment in range(1, 16):
                segment = fuselage.get_segment(isegment)
                profile.append(segment.get_loft().shape())
                #CommonSurface3.append(BRepAlgoAPI_Common(m_rippen,profile[isegment-1]).Shape())
                #neu.append(w1.create_hollowedsolid(segment.get_loft().shape()))
                #verbunden.append(BRepAlgoAPI_Fuse(neu[isegment-1],CommonSurface3[isegment-1]).Shape())
                #verbunden.append(BRepAlgoAPI_Fuse(neu[isegment-1],CommonSurface3).Shape())
                #display.DisplayShape(verbunden)
                #display.DisplayShape(CommonSurface3)
            #display.DisplayShape(verbunden)

            cs=i1.fuse_shapes_common(profile)
            ausgehoelt=w1.create_hollowedsolid(cs)

            #display.DisplayShape(cs,transparency=0.8)
            #display.DisplayShape(neu,transparency=0.8)
            CommonSurface3=BRepAlgoAPI_Common(m_rippen,cs).Shape()

            #display.DisplayShape(CommonSurface3)
            fertig=BRepAlgoAPI_Fuse(ausgehoelt,CommonSurface3).Shape()
            
            display.DisplayShape(fertig,transparency=0.8)
            aus.write_stl_file2(fertig,"flugel.stl")
                #CS.append(BRepAlgoAPI_Common(m_rippen,profile[isegment-1]).Shape())
                #verbunden.append(BRepAlgoAPI_Fuse(neu[isegment-1],CS[isegment-1]).Shape())
            #display.DisplayShape(verbunden,transparency=0.8)
            #display.DisplayShape(CommonSurface3)

            
            
        display.FitAll()

        start_display()

        #return fertig
    


# In[ ]:



