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
from Airplane.ReinforcementPipeFactory import *
from Airplane.Wing.RuderFactory import RuderFactory

from factories.RibFactory import *
from Airplane.Wing.WingRibFactory import *
from parts.Wing import *
from parts.Rib import *
from Extra.mydisplay import *

from _alt.abmasse import *
from stl_exporter.Ausgabeservice import *
from _alt.Aussparungen import *
from _alt.Innenstruktur import *
from _alt.shape_verschieben import *
from _alt.Wand_erstellen import *
import logging

class WingFactory:
    def __init__(self, tigl_handle,wingNr) -> None:
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates=PDim.ShapeDimensions(self.wing_shape)
        self.shape:OTopo.TopoDS_Shape=None
        self.shapes:list=[]
        self.wing_rib_factory: WingRibFactory= WingRibFactory(tigl_handle,wingNr)
        self.reinforcement_pipe_factory: ReinforcementePipeFactory= ReinforcementePipeFactory(tigl_handle,wingNr)
        self.ruder_factory:RuderFactory= RuderFactory(tigl_handle,wingNr)
        self.m=myDisplay.instance()
    
    def create_wing_option1(self):
        internal_struktur=[]
        self.wing_rib_factory.create_ribs_option1(3)
        internal_struktur.append(self.wing_rib_factory.get_shape())
        
        self.reinforcement_pipe_factory.create_reinforcemente_pipe_option1(quantity=3, pipe_position=[0,1])
        internal_struktur.append(self.reinforcement_pipe_factory.get_shape())
        
        #Fuse internal Strukture
        self.shapes.append(fuse_list_of_shapes(internal_struktur))
        
        #Cut-internalt strukture out
        self.shapes.append(OAlgo.BRepAlgoAPI_Cut(self.wing_shape,self.shapes[-1]).Shape())
        self.m.display_cut(self.shapes[-1],self.wing_shape,self.shapes[-2])
        
        ruder=self.ruder_factory.get_trailing_edge_cutOut()
        self.shapes.append(OAlgo.BRepAlgoAPI_Cut(self.shapes[-1],ruder).Shape())
        self.m.display_cut(self.shapes[-1],self.shapes[-2],ruder)     
        
    
    def get_shape(self)-> OTopo.TopoDS_Shape:
        return self.shapes[-1]
        
    def _create_wing_shape(self, wing_nr):
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
    
    def _create_holow_wing(self, thickness:float):
        '''Creates a new Hollows_wing shape with a given thikness and stores it in the wing:Wing Objekt'''
        logstr= "Hollowing Wing: " + self.wing_configuration.get_name()
        logging.info(logstr)            
        self.wing.hollow= create_hollowedsolid(self.wing.shape ,thickness)
        #facesToRemove = TopTools_ListOfShape()
        #self.wing.hollow= OOff.BRepOffsetAPI_MakeThickSolid(self.wing.shape, facesToRemove, 0.2, 0.001)
        
    def mirrored_wing_shape(self, withribs=True):
        '''Creates a mirrored shape from the wing.with_ribs and stores it in the wing:Wing Objekt'''
        logstr= "Creating Mirrored Wing from: " + self.wing_configuration.get_name()
        logging.info(logstr)    
        if self.has_mirrored_shape():
            # Set up the mirror
            aTrsf= Ogp.gp_Trsf()
            aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
            # Apply the mirror transformation
            if withribs==True:
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(self.shape, aTrsf)
                # Get the mirrored shape back out of the transformation and convert back to a wire
                self.mirrored_shape = aBRespTrsf.Shape()         
            else:
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(self.shape, aTrsf)
                self.mirrored_shape = aBRespTrsf.Shape()
        return self.mirrored_shape
                
    def fuse_mirrored_wing(self):
        logstr= "Fussing: " + self.wing_configuration.get_name()
        logging.info(logstr)    
        self.shape= OAlgo.BRepAlgoAPI_Fuse(self.shape,self.mirrored_shape).Shape()
    
    def _has_mirrored_shape(self) -> boolean:
        '''checks if the wing in the factory has a mirrored shape'''     
        mirorred_loft= self.wing_configuration.get_mirrored_loft()
        return mirorred_loft!= None
        
    def _fuse_ribs(self, ribs):
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
    
    def export_stl(self, name, mirored=False):
        
        if mirored:
            write_stl_file2(self.wing.mirrored_shape, name)
        else:
            write_stl_file2(self.wing.with_ribs, name)
        logging.info("exporting .stl file")
    
if __name__ == "__main__":
    #tigl_handle= tigl_extractor.get_tigl_handler("aircombat_v7")
    tigl_handle= Extra.tigl_extractor.get_tigl_handler("simple_aircraft_v2")
    m=myDisplay.instance(True,7)
    a=WingFactory(tigl_handle,1)
    a.create_wing_option1()
    m.display_in_origin(a.shape)
    m.display_in_origin(a.wing_shape,"",True)
    m.start()