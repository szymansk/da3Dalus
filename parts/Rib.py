import math
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRep as OBrep
from OCC.Core.gp import *
from collections import OrderedDict

class Rib:
    def __init__(self):
        self.compound= OrderedDict()
        self.primitive_shapes= OrderedDict()
        self.dimensions= ()
        self.ribs:OTopo.TopoDS_Shape= None
        self.profile:OTopo.TopoDS_Face=None
        self.reinforcement_tunnel_in:OTopo.TopoDS_Face=None
        self.reinforcement_tunnel_out:OTopo.TopoDS_Face=None
        self.spacing=None
        self.height= None
        self.width= None
        self.ydiff=None
        self.thikness= None
        self.extrude_lenght= None
        self.type:str=type
        

    def set_profile(self, type) -> OTopo.TopoDS_Face:
        '''
        set_profile x, /, -/,
        '''
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
        self.profile=face
        
    def x_profile(self)-> OTopo.TopoDS_Face:
        print("test:", self.height, self.thikness)
        gesamt_x = 0.0+math.tan(45)*self.height + self.thikness
        mitte_x = gesamt_x*0.5
        mitte_lx= (gesamt_x-self.thikness)*0.5
        mitte_rx= (gesamt_x+self.thikness)*0.5
        mitte_yl= self.height*0.5
        mitte_yo= (self.height+self.thikness)*0.5
        mitte_yu= (self.height-self.thikness)*0.5

        mkw = OBuilder.BRepBuilderAPI_MakeWire()

        ## Pkt 1 nach 2
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(mitte_lx,mitte_yl, 0.0)).Edge()
        )

        ## Pkt 2 nach 3
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_lx,mitte_yl, 0.0), gp_Pnt(0.0, self.height, 0.0)
            ).Edge()
        )
        ## Pkt 3 nach 4
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(0.0, self.height, 0.0), gp_Pnt(self.thikness, self.height, 0.0)
            ).Edge()
        )
        ## Pkt 4 nach 5
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(self.thikness, self.height, 0.0), gp_Pnt(mitte_x, mitte_yo, 0.0)
            ).Edge()
        )

        ##  Pkt5 nach 6
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                    gp_Pnt(mitte_x, mitte_yo, 0.0), gp_Pnt(gesamt_x-self.thikness,self.height , 0.0)
            ).Edge()
        )

        ## Pkt6 nach 7
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x-self.thikness,self.height , 0.0), gp_Pnt(gesamt_x, self.height, 0.0)
            ).Edge()
        )

        ## Pkt 7 nach 8
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x, self.height, 0.0), gp_Pnt(mitte_rx,mitte_yl, 0.0)
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
                gp_Pnt(gesamt_x, 0.0, 0.0), gp_Pnt(gesamt_x-self.thikness, 0.0, 0.0)
            ).Edge()
        )

        ## Pk 10 nach 11
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(gesamt_x-self.thikness, 0.0, 0.0), gp_Pnt(mitte_x, mitte_yu, 0.0)
            ).Edge()
        )

        ## Pk 11 nach 12
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(mitte_x, mitte_yu, 0.0), gp_Pnt(self.thikness, 0.0, 0.0)
            ).Edge()
        )

        ## Pk 12 nach 1
        mkw.Add(
            OBuilder.BRepBuilderAPI_MakeEdge(
                gp_Pnt(self.thikness, 0.0, 0.0), gp_Pnt(0.0, 0.0, 0.0)
            ).Edge()
        )
        
        face: OTopo.TopoDS_Face= OBuilder.BRepBuilderAPI_MakeFace(mkw.Wire()).Face()
        return face
    
