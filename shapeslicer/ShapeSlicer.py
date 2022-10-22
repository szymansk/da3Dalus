import logging
from operator import length_hint
from os import name
from re import M
from turtle import position, shape, width
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
    def __init__(self, shape, quantity, name="", dev=False):
        self.parts_list=[]
        self.quantity:int= quantity
        self.cutout_front_box:OTopo.TopoDS_Shape= None
        self.cutout_back_box:OTopo.TopoDS_Shape= None
        self.total_lenght, self.total_widht, self.total_height= get_dimensions_from_Shape(shape)
        #self.shape=self.orient_shape(shape)
        self.shape=shape
        self.part_lenght:float=self.total_lenght/quantity
        self.position_front:float=0.0
        self.position_back:float=0.0
        self.m=myDisplay.instance(dev)
        self.name= name
        #logstr= "Dividing shape in " + str(quantity) + "equal parts of lenght " + str(self.part_lenght)
        logstr= "initiating slicer"
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
            logstr= "Part " + str(i)
            logging.info(logstr)
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
            #self.m.display_this_shape(part,logstr)
            self.parts_list.append(part)
        self.m.display_slice_x(self.parts_list, self.name)
    
    def slice_with_list_cut(self, list_of_pos):
        frontbox=None
        rearbox=None
        
        for i,front_pos in enumerate(list_of_pos):
            part=self.shape
            rearbox=OPrim.BRepPrimAPI_MakeBox(self.total_lenght, self.total_widht, self.total_height).Shape()
            rearbox= OExs.translate_shp(rearbox, Ogp.gp_Vec(list_of_pos[i],-self.total_widht/2, -self.total_height/2))
            part1=OAlgo.BRepAlgoAPI_Cut(part,rearbox).Shape()
            #self.m.display_cut(part1,part,rearbox)
            if i!= len(list_of_pos):
                lenght=list_of_pos[i]
                if i!= 0:
                    logging.info("Cutting frontbox " + str(i))
                    frontbox=OPrim.BRepPrimAPI_MakeBox(list_of_pos[i-1], self.total_widht, self.total_height).Shape()
                    frontbox= OExs.translate_shp(frontbox, Ogp.gp_Vec(0.0,-self.total_widht/2, -self.total_height/2))
                    beforecut=part1
                    part1=OAlgo.BRepAlgoAPI_Cut(beforecut,frontbox).Shape()
                    self.m.display_cut(part1, beforecut,frontbox)
                    #lenght=list_of_pos[i+1]-list_of_pos[i] 
                logstr= f"Part {i}  {lenght=}"
                logging.info(logstr)
            else:
                self.m.display_cut(part1,part,rearbox)
            #self.m.display_this_shape(part1)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)
    
    def slice_with_list_common(self, list_of_pos, direction="x"):
        frontbox=None
        
        for i,front_pos in enumerate(list_of_pos):
            part=self.shape
            if i==0:
                lenght=list_of_pos[i]
            else:
                lenght=list_of_pos[i]-list_of_pos[i-1]
            if i==0:
                frontbox=OPrim.BRepPrimAPI_MakeBox(lenght+0.01, self.total_widht, self.total_height).Shape()
                frontbox= OExs.translate_shp(frontbox, Ogp.gp_Vec(-0.01,-self.total_widht/2, -self.total_height/2))
            else:
                frontbox=OPrim.BRepPrimAPI_MakeBox(lenght, self.total_widht, self.total_height).Shape()
                frontbox= OExs.translate_shp(frontbox, Ogp.gp_Vec(list_of_pos[i-1],-self.total_widht/2, -self.total_height/2))
            part1=OAlgo.BRepAlgoAPI_Common(part,frontbox).Shape()
            self.m.display_common(part1,frontbox, part)
            logging.info("Coomon frontbox " + str(i))
            logstr= f"Part {i}  {lenght=}"
            logging.info(logstr)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)
    
    def slice_with_list_common_y(self, list_of_pos):
        frontbox=None
        xmin,ymin,zmin,xmax,ymax,zmax= get_koordinates(self.shape)
        for i,front_pos in enumerate(list_of_pos):
            part=self.shape
            if i==0:
                width=list_of_pos[i]
            else:
                width=list_of_pos[i]-list_of_pos[i-1]
            if i==0:
                frontbox=OPrim.BRepPrimAPI_MakeBox(self.total_lenght, width, self.total_height).Shape()
                frontbox= OExs.translate_shp(frontbox, Ogp.gp_Vec(xmin,0.0, zmin))
            else:
                frontbox=OPrim.BRepPrimAPI_MakeBox(self.total_lenght, width, self.total_height).Shape()
                frontbox= OExs.translate_shp(frontbox, Ogp.gp_Vec(xmin,list_of_pos[i-1], zmin))
            part1=OAlgo.BRepAlgoAPI_Common(part,frontbox).Shape()
            self.m.display_common(part1,frontbox, part)
            logging.info("Common frontbox " + str(i))
            logstr= f"Part {i}  {width=}"
            logging.info(logstr)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)
            
    def slicing_positions(self):
        result=[]
        before_wing = dimensions_mainwing.get("xmin")- 0.02
        after_wing = dimensions_mainwing["xmax"]+ 0.002
        mid_wing= (after_wing+ before_wing)/2
        result.append(before_wing/2)
        result.append(before_wing)
        result.append(after_wing)
        result.append(mid_wing)
        end_fuselage= dimensions_fuselage["xmax"]
        split_rear_fuselage=(end_fuselage+after_wing)/2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        return result
    
    def slicing_positions2(self,wing_shape, fuselage_shape):
        result=[]
        before_wing = get_koordinate(wing_shape, "xmin")- 0.0004
        after_wing =get_koordinate(wing_shape, "xmax")+ 0.0004
        mid_wing= (after_wing+ before_wing)/2
        result.append(before_wing/2)
        result.append(before_wing)
        result.append(mid_wing)
        result.append(after_wing)
        end_fuselage= get_koordinate(fuselage_shape, "xmax")
        split_rear_fuselage=(end_fuselage+after_wing)/2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        logging.info(result)
        logging.info(len(result))
        return result
    
    def slicing_postion_wing(self,wing_shape,factor=0.4):
        result=[]
        ymax=get_koordinate(wing_shape, "ymax")
        start_of_flap= ymax * factor+0.001
        half_of_start= start_of_flap/2
        rest= ymax-start_of_flap
        dif=rest/3
        p1=start_of_flap+dif
        p2=p1+dif
        result.append(half_of_start)
        result.append(start_of_flap)
        result.append(p1)
        result.append(p2)
        result.append(ymax)
        logging.info(result)
        logging.info(len(result))
        return result
        
        
    
        

    
    