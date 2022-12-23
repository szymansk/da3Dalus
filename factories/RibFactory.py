from inspect import _void
from turtle import width
from typing import Any
from unittest import result
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo
import OCC.Core.gp as Ogp
from math import *
from _alt.abmasse import *
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
import logging
from Extra.BooleanOperationsForLists import *
from _alt.shape_verschieben import *



class RibFactory:
    
    def __init__(self) -> None:
        self.rib:Rib= Rib()
        self.md=ConstructionStepsViewer.instance()
              
    #TODO where does height, thikness, extrude come frome?
    def create_rib_grid(self, spacing, thikness,xdiff, ydiff, zdiff,type:str="x"):
        logging.debug("Creating rid grid")
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
        logging.debug("Pattern will start at position: " + str(position))
        for i in range(q):
            trans_rib=OExs.translate_shp(self.rib.rib.Shape(),gp_Vec(0.0,position,0.0))
            if i==0:
                ribs= trans_rib
            else:
                ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            position=position + spacing
        self.rib.ribs= ribs
        self.md.display_in_origin(ribs, logging.NOTSET)
    
    def calculate_ribs_quantity(self) ->int:
        x= int(2*(self.rib.ydiff/self.rib.spacing))
        return (x)
    
    def create_star_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8):
        logging.debug("Creating star ribs")
        heavy_ribs=self.create_heavy_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8)
        hardware_cutout_box= self.hardware_box(fuselage_height, fuselage_lenght, fuselage_width, factor_length, factor)
        heavy_ribs=self.cutout_from_ribs(hardware_cutout_box)
        light_ribs= self.create_light_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8)
        star=self.rib.ribs= OAlgo.BRepAlgoAPI_Fuse(heavy_ribs,light_ribs).Shape()
        self.create_reinforcement_tunnel_out()
        star= self.rib.ribs=self.fuse_reinforcement_tunnel_out()
        return star
    
    def create_heavy_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8, quantity=2):
        logging.debug("Creating heavy ribs")
        big_rib=self.create_big_rib(fuselage_lenght, fuselage_width, fuselage_height, thikness)
        big_rib_pattern=self.rib.ribs=self.circle_pattern(big_rib, "big rib",quantity)
        return big_rib_pattern
    
    def create_light_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length=0.4, factor=0.8):
        logging.debug("Creating light ribs: first Heavy ribs and then cutout Cylinder")
        heavy_ribs=self.create_heavy_ribs(fuselage_lenght, fuselage_width, fuselage_height, thikness,factor_length, factor, 4)
        cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*factor)/2,100).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90, "Cylinder")
        return self.cutout_from_ribs(cylinder)   
    
    '''
    def create_thin_ribs(self,fuselage_lenght, fuselage_width, fuselage_height, thikness, factor=0.8):
        logging.debug("Creating thin ribs")
        big_rib=self.create_big_rib(fuselage_lenght, fuselage_width, fuselage_height, thikness)
        big_rib_pattern=self.circle_pattern(self.rib.rib)
        cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*factor)/2,100).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.cutout_from_ribs(cylinder)
    '''

    def create_big_rib(self, fuselage_lenght, fuselage_width, fuselage_height, thikness):
        logging.debug("Creating big rib")
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
        logging.debug("Creating circle pattern")
        d_angle= 180/quantity
        for i in range(quantity):     
            angle=i*d_angle
            new_shape= self.rotate_shape(shape, Ogp.gp_OX(), angle,shape_name)
            if i==0:
                patern=new_shape
            else:
                patern=OAlgo.BRepAlgoAPI_Fuse(patern,new_shape).Shape()
                logging.debug("Fusing rib to pattern")
        return patern
    
    def cutout_from_ribs(self, hardware_box)->OTopo.TopoDS_Shape:
        logging.debug("Cutting from ribs")
        return OAlgo.BRepAlgoAPI_Cut(self.rib.ribs, hardware_box).Shape()
    
    def cut_rib_as_fuselage(self, fuselage, ribs)->OTopo.TopoDS_Shape:
        logging.debug("Cutting Ribs to Fuselage form")
        return OAlgo.BRepAlgoAPI_Common(fuselage, ribs).Shape()
    
    def common_to_ribs(self, shape)->OTopo.TopoDS_Shape:
        logging.debug("Common ribs to Shape form")
        self.rib.compound["shaped_rib"]=OAlgo.BRepAlgoAPI_Common(self.rib.compound[next(reversed(self.rib.compound))], shape).Shape()
        return self.rib.compound["shaped_rib"]
        
    def cut_out_wing(self, wings)->OTopo.TopoDS_Shape:
        logging.debug("Cutting wings from ribs")
        return OAlgo.BRepAlgoAPI_Cut(self.rib.ribs, wings).Shape()
    
    def hardware_box(self, fuselage_height, fuselage_lenght, fuselage_width, factor_length=0.4, factor=0.8 )->OTopo.TopoDS_Shape:
        logging.debug("Creating hardware box")
        hardware_box_height=fuselage_height*(factor/2)+ self.rib.thikness
        hardware_box_lenght= fuselage_lenght*factor_length
        hardware_box_widht= fuselage_width*factor
        hardware_box= OPrim.BRepPrimAPI_MakeBox(hardware_box_lenght, hardware_box_widht, hardware_box_height).Shape()
        moved_hardware_box= OExs.translate_shp(hardware_box,Ogp.gp_Vec(0,-hardware_box_widht/2, -hardware_box_height+ self.rib.thikness))
        return moved_hardware_box

    def move_rippen(self, x, y,z ):
        logstr= "Moving ribs to x:" + str(x) + " y:" + str(y) + " z:" + str(z)
        logging.debug(logstr)
        trafo = TGeo.CTiglTransformation()
        trafo.add_translation(x,y,z)
        self.rib.ribs=trafo.transform(self.rib.ribs)
        
    def rotate(self, axis, angle):
        logstr= "Rotating ribs over Y-axis: " + angle + "°"
        logging.debug(logstr)
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
        logging.debug(logstr)
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
        logging.debug("Fusing reinforcement tunnel in")
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(radius,fuselage_length).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.rib.reinforcement_tunnel_in=cylinder
        return cylinder
    
    def create_reinforcement_tunnel_out(self, radius=0.3, fuselage_length=100)->OTopo.TopoDS_Shape:
        #TODO variable radius of outer cylinder
        logging.debug("Creating reinforcement tunnel out")
        cylinder= OPrim.BRepPrimAPI_MakeCylinder(radius,fuselage_length).Shape()
        cylinder= self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.rib.reinforcement_tunnel_out=cylinder
        return cylinder
    
    def fuse_reinforcement_tunnel_out(self)->OTopo.TopoDS_Shape:
        logging.debug("Fusing reinforcement tunnel out")
        fused= OAlgo.BRepAlgoAPI_Fuse(self.rib.ribs,self.rib.reinforcement_tunnel_out).Shape()
        return fused
    
    def create_tunnels_for_carbon_reinforcemnt(self, radius, y_max,y_min,z_max,z_min):
        '''
        Creates four Cylinders with a given radius and positions them in a Ractangular pattern with the given kordinates 
        '''
        logstr= f"Tunnel for Carbon Reinforcements in kordinates {x_pos=:.3f} {y_max=:.3f} {y_min=:.3f} {z_max=:.3f} {z_min=:.3f}"
        logging.debug(logstr)
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
        self.md.display_this_shape(tunnels, severity=logging.NOTSET, logstr)
        return tunnels
    
    def create_quadrat_rib(self, rib_width, lenght, height, y_max,y_min,z_max,z_min):
        prim=[]
        compound=[]
        lenght*=1.2
        height*=1.2
        prim.append(OPrim.BRepPrimAPI_MakeBox(lenght, rib_width, height).Shape())
        prim.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0,-rib_width/2,-self.shape_height/2)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0.0,y_max,0.0)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0.0,y_min,0.0)))
        #berechnen der top stelle des flügels
        hor_rib= rotate_shape(prim[-1], Ogp.gp_OX(), 90)
        compound.append(OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,z_max)))
        compound.append(OExs.translate_shp(hor_rib,Ogp.gp_Vec(0.0,0.0,z_min)))
        interim_rib=fuse_list_of_shapes(compound)
        logstr= f"Quadrat ribs: x_pos=0 y_max={y_max:.3f} y_min={y_min:.3f} z_max={z_max:.3f} z_min={z_min:.3f}"
        self.md.display_this_shape(interim_rib, severity=logging.NOTSET, logstr)
        logging.debug(logstr)
        return interim_rib
    
    def create_cylinder_reinforcemnt(self, radius,lenght,y_max,y_min,z_max,z_min ):
        x_pos=0.0
        logstr= f"Tunnel for Carbon Reinforcements {x_pos=:.3f} {y_max=:.3f} {y_min=:.3f} {z_max=:.3f} {z_min=:.3f}"
        logging.debug(logstr)
        prim=[]
        compound=[]
        prim.append(OPrim.BRepPrimAPI_MakeCylinder(radius,lenght).Shape())
        prim.append(rotate_shape(prim[-1], Ogp.gp_OY(), 90))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_max,z_max)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_max,z_min)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_min,z_min)))
        compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(x_pos,y_min,z_max)))
        interim_cylinders= fuse_list_of_shapes(compound)
        self.md.display_this_shape(interim_cylinders, severity=logging.NOTSET)
        return interim_cylinders

    def create_rib_weight_reduction_recces(self, radius=0.01, lenght=0.2, distance=0.1):
        prim=[]
        prim.append(OPrim.BRepPrimAPI_MakeCylinder(radius,lenght).Shape())
        prim.append(rotate_shape(prim[-1], Ogp.gp_OX(), 90))
        recces=self.create_linear_pattern(prim[-1], 8, distance)
        self.md.display_this_shape(recces, severity=logging.NOTSET)
        return recces

    def create_linear_pattern(self, shape, quantity, distance):
        pattern=shape
        logstr= f"Linear pattern of {quantity} x {distance} meters"
        logging.debug(logstr)
        list=[]
        for i in range(1,quantity):
            x= i*distance
            list.append(OExs.translate_shp(shape,Ogp.gp_Vec(x,0.0,0.0)))
        pattern=fuse_list_of_shapes(list, logstr)
        return pattern

    def create_wing_reinforcement_ribs(self):
        prim = []
        compound = []
        xmin = dimensions_mainwing("x_min")
        zmax = dimensions_mainwing("z_max")
        length, width, height = get_mainwing_dimensions()
        box_length, box_width, box_height = length / 2, 0.0004, 2 * height
        prim.append(OPrim.BRepPrimAPI_MakeBox(box_length, box_width, box_height).Shape())
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(0, -box_width / 2, -box_height / 2)))
        prim.append(OExs.rotate_shape(prim[-1], Ogp.gp_OY(), 60))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(xmin - 0.002, 0, zmax - 0.01)))
        f_length, f_width, f_height = get_fuselage_dimensions()
        rib_width = f_width * 0.7
        distance = rib_width / 5
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(0, -distance * 2, 0)))
        for i in range(0,5):
            compound.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0,distance*i,0)))
        compound.append(fuse_list_of_shapes(compound))
        box = OPrim.BRepPrimAPI_MakeBox(f_length, f_width, f_height).Shape()
        moved_box= OExs.translate_shp(box,Ogp.gp_Vec(0,-f_width/2, zmax ))
        compound.append(OAlgo.BRepAlgoAPI_Cut(compound[-1],moved_box).Shape())
        self.md.display_cut(compound[-1], compound[-2], moved_box, logging.NOTSET)
        return compound[-1]
    
   
    def create_sharp_ribs(self,rib_width=0.0004, factor=0.3, radius=0.004):
        prim = []
        compound = []
        y_max = dimensions_fuselage["y_max"] * factor
        y_min = -y_max
        z_max = dimensions_fuselage["z_max"] * factor
        z_min = dimensions_mainwing["z_max"] + radius
        lenght = dimensions_fuselage["lenght"]
        width = dimensions_fuselage["width"]
        prim.append(self.create_quadrat_rib(rib_width, y_max, y_min, z_max, z_min))
        prim.append(self.create_cylinder_reinforcemnt(radius, lenght, y_max, y_min, z_max, z_min))
        reduktion_radius = ((z_max - z_min) * 0.8) / 2
        reduktion_zpos = ((z_max - z_min) / 2) - reduktion_radius + (rib_width / 2)
        logstr = f"y_max= {y_max:.4f} y_min {y_min:.4f} z_max= {z_max:.4f} z_min= {z_min:.4f} radius= {reduktion_radius:.4f} z_pos= {reduktion_zpos:.5f}"
        logging.debug(logstr)
        prim.append(self.create_rib_weight_reduction_recces(reduktion_radius, 0.1))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(reduktion_radius * 2, width / 2, reduktion_zpos)))
        compound.append(OAlgo.BRepAlgoAPI_Cut(prim[0],prim[-1]).Shape())
        self.md.display_cut(compound[-1], prim[0], prim[-1], logging.NOTSET, logstr)
        reduktion_radius=y_max*0.7
        prim.append(self.create_rib_weight_reduction_recces(reduktion_radius, 0.1))
        prim.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(reduktion_radius*2,self.fuselage_widht/2,0)))
        prim.append(OExs.rotate_shape(prim[-1],Ogp.gp_OX(), 90))
        compound.append(OAlgo.BRepAlgoAPI_Cut(compound[-1],prim[-1]).Shape())
        self.md.display_cut(compound[-1], compound[-2], prim[-1], logging.NOTSET, "Ribs with vertikal cutout")
        prim.append(self.create_wing_reinforcement_ribs())
        compound.append(OAlgo.BRepAlgoAPI_Fuse(compound[-1],prim[-1]).Shape())
        self.md.display_fuse(compound[-1], compound[-2], prim[-1], logging.NOTSET)
        compound.append(OAlgo.BRepAlgoAPI_Fuse(compound[-1],prim[1]).Shape())
        logging.debug("Fused ribs and cylinders")
        self.md.display_fuse(compound[-1], compound[-2], prim[1], logging.NOTSET, "Fused ribs and cylinders")
        self.rib.compound["sharp ribs"]= compound[-1]
        return compound[-1]

