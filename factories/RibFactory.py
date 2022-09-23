from inspect import _void
from typing import Any
from unittest import result
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo
import OCC.Core.gp as Ogp
from math import *
from abmasse import *
from mydisplay import myDisplay
from parts.Rib import *
import logging
from BooleanOperationsForLists import *



class RibFactory:
    
    def __init__(self, shape) -> None:
        self.rib:Rib= Rib()
        self.md=myDisplay.instance()
        self.dimensions= 
        self.shape_length, self.shape_width, self.shape_height= get_dimensions_from_Shape(shape)
              
    #TODO where does height, thikness, extrude come frome?
    def create_rib_grid(self, spacing, thikness,xdiff, ydiff, zdiff,type:str="x"):
        logging.info("Creating rid grid")
       #self.rib.height=self.wing.xdiff
        self.rib.height=xdiff
        self.rib.thikness=thikness
        self.rib.set_profile(type)
        self.rib.extrude_lenght=zdiff
        self.rib.ydiff=ydiff
        self.rib.spacing=spacing
        self.extrude_profile(self.rib.extrude_lenght)
        self.make_pattern()
    
    #def create_rib(self,profile_height, profile_thikness, extrude_lenght):
     #   self.single = Ribs(profile_height, profile_thikness, extrude_lenght)

    def extrude_profile(self, extrude_lenght):
        self.rib.extrude_length=extrude_lenght
        self.rib.rib= OPrim.BRepPrimAPI_MakePrism(
            self.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.rib.extrude_lenght)),
        )
        
    def make_pattern(self):
        trans_rib=None
        ribs=None
        spacing=self.rib.spacing       
        q=self.calculate_ribs_quantity()
        #position=-(spacing*round(q/2))
        position= -self.rib.height
        logging.info("Pattern will start at position: " + str(position))
        for i in range(q):
            trans_rib=OExs.translate_shp(self.rib.rib.Shape(),gp_Vec(0.0,position,0.0))
            if i==0:
                ribs= trans_rib
            else:
                ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            position=position + spacing
        self.rib.ribs= ribs
    
    def calculate_ribs_quantity(self) ->int:
        x= int(2*(self.rib.ydiff/self.rib.spacing))
        return (x)
    
    def create_star_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8):
        logging.info("Creating star ribs")
        heavy_ribs=self.create_heavy_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8)
        hardware_cutout_box= self.hardware_box(fuselage_height, fuselage_lenght, fuselage_width, factor_length, factor)
        heavy_ribs=self.cutout_from_ribs(hardware_cutout_box)
        light_ribs= self.create_light_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8)
        star=self.rib.ribs= OAlgo.BRepAlgoAPI_Fuse(heavy_ribs,light_ribs).Shape()
        self.create_reinforcement_tunnel_out()
        star= self.rib.ribs=self.fuse_reinforcement_tunnel_out()
        return star
    
    def create_heavy_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8, quantity=2):
        logging.info("Creating heavy ribs")
        big_rib=self.create_big_rib(fuselage_lenght, fuselage_width, fuselage_height, thikness)
        big_rib_pattern=self.rib.ribs=self.circle_pattern(big_rib, "big rib",quantity)
        return big_rib_pattern
    
    def create_light_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8):
        logging.info("Creating light ribs: first Heavy ribs and then cutout Cylinder")       
        heavy_ribs=self.create_heavy_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length, factor, 4)
        cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*factor)/2,100).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90, "Cylinder")
        return self.cutout_from_ribs(cylinder)   
    
    '''
    def create_thin_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness, factor=0.8):
        logging.info("Creating thin ribs")
        big_rib=self.create_big_rib(fuselage_lenght, fuselage_width, fuselage_height, thikness)
        big_rib_pattern=self.circle_pattern(self.rib.rib)
        cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*factor)/2,100).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.cutout_from_ribs(cylinder)
    '''

    def create_big_rib(self, fuselage_lenght, fuselage_width, fuselage_height, thikness):
        logging.info("Creating big rib")
        box_height= max(fuselage_width, fuselage_height)
        self.rib.height=box_height
        self.rib.width= fuselage_width
        self.rib.thikness=thikness
        self.rib.extrude_lenght=fuselage_lenght
        box = OPrim.BRepPrimAPI_MakeBox(fuselage_lenght, thikness, box_height).Shape()
        big_rib= OExs.translate_shp(box,Ogp.gp_Vec(0,-thikness/2,-box_height/2))
        self.rib.rib= big_rib
        return big_rib
        
    def circle_pattern(self, shape, shape_name, quantity=2):
        logging.info("Creating circle pattern")
        d_angle= 180/quantity
        for i in range(quantity):     
            angle=i*d_angle
            new_shape= self.rotate_shape(shape, Ogp.gp_OX(), angle,shape_name)
            if i==0:
                patern=new_shape
            else:
                patern=OAlgo.BRepAlgoAPI_Fuse(patern,new_shape).Shape()
                logging.info("Fusing rib to pattern")
        return patern
    
    def cutout_from_ribs(self, hardware_box)->OTopo.TopoDS_Shape:
        logging.info("Cutting from ribs")
        return OAlgo.BRepAlgoAPI_Cut(self.rib.ribs, hardware_box).Shape()
    
    def cut_rib_as_fuselage(self, fuselage, ribs)->OTopo.TopoDS_Shape:
        logging.info("Cutting Ribs to Fuselage form")
        return OAlgo.BRepAlgoAPI_Common(fuselage, ribs).Shape()
        
    def cut_out_wing(self, wings)->OTopo.TopoDS_Shape:
        logging.info("Cutting wings from ribs")
        return OAlgo.BRepAlgoAPI_Cut(self.rib.ribs, wings).Shape()
    
    def hardware_box(self, fuselage_height, fuselage_lenght, fuselage_width, factor_length=0.4, factor=0.8 )->OTopo.TopoDS_Shape:
        logging.info("Creating hardware box")
        hardware_box_height=fuselage_height*(factor/2)+ self.rib.thikness
        hardware_box_lenght= fuselage_lenght*factor_length
        hardware_box_widht= fuselage_width*factor
        hardware_box= OPrim.BRepPrimAPI_MakeBox(hardware_box_lenght, hardware_box_widht, hardware_box_height).Shape()
        moved_hardware_box= OExs.translate_shp(hardware_box,Ogp.gp_Vec(0,-hardware_box_widht/2, -hardware_box_height+ self.rib.thikness))
        return moved_hardware_box

    def move_rippen(self, x, y,z ):
        logstr= "Moving ribs to x:" + str(x) + " y:" + str(y) + " z:" + str(z)
        logging.info(logstr)
        trafo = TGeo.CTiglTransformation()
        trafo.add_translation(x,y,z)
        self.rib.ribs=trafo.transform(self.rib.ribs)
        
    def rotate(self, axis, angle):
        logstr= "Rotating ribs over Y-axis: " + angle + "°"
        logging.info(logstr)
        angle = radians(angle)
        trns = gp_Trsf()
        trns.SetRotation(axis, angle)
        brep_trns = OBuilder.BRepBuilderAPI_Transform(self.rib.ribs, trns, False)
        brep_trns.Build()
        self.rib.ribs = brep_trns.Shape()
    
    def rotate_shape(self, shape, axis, angle, shape_name= "Shape")->OTopo.TopoDS_Shape:
        """Rotate a shape around an axis, with a given angle.
        @param shape : the shape to rotate
        @point : the origin of the axis
        @vector : the axis direction
        @angle : the value of the rotation
        @return: the rotated shape.
        """
        logstr= "Rotating " + shape_name +" over given axis: " + str(angle) + "°"
        logging.info(logstr)
        #assert_shape_not_null(shape)
        #if unite == "deg":  # convert angle to radians
        angle = radians(angle)
        trns = Ogp.gp_Trsf()
        trns.SetRotation(axis, angle)
        brep_trns = OBuilder.BRepBuilderAPI_Transform(shape, trns, False)
        brep_trns.Build()
        shp = brep_trns.Shape()
        return shp

    def create_reinforcement_tunnel_in(self, radius=0.2, fuselage_length=100)->OTopo.TopoDS_Shape:
        #TODO variable radius of inner cylinder
        logging.info("Fusing reinforcement tunnel in")
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(radius,fuselage_length).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.rib.reinforcement_tunnel_in=cylinder
        return cylinder
    
    def create_reinforcement_tunnel_out(self, radius=0.3, fuselage_length=100)->OTopo.TopoDS_Shape:
        #TODO variable radius of outer cylinder
        logging.info("Creating reinforcement tunnel out")
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(radius,fuselage_length).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.rib.reinforcement_tunnel_out=cylinder
        return cylinder
    
    def fuse_reinforcement_tunnel_out(self)->OTopo.TopoDS_Shape:
        logging.info("Fusing reinforcement tunnel out")
        fused= OAlgo.BRepAlgoAPI_Fuse(self.rib.ribs,self.rib.reinforcement_tunnel_out).Shape()
        return fused
    
    def create_tunnels_for_carbon_reinforcemnt(self, radius, y_max,y_min,z_max,z_min):
        '''
        Creates four Cylinders with a given radius and positions them in a Ractangular pattern with the given kordinates 
        '''
        logstr= f"Tunnel for Carbon Reinforcements in kordinates {x_pos=:.3f} {y_max=:.3f} {y_min=:.3f} {z_max=:.3f} {z_min=:.3f}"
        logging.info(logstr)
        prim= []
        compound=[]
        prim.append(OPrim.BRepPrimAPI_MakeCylinder(radius,self.shape_length).Shape())
        prim.append(self.rotate_shape(prim[-1], Ogp.gp_OY(), 90))
        x_pos=0
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_max,z_max)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_max,z_min)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_min,z_min)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_min,z_max)))
        tunnels=fuse_list_of_shapes(compound)
        self.md.display_this_shape(tunnels, logstr)
        return tunnels
    
    def create_quadrat_rib(self, rib_width, y_max,y_min,z_max,z_min):
        prim=[]
        compound=[]
        prim.append(OPrim.BRepPrimAPI_MakeBox(self.shape_length*1.2, rib_width, self.shape_height*1.2).Shape())
        prim.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0,-rib_width,-self.shape_height/2)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0.0,y_max,0.0)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0.0,y_min,0.0)))
        #berechnen der top stelle des flügels
        self.wing_zmax= get_koordinate(self.wing_shape, "zmax")
        hor_rib= rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_1=OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,z_max))
        hor_rib_2=OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,z_min))
        interim_rib=ver_rib_1
        interim_rib=OAlgo.BRepAlgoAPI_Fuse(interim_rib,ver_rib_2).Shape()
        interim_rib=OAlgo.BRepAlgoAPI_Fuse(interim_rib,hor_rib_1).Shape()
        quadrat_rib=OAlgo.BRepAlgoAPI_Fuse(interim_rib,hor_rib_2).Shape()
        logstr= f"Quadrat ribs: x_pos=0 y_max={y_max:.3f} y_min={y_min:.3f} z_max={z_max:.3f} z_min={z_min:.3f}"
        self.m.display_fuse(quadrat_rib, interim_rib, hor_rib_2, logstr)
        logging.info(logstr)
        return quadrat_rib
    

