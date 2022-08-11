#!/usr/bin/env python
# coding: utf-8

# In[49]:


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
from OCC.Core.gp import gp_Pnt, gp_OX, gp_OY,gp_OZ, gp_Vec, gp_Trsf, gp_DZ,gp_DX, gp_Ax2, gp_Ax3, gp_Pnt2d, gp_Dir2d, gp_Ax2d, gp_Dir
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




# In[50]:


class Aussparung:
    
    def motor_auslesen(pfad):
        from xml.etree.ElementTree import parse
        doc = parse(pfad).getroot()

        for element in doc.findall('engine'):
            shaftDiameter=float(element.find('shaftDiameter').text)
            shaftLength=float(element.find('shaftLength').text)
            motorLength=float(element.find('motorLength').text)
            motorDiameter=float(element.find('motorDiameter').text)
            overallLength=float(element.find('overallLength').text)
            connectorType=float(element.find('connectorType').text)
            slots=float(element.find('slots').text)
            poles=float(element.find('poles').text)
            
        return shaftDiameter, shaftLength,motorLength,motorDiameter,overallLength,connectorType,slots,poles

    def servo_auslesen(pfad):
        from xml.etree.ElementTree import parse
        doc = parse(pfad).getroot()

        for element in doc.findall('engine'):
            shaftDiameter=float(element.find('shaftDiameter').text)
            shaftLength=float(element.find('shaftLength').text)
            motorLength=float(element.find('motorLength').text)
            motorDiameter=float(element.find('motorDiameter').text)
            overallLength=float(element.find('overallLength').text)
            connectorType=float(element.find('connectorType').text)
            slots=float(element.find('slots').text)
            poles=float(element.find('poles').text)
            
        return shaftDiameter, shaftLength,motorLength,motorDiameter,overallLength,connectorType,slots,poles
       
    def make_motor_schacht(shaftDiameter,shaftLength,motorLength,motorDiameter,overallLength):
        puffer=1
        skalierung=1
        shaftDiameter*=skalierung
        shaftLength*=skalierung
        motorLength*=skalierung
        motorDiameter*=skalierung
        overallLength*=skalierung
        '''
        shaftDiameter+=puffer
        shaftLength+=puffer
        motorLength+=puffer
        motorDiameter+=puffer
        overallLength+=puffer
        '''
        motor=BRepPrimAPI_MakeCylinder(motorDiameter, motorLength).Shape()

        neckLocation = gp_Pnt(0, 0, motorLength)
        neckAxis = gp_DZ()
        neckAx2 = gp_Ax2(neckLocation, neckAxis)
        schaft=BRepPrimAPI_MakeCylinder(neckAx2,shaftDiameter,shaftLength).Shape()

        fertig=BRepAlgoAPI_Fuse(motor,schaft)
        
        angle = radians(-90)
        trns = gp_Trsf()
        trns.SetRotation(gp_OY(), angle)
        brep_trns = BRepBuilderAPI_Transform(fertig.Shape(), trns, False)
        brep_trns.Build()
        fertig = brep_trns.Shape()
        
        #display.DisplayShape(shp)
        #display.FitAll()

        #start_display()

        return fertig
    
    def make_akku_schacht(length,height,width,puffer):
        length+=puffer
        height+=puffer
        width+=puffer
        
        akku=BRepPrimAPI_MakeBox(length,height,width).Shape()
        #display.DisplayShape(akku)
        #display.FitAll()
        #start_display()
        return akku
        
    def verschieben(shape,x,y,z):
        s2=translate_shp(shape,gp_Vec(x,y,z))
        return s2
        
    def make_Servo(self,hoehe,breite,tiefe):
        import math
        dreieckoben_y = hoehe+math.tan(45)*(breite*0.5)
        dreieckunten_y = -math.tan(45)*(breite*0.5)

        breitedreieckgesamt= ((hoehe*0.5)/math.tan(45))*2+breite
        breitedreieck= (hoehe*0.5)/math.tan(45)

        mkw = BRepBuilderAPI_MakeWire()

        ## Pkt 1 nach 2
        mkw.Add(
            BRepBuilderAPI_MakeEdge(gp_Pnt(0.0, 0.0, hoehe*0.5), gp_Pnt(breitedreieck,0.0, 0.0)).Edge()
        )
        ## Pkt 2 nach 3
        mkw.Add(
            BRepBuilderAPI_MakeEdge(gp_Pnt(breitedreieck,0.0, 0.0), gp_Pnt(breitedreieck+breite,0.0, 0.0)).Edge()
        )

        ## Pkt 3 nach 4
        mkw.Add(
            BRepBuilderAPI_MakeEdge(
                gp_Pnt(breitedreieck+breite,0.0, 0.0), gp_Pnt(breitedreieckgesamt, 0.0, hoehe*0.5)
            ).Edge()
        )
        ## Pkt 4 nach 5
        mkw.Add(
            BRepBuilderAPI_MakeEdge(
                gp_Pnt(breitedreieckgesamt, 0.0, hoehe*0.5), gp_Pnt(breitedreieck+breite, 0.0, hoehe)
            ).Edge()
        )

        ## Pkt 5 nach 6
        mkw.Add(
            BRepBuilderAPI_MakeEdge(
                gp_Pnt(breitedreieck+breite, 0.0, hoehe), gp_Pnt(breitedreieck, 0.0, hoehe)
            ).Edge()
        )
        ## Pkt 6 nach 1
        mkw.Add(
            BRepBuilderAPI_MakeEdge(
                gp_Pnt(breitedreieck, 0.0, hoehe), gp_Pnt(0.0, 0.0, hoehe*0.5)
            ).Edge()
        )

        S = BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, tiefe,0.0 )),
        )

        A=0.23
        B=0.16
        C=0.23
        D=0.12
        E=0.32
        F=0.16
        b1 = BRepPrimAPI_MakeBox(F,B,D).Shape()


        b2= BRepPrimAPI_MakeBox(A-F,E,D).Shape()

        mitte = (E-B)*0.5
        b2=self.verschieben(b2,0.0,-mitte,0.0)

        servo=BRepAlgoAPI_Fuse(b1,b2).Shape()

        return S,b1,b2,servo
        
        
    #fertig=make_motor_schacht(shaftDiameter,shaftLength,motorLength,motorDiameter,overallLength)
    #display.DisplayShape(fertig.Shape())
    #display.DisplayShape(schaft)


    #display.FitAll()

    #start_display()
