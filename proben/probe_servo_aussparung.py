import math as math

import math as math

import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.TopTools as OTop
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *
from proben.probe_Cable_pipe import create_pipe


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
    

if __name__ == '__main__':
    m=ConstructionStepsViewer.instance(True)
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
   