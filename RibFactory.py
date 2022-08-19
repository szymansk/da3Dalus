import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
from math import *
from Ribs import *


class RibFactory:
    
    def __init__(self,) -> None:
        self.single=None
        self.multiple=None
    
    def create_rib(self,profile_height, profile_thikness, extrude_lenght):
        self.single = Ribs(profile_height, profile_thikness, extrude_lenght)
        
    def extrude_profile(self):
        return OPrim.BRepPrimAPI_MakePrism(
            self.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.rib.extrude_lenght)),
        )
        
    def make_pattern(self,anz, wingspan,spacing):
        trans_rib=None
        ribs=self.rib.single
        for i in range(anz):
            trans_rib=OExs.translate_shp(self.rib.single,gp_Vec(0.0,wingspan,0.0))
            #ribs=OAlgo.BRepAlgoAPI_Fuse(self.rib.single,trans_rib).Shape()
            ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            wingspan=wingspan-spacing
        self.ribs.shape= ribs
    
    def rotate(shape, axis, angle):
        """Rotate a shape around an axis, with a given angle.
        @param shape : the shape to rotate
        @point : the origin of the axis
        @vector : the axis direction
        @angle : the value of the rotation
        @return: the rotated shape.
        """
        #assert_shape_not_null(shape)
        #if unite == "deg":  # convert angle to radians
        angle = radians(angle)
        trns = gp_Trsf()
        trns.SetRotation(axis, angle)
        brep_trns = OBuilder.BRepBuilderAPI_Transform(shape, trns, False)
        brep_trns.Build()
        shp = brep_trns.Shape()
        return shp
    