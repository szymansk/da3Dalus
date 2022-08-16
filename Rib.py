import math
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRep as OBrep
from OCC.Core.gp import *

class Rib:
    
    def __init__(self, profile_height, profile_thikness, extrude_lenght,type:str="x") -> None:
        self.profile_height= profile_height
        self.profile_thikness=profile_thikness
        self.extrude_lenght=extrude_lenght
        self.type:str=type
        self.profile:OTopo.TopoDS_Face=self.face_profile(type)
        self.single=self.extrude_profile(extrude_lenght)
        

        
    
    def face_profile(self, type) -> OTopo.TopoDS_Face:
        face:OTopo.TopoDS_Face=None
        if type=="/":
            #TODO / profile Funktion
            pass
        elif type=="-":#
            #TODO - profile Fuktion
            pass
        elif type=="/-":
            pass
        else : #x
            face= self.x_profile()        
        return face
        
    def x_profile(self)-> OTopo.TopoDS_Face:
        gesamt_x = 0.0+math.tan(45)*self.profile_height + self.profile_thikness
        mitte_x = gesamt_x*0.5
        mitte_lx= (gesamt_x-self.profile_thikness)*0.5
        mitte_rx= (gesamt_x+self.profile_thikness)*0.5
        mitte_yl= self.profile_height*0.5
        mitte_yo= (self.profile_height+self.profile_thikness)*0.5
        mitte_yu= (self.profile_height-self.profile_thikness)*0.5

        mkw = OBuilder.BRepBuilderAPI_MakeWire()

        ## Pkt 1 nach 2
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(mitte_lx,mitte_yl, 0.0)).Edge()
        )

        ## Pkt 2 nach 3
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_lx,mitte_yl, 0.0), gp_Pnt(0.0, self.profile_height, 0.0)
            ).Edge()
        )
        ## Pkt 3 nach 4
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(0.0, self.profile_height, 0.0), gp_Pnt(self.profile_thikness, self.profile_height, 0.0)
            ).Edge()
        )
        ## Pkt 4 nach 5
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(self.profile_thikness, self.profile_height, 0.0), gp_Pnt(mitte_x, mitte_yo, 0.0)
            ).Edge()
        )

        ##  Pkt5 nach 6
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                    gp_Pnt(mitte_x, mitte_yo, 0.0), gp_Pnt(gesamt_x-self.profile_thikness,self.profile_height , 0.0)
            ).Edge()
        )

        ## Pkt6 nach 7
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x-self.profile_thikness,self.profile_height , 0.0), gp_Pnt(gesamt_x, self.profile_height, 0.0)
            ).Edge()
        )

        ## Pkt 7 nach 8
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x, self.profile_height, 0.0), gp_Pnt(mitte_rx,mitte_yl, 0.0)
            ).Edge()
        )

        ## Pkt 8 nach 9
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_rx,mitte_yl, 0.0), gp_Pnt(gesamt_x, 0.0, 0.0)
            ).Edge()
        )

        ## Pk 9 nach 10
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x, 0.0, 0.0), gp_Pnt(gesamt_x-self.profile_thikness, 0.0, 0.0)
            ).Edge()
        )

        ## Pk 10 nach 11
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x-self.profile_thikness, 0.0, 0.0), gp_Pnt(mitte_x, mitte_yu, 0.0)
            ).Edge()
        )

        ## Pk 11 nach 12
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_x, mitte_yu, 0.0), gp_Pnt(self.profile_thikness, 0.0, 0.0)
            ).Edge()
        )

        ## Pk 12 nach 1
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(self.profile_thikness, 0.0, 0.0), gp_Pnt(0.0, 0.0, 0.0)
            ).Edge()
        )
        
        face: OTopo.TopoDS_Face= OBuilder.BRepBuilderAPI_MakeFace(mkw.Wire()).Face()
        return face
        
            

                