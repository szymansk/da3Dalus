import logging
from operator import length_hint
from re import M
from turtle import position, shape
from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.Bnd as OBnd
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Extend.ShapeFactory as OExs
from Ausgabeservice import *
from Wand_erstellen import *
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from math import *
from OCC.Core.TopTools import TopTools_ListOfShape
from shape_verschieben import *

from abmasse import *
from mydisplay import myDisplay

class ShapeSlicer:
    def __init__(self, shape, quantity, part="fuselage"):
        self.parts_list=[]
        self.quantity:int= quantity
        self.cutout_front_box:OTopo.TopoDS_Shape= None
        self.cutout_back_box:OTopo.TopoDS_Shape= None
        self.total_lenght, self.total_widht, self.total_height= get_dimensions_from_Shape(shape)
        self.shape=self.orient_shape(shape)
        self.part_lenght:float=self.total_lenght/quantity
        self.position_front:float=0.0
        self.position_back:float=0.0
        self.m=myDisplay.instance()
        logstr= "Dividing shape in " + str(quantity) + "equal parts of lenght " + str(self.part_lenght)
        logging.info(logstr)
    
    def orient_shape(self,shape)-> OTopo.TopoDS_Shape:
        if self.total_lenght<self.total_widht:
            shape=rotate_shape(shape, Ogp.gp_OZ(), 90)
        self.total_lenght, self.total_widht, self.total_height= get_dimensions_from_Shape(shape)
        return shape
    
    def slice(self):
        for i in range(0,self.quantity):
            self.position_front=self.part_lenght*i
            self.cutout_front_box=OPrim.BRepPrimAPI_MakeBox(self.part_lenght, self.total_widht, self.total_height).Shape()
            self.cutout_front_box=OExs.translate_shp(self.cutout_front_box,Ogp.gp_Vec(self.position_front,(-self.total_widht/2), (-self.total_height/2)))
            part:OTopo.TopoDS_Shape=self.shape
            logstr= "Front Cutout " + str(i)
            self.m.display_this_shape(self.cutout_front_box,logstr)
            self.m.display_in_origin(self.cutout_front_box,True)
            part=OAlgo.BRepAlgoAPI_Common(part,self.cutout_front_box).Shape()
            logstr= "Part " + str(i)
            self.m.display_this_shape(part,logstr)
            self.parts_list.append(part)
    
    def slice2(self):
        for i in range(0,self.quantity):
            #self.position_front=self.part_lenght*i-self.part_lenght
            self.position_front=-self.total_lenght+self.part_lenght*i
            self.position_back=self.part_lenght*(i+1)
            self.cutout_front_box=OPrim.BRepPrimAPI_MakeBox(self.total_lenght, self.total_widht, self.total_height).Shape()
            self.cutout_front_box=OExs.translate_shp(self.cutout_front_box,Ogp.gp_Vec(0,(-self.total_widht/2), (-self.total_height/2)))
            self.cutout_back_box=OPrim.BRepPrimAPI_MakeBox(self.total_lenght, self.total_widht, self.total_height).Shape()
            self.cutout_back_box=OExs.translate_shp(self.cutout_back_box,Ogp.gp_Vec(0,(-self.total_widht/2), (-self.total_height/2)))

            part:OTopo.TopoDS_Shape=self.shape
            self.cutout_front_box=OExs.translate_shp(self.cutout_front_box,Ogp.gp_Vec(self.position_front,0, 0))
            logstr= "Front Cutout " + str(i)
            #self.m.display_this_shape(self.cutout_front_box,logstr)
            self.cutout_back_box=OExs.translate_shp(self.cutout_back_box,Ogp.gp_Vec(self.position_back,0, 0))
            logstr= "Back Cutout " + str(i)
            #self.m.display_this_shape(self.cutout_back_box,logstr)
            if i!=0:
                part=OAlgo.BRepAlgoAPI_Cut(part,self.cutout_front_box).Shape()
            part=OAlgo.BRepAlgoAPI_Cut(part,self.cutout_back_box).Shape()
            logstr= "Part " + str(i)
            self.m.display_this_shape(part,logstr)
            self.parts_list.append(part)
        
            
            
    
    
        

    
    