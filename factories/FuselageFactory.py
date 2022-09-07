from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored

import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories
import tigl3.boolean_ops as TBoo

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import time
from OCC.Display.SimpleGui import init_display

from factories.RibFactory import *
from parts.Wing import *
from parts.Fuselage import *
from mydisplay import *

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *
import logging

class FuselageFactory:
    def __init__(self, tigl_handle) -> None:
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.fuselage:Fuselage= Fuselage()
    
    def create_fuselage_shape(self, fuse_nr):
        fuselage: TConfig.CCPACSFuselage= self.cpacs_configuration.get_fuselage(fuse_nr)
        logstr= "Creating Fuselage Shape: " + fuselage.get_name()
        self.fuselage.loft: TGeo.CNamedShape= fuselage.get_loft()
        self.fuselage.shape: OTopo.TopoDS_Shape=self.fuselage.loft.shape()
        self.fuselage.calculate_koordinates()
        self.fuselage.calculate_outter_dimensions()
        logging.info(self.fuselage.__str__())
        
    def create_holow_fuselage(self, thickness:float, fuselage=None):
        logstr= "Hollowing Fuselage: thickness=" + str(thickness)
        logging.info(logstr)
        if fuselage== None:
            fuselage=self.fuselage.cutted
        #self.fuselage.hollow= create_hollowedsolid(self.fuselage.shape ,thickness)
        facesToRemove = TopTools_ListOfShape()
        hollowed= OOff.BRepOffsetAPI_MakeThickSolid(fuselage, facesToRemove, thickness, 0.001).Shape()
        return hollowed
                
    def add_ribs(self, ribs, name) -> OTopo.TopoDS_Shape:
        logstr= "Adding " + name + " to fuselage "
        logging.info(logstr)           
        comon= self.common_shape(ribs, name)
        fused= self.fuse_shape(comon, name)
        return fused
      
    def fuse_shape(self, shape, name= "Shape", fuselage= None) -> OTopo.TopoDS_Shape:
        logstr= "Fusing: " + name + " to Fuselage ---- Wait"
        logging.info(logstr)
        start= time.time()
        if fuselage == None:
            fuselage=self.fuselage.hollow
        #fuses given shape to the fuselage
        fused_fuselage= OAlgo.BRepAlgoAPI_Fuse(fuselage,shape).Shape()
        end= time.time()
        dif= end-start
        logging.info("Fusing: End  ---- Time=" + str(dif) + "seconds")
        return fused_fuselage
    
    def common_shape(self, shape, name="shape", fuselage= None)-> OTopo.TopoDS_Shape:
        logstr= "Common: " + name + " and Fuselage"
        logging.info(logstr)
        start= time.time()
        if fuselage == None:
            fuselage=self.fuselage.shape
        #cuts the a given shape to the shape of the wing
        common = OAlgo.BRepAlgoAPI_Common(shape,fuselage).Shape()
        end= time.time()
        dif= end-start
        logging.info("Common: End  ---- Time: " + str(dif) + "seconds")
        return common
         
    def cut_out_shape(self,shape, name= "shape", fuselage=None)-> OTopo.TopoDS_Shape:
        logstr= "Cutting: " + name + " from Fuselage"
        logging.info(logstr)
        #display_this_shape(wings_shape)
        #named_wings_shape= TGeo.CNamedShape(wings_shape, "Wing_cutout")
        #cutter= TBoo.CCutShape(self.fuselage.shape, named_wings_shape)
        if fuselage == None:
            cutted_fuselage:TopoDS_Shape= OAlgo.BRepAlgoAPI_Cut(self.fuselage.shape,shape).Shape()
        else:
            cutted_fuselage:TopoDS_Shape= OAlgo.BRepAlgoAPI_Cut(fuselage,shape).Shape()
        return cutted_fuselage
        
    def export_stl(self, name):
        write_stl_file2(self.fuselage.with_ribs, name)
        