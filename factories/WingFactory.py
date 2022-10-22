from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as geo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import time
from OCC.Display.SimpleGui import init_display

from factories.RibFactory import *
from parts.Wing import *
from parts.Rib import *
from mydisplay import *

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *
import logging

class WingFactory:
    def __init__(self, tigl_handle) -> None:
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.wing_configuration= None
        self.wing:Wing= Wing()
        
        #self.rib_factory: RibFactory= RibFactory()
        
    def create_wing_shape(self, wing_nr):
        ''' Creates the wing shape out of the CPACS and stores it in the wing:Wing Objekt. Calls the funktions to calculate_koordinates and calculate_outter_dimensions '''
        #Get wing returns CPACSWing, XML Wing description
        self.wing_configuration: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(wing_nr)
        logstr= "Creating Wing Shape from: " + self.wing_configuration.get_name() 
        logging.info(logstr)                
        #Get_loft()-shape() creates a TigleShape out of the Wing
        #3D solid  with Tigl metadata
        wing_loft: TGeo.CNamedShape = self.wing_configuration.get_loft()
        self.wing.shape: OTopo.TopoDS_Shape = wing_loft.shape()
        claculate_mainwing_dimension(self.wing.shape) 
        self.create_mirrored_wing(False)
        self.fuse_mirrored_wing()
        self.wing.calculate_koordinates()
        self.wing.calculate_outter_dimensions()
        logging.info(self.wing.__str__())
    
    def create_holow_wing(self, thickness:float):
        '''Creates a new Hollows_wing shape with a given thikness and stores it in the wing:Wing Objekt'''
        logstr= "Hollowing Wing: " + self.wing_configuration.get_name()
        logging.info(logstr)            
        self.wing.hollow= create_hollowedsolid(self.wing.shape ,thickness)
        #facesToRemove = TopTools_ListOfShape()
        #self.wing.hollow= OOff.BRepOffsetAPI_MakeThickSolid(self.wing.shape, facesToRemove, 0.2, 0.001)
        
    def create_mirrored_wing(self, withribs=True):
        '''Creates a mirrored shape from the wing.with_ribs and stores it in the wing:Wing Objekt'''
        logstr= "Creating Mirrored Wing from: " + self.wing_configuration.get_name()
        logging.info(logstr)    
        if self.wing.has_mirrored_shape:
            # Set up the mirror
            aTrsf= Ogp.gp_Trsf()
            aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
            # Apply the mirror transformation
            if withribs==True:
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(self.wing.with_ribs, aTrsf)
                # Get the mirrored shape back out of the transformation and convert back to a wire
                self.wing.mirrored_with_ribs = aBRespTrsf.Shape()         
            else:
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(self.wing.shape, aTrsf)
                self.wing.mirrored_shape = aBRespTrsf.Shape()
                
    def fuse_mirrored_wing(self):
        logstr= "Fussing: " + self.wing_configuration.get_name()
        logging.info(logstr)    
        self.wing.complete= OAlgo.BRepAlgoAPI_Fuse(self.wing.shape,self.wing.mirrored_shape).Shape()
    
    def has_mirrored_shape(self) -> boolean:
        '''checks if the wing in the factory has a mirrored shape'''     
        mirorred_loft= self.wing_configuration.get_mirrored_loft()
        return mirorred_loft!= None
        
    def fuse_ribs(self, ribs):
        logging.info("Fusing: Ribs to Wing ---- Wait")
        start= time.time()
        #cuts the ribs to the shape of the wing
        #CommonSurface = OAlgo.BRepAlgoAPI_Common(self.wing.rib.ribs,self.wing.shape).Shape()
        CommonSurface = OAlgo.BRepAlgoAPI_Common(ribs,self.wing.shape).Shape()
        #fuses Wing and Ribs to 1 shape
        self.wing.with_ribs= OAlgo.BRepAlgoAPI_Fuse(self.wing.hollow,CommonSurface).Shape()
        end= time.time()
        dif= end-start
        logging.info("Fusing: End ---- Took " + str(dif) + " seconds")
    
    def get_solid_mainwings(self):
        pass
    
    '''
    def calculate_ribs_quantity(self) ->int:
        x= int(2*(self.wing.ydiff/self.wing.rib.spacing))
        print("Rib_quantity:" , x)
        
        return (x)
    
    #TODO where does height, thikness, extrude come frome?
    def create_rib_grid(self, spacing, thikness,type:str="x"):
       self.wing.rib.height=self.wing.xdiff
       self.wing.rib.thikness=thikness
       self.wing.rib.set_profile(type)
       self.wing.rib.extrude_lenght=self.wing.zdiff
       self.wing.rib.spacing=spacing
       self.extrude_profile(self.wing.rib.extrude_lenght)
       self.make_pattern()
        
    def extrude_profile(self, extrude_lenght):
        self.wing.rib.extrude_length=extrude_lenght
        self.wing.rib.rib= OPrim.BRepPrimAPI_MakePrism(
            self.wing.rib.profile,
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, self.wing.rib.extrude_lenght)),
        )
               
    def make_pattern(self):
        trans_rib=None
        ribs=self.wing.rib.rib.Shape()
        spacing=self.wing.rib.spacing       
        q=self.calculate_ribs_quantity()
        position=-(spacing*q/4)
        print("position:",position)
        for i in range(q):
            trans_rib=OExs.translate_shp(self.wing.rib.rib.Shape(),gp_Vec(0.0,position,0.0))
            #ribs=OAlgo.BRepAlgoAPI_Fuse(self.rib.single,trans_rib).Shape()
            ribs=OAlgo.BRepAlgoAPI_Fuse(ribs,trans_rib).Shape()
            position=position + spacing
        #ribs=move_rippen_neu(ribs,self.wing.xmin,self.wing.ymax,self.wing.zmin)
        self.wing.rib.ribs= ribs
    
    #def move_rippen(self,rippen_gesamt,xmin,ymin,zmin):
    def move_rippen(self):
        from tigl3.geometry import CTiglTransformation
        #help(CTiglTransformation)

        trafo = CTiglTransformation()
        trafo.add_translation(self.wing.xmin,self.wing.ymin,self.wing.zmin)
        self.wing.rib.ribs=trafo.transform(self.wing.rib.ribs)
    '''
    
    def export_stl(self, name, mirored=False):
        
        if mirored:
            write_stl_file2(self.wing.mirrored_shape, name)
        else:
            write_stl_file2(self.wing.with_ribs, name)
        logging.info("exporting .stl file")
        