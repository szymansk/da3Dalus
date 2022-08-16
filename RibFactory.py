import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
from Rib import *


class RibFactory:
    
    def __init__(self) -> None:
        self.rib: Rib= Rib()
        
    
    def extrude_profile(self):
        return OPrim.BRepPrimAPI_MakePrism(
            self.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.rib.extrude_lenght)),
        )
        
    def make_rib_pattern(self,breite,anz,rasterabstand):
        s2=[]
        for i in range(anz):
            s2=OExs.translate_shp(self.rib.single,gp_Vec(0.0,breite,0.0))
            rippen=OAlgo.BRepAlgoAPI_Fuse(self.rib.single,s2).Shape()
            breite=breite-rasterabstand
            shape=rippen
        return shape