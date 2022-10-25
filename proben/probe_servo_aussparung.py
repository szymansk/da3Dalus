
import zlib
import OCC.Core.gp as Ogp
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
from OCC.Core.ChFi2d import * #ChFi2d_AnaFilletAlgo
from Airplane.Wing.CablePipe import CabelPipe

import math as math
from re import A
from turtle import Shape
from unicodedata import mirrored, name


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
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.TopTools as OTop
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from stl_exporter.Ausgabeservice import write_stl_file2
from _alt.abmasse import *
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging

def draft_angle_from_shape(myshape):
    ListOfFace= TopTools_ListOfShape() 

    
    Direc= Ogp.gp_Dir(0.0,0.0,1.0); 
    # Z direction 
    Angle = 5*math.pi/180.; 
    # 5 degree angle 
    neutral_plane=Ogp.gp_Pln(Ogp.gp_Pnt(0.,0.,5.),Direc) 
    # Neutral plane Z=5 
    theDraft=OOff.BRepOffsetAPI_DraftAngle(myshape)
    #BRepOffsetAPI_DraftAngle theDraft(myShape); 
    itl=OTop.TopTools_ListIteratorOfListOfListOfShape()
    #TopTools_ListIteratorOfListOfShape itl; 
    
    aFaceExplorer = TopExp_Explorer(myshape, TopAbs_FACE)
    while aFaceExplorer.More():
        aFace: OTopo.TopoDS_Face = topods.Face(aFaceExplorer.Current())
        theDraft.Add(aFace,Direc,Angle,neutral_plane)
        if not theDraft.AddDone():
            #An error has occurred. The faulty face is given by //  ProblematicShape 
            break
        
        if not theDraft.AddDone():
            #An error has occured
            guilty:OTopo
    
    for (itl.Initialize(ListOfFace); itl.More(); itl.Next())  { 
        theDraft.Add(TopoDS::Face(itl.Value()),Direc,Angle,Neutral); 
        if  (!theDraft.AddDone()) { 
            // An error has occurred. The faulty face is given by //  ProblematicShape 
            break; 
            } 
    } 
    if (!theDraft.AddDone()) { 
        // An error has  occurred 
        TopoDS_Face guilty =  theDraft.ProblematicShape(); 
        ... 
    } 
    theDraft.Build(); 
    if (!theDraft.IsDone()) { 
        // Problem  encountered during reconstruction 
        ... 
    } 
    else { 
        TopoDS_Shape  myResult = theDraft.Shape(); 
        ... 
    } 

if __name__ == '__main__':
    m=myDisplay.instance(True)
    #pipe()
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
    tigl_handle.open(tixi_handle, "")
    config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
   
    cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
    wing: TConfig.CCPACSFuselage= cpacs_configuration.get_wing(1)
    name2= wing.get_name()
    wing_loft: TGeo.CNamedShape= wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape=wing_loft.shape()
    m.display_in_origin(wing_shape,True)
    pipe_complete=create_pipe(wing_shape)
    m.display_in_origin(pipe_complete)
    
    m.start()
   