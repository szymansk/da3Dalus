import enum
from math import radians
from turtle import Shape
from unicodedata import mirrored, name



import tigl3.configuration as TConfig
import tigl3.curve_factories as TCur
import tigl3.exports as TExp
import tigl3.geometry as TGeo
import tigl3.surface_factories as TSur
import tigl3.boolean_ops as TBoo

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRepTools as OTools
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Extend.ShapeFactory as OExs
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
import Extra.tigl_extractor as tigl_extractor
import Extra.patterns as pat

class ShapeDimensions:
    def __init__(self,shape:OTopo.TopoDS_Shape):
        self.shape:OTopo.TopoDS_Shape= shape
        self.xmin,self.ymin,self.zmin,self.xmax,self.ymax,self.zmax= self._calc_koordinates(shape)
        self.lenght, self.width, self.height= self._calc_dimensions_from_Shape(shape)
        self.xmid, self.ymid, self.zmid= self._calc_mid_kordinates()
        self.points=self._calc_points()
        
    def _calc_koordinates(self,shape) :
        bbox = Bnd_Box()
        brepbndlib_Add(shape,bbox)
        xmin,ymin,zmin,xmax,ymax,zmax = bbox.Get()
        return xmin, ymin, zmin,xmax,ymax,zmax

    def _calc_dimensions(self,xmin,ymin,zmin,xmax,ymax,zmax):
        xdiff = xmax - xmin
        ydiff = ymax - ymin
        zdiff = zmax - zmin
        return xdiff,ydiff,zdiff

    def _calc_dimensions_from_Shape(self, shape):
        xmin, ymin, zmin,xmax,ymax,zmax=self._calc_koordinates(shape)
        xdiff,ydiff,zdiff= self._calc_dimensions(xmin, ymin, zmin,xmax,ymax,zmax)
        return xdiff, ydiff, zdiff

    def _calc_mid_kordinates(self):
        xmid= self.xmin + (self.lenght/2)
        ymid= self.ymin + (self.width/2)
        zmid= self.zmin + (self.height/2)
        return xmid, ymid, zmid
    
    def _calc_points(self) -> list:
        point0=Ogp.gp_Pnt(self.xmid,self.ymid,self.zmid)
        point1=Ogp.gp_Pnt(self.xmin,self.ymin,self.zmin)
        point2=Ogp.gp_Pnt(self.xmax,self.ymin,self.zmin)
        point3=Ogp.gp_Pnt(self.xmax,self.ymax,self.zmin)
        point4=Ogp.gp_Pnt(self.xmin,self.ymax,self.zmin)
        point5=Ogp.gp_Pnt(self.xmin,self.ymin,self.zmax)
        point6=Ogp.gp_Pnt(self.xmax,self.ymin,self.zmax)
        point7=Ogp.gp_Pnt(self.xmax,self.ymax,self.zmax)
        point8=Ogp.gp_Pnt(self.xmin,self.ymax,self.zmax)
        points=[point0,point1,point2,point3,point4,point5,point6,point7,point8]
        return points
    
    def get_xmin(self):
        return self.xmin
    
    def get_ymin(self):
        return self.ymin
    
    def get_zmin(self):
        return self.zmin
    
    def get_xmid(self):
        return self.xmid
    
    def get_ymid(self):
        return self.ymid
    
    def get_zmid(self):
        return self.zmid
    
    def get_xmax(self):
        return self.xmax
    
    def get_ymax(self):
        return self.ymax
    
    def get_zmax(self):
        return self.zmax

    def get_length(self):
        return self.lenght
    
    def get_width(self):
        return self.width
    
    def get_height(self):
        return self.height

    def get_point(self, index):
        return self.points[index]
    
    def get_points(self):
        return self.points
    
    def __str__(self):
        return f"{self.xmin=:.4f}, {self.ymin=:.4f}, {self.zmin=:.4f}, {self.xmid=:.4f}, {self.ymid=:.4f}, {self.zmid=:.4f}, {self.xmax=:.4f}, {self.ymax=:.4f}, {self.zmax=:.4f}, { self.lenght=:.4f}, {self.width=:.4f}, { self.height=:.4f}"

    def get_koordinates_on_achs(self, quantity):
        x_diff=self.get_length()/(quantity+1)
        x_list=[]
        for i in range(1,quantity+1):
            new_x=self.get_xmin()+(i*x_diff)
            
            x_list.append(new_x)
        logging.info(f"{x_list=}")
        return x_list

    def get_bounding_box_shape(self):
        return OPrim.BRepPrimAPI_MakeBox(self.points[1],self.lenght,self.width,self.height).Shape()

if __name__ == "__main__":
    m=myDisplay.instance(True)
    box=OPrim.BRepPrimAPI_MakeBox(3,4,5).Shape()
    moved_box=OExs.translate_shp(box,Ogp.gp_Vec(1,2,3))
    box_dimensions=ShapeDimensions(moved_box)
    m.display_in_origin(moved_box,True)
    for i,point in enumerate(box_dimensions.get_points()):
        m.display_point_in_origin(point,0.1,str(i))
    m.start()
    