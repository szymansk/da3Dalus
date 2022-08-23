from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
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
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display
from parts.Airplane import Airplane
from parts.Fuselage import Fuselage
from factories.RibFactory import RibFactory
from factories.WingFactory import WingFactory
from factories.FuselageFactory import *
from abmasse import *

class AirplaneFactory:
    def __init__(self, tigl_handle, wing_thikness,rib_spacing,rib_thikness) -> None:
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.airplane: Airplane= Airplane()
        self.wing_factory: WingFactory= WingFactory(tigl_handle)
        self.fuselage_factory: FuselageFactory= FuselageFactory(tigl_handle)
        self.rib_factory: RibFactory= RibFactory()
        self.wing_thikness= wing_thikness
        self.rib_spacing= rib_spacing
        self.rib_thikness= rib_thikness
    

    def cpacs_einlesen(self,filename):
        #self.filename=filename
        tixi_h = tixi3wrapper.Tixi3()
        tigl_h = tigl3wrapper.Tigl3()
        tixi_h.open(filename)
        tigl_h.open(tixi_h, "")

        return tixi_h, tigl_h
    
    def create_airplane(self):
        self.create_right_mainwing()
        self.create_left_mainwing()
        self.create_right_h_tailwing()
        self.create_left_h_tailwing()
        self.create_v_tailwing()
        self.create_fuselage()
        
    def create_wing(self,nr,name):
        #wing_factory= WingFactory(tigl_h)
        print("----Creating", name)
        self.wing_factory.create_wing_shape(nr)
        self.wing_factory.create_holow_wing(self.wing_thikness)
        #self.wing_factory.create_rib_grid(self.rib_spacing,self.wing_thikness)
        #self.wing_factory.move_rippen()
        self.rib_factory.create_rib_grid(self.rib_spacing,self.wing_thikness,self.wing_factory.wing.xdiff,self.wing_factory.wing.ydiff, self.wing_factory.wing.zdiff)
        self.rib_factory.move_rippen(self.wing_factory.wing.xmin,self.wing_factory.wing.ymin,self.wing_factory.wing.zmin)
        self.wing_factory.fuse_ribs(self.rib_factory.rib.ribs)
        self.wing_factory.export_stl(name)
    
    def create_right_mainwing(self):
        self.create_wing(1,"right_mainwing.stl")
        self.airplane.set_right_mainwing(self.wing_factory.wing.with_ribs)
        
    def create_left_mainwing(self):
        '''
        Creates a mirrored shape of the "rightwing" in the factory, must be called after create_right_wing
        '''
        self.wing_factory.create_mirrored_wing()
        self.wing_factory.export_stl("left_mainwing.stl", True)
        self.airplane.set_left_mainwing(self.wing_factory.wing.mirrored_shape)
    
    def create_right_h_tailwing(self):
        self.create_wing(2, "right_h_tailwing.stl")
        self.airplane.set_right_tailwing(self.wing_factory.wing.with_ribs)
    
    def create_left_h_tailwing(self):
        self.wing_factory.create_mirrored_wing()
        self.wing_factory.export_stl("left_h_tailwing.stl",True)
        self.airplane.set_left_tailwing(self.wing_factory.wing.mirrored_shape)
    
    def create_v_tailwing(self):
        self.create_wing(3, "v_tailwing")
        self.wing_factory.export_stl("v_tailwing.stl")
        self.airplane.set_v_tailwing(self.wing_factory.wing.with_ribs)
        
    def fuse_mainwings(self):
        if self.airplane.wings.get("right_mainwing") != None and self.airplane.wings.get("left_mainwing") != None:
            print("Fusing mainwings")
            self.airplane.mainwings=OAlgo.BRepAlgoAPI_Fuse(self.airplane.wings.get("right_mainwing"), self.airplane.wings.get("left_mainwing")).Shape()
        else:
            print("Fusing mainwings not posible")
        
    def fuse_tailwings(self):
        if self.airplane.wings.get("right_h_tailwing") !=None and self.airplane.wings.get("left_h_tailwing") !=None: 
            print("Fusing tailwings")     
            h_tailwings=OAlgo.BRepAlgoAPI_Fuse(self.airplane.wings.get("right_h_tailwing"), self.airplane.wings.get("left_h_tailwing")).Shape()
            #FIXME Add Vertikale Tailwing
            self.airplane.tailwings=OAlgo.BRepAlgoAPI_Fuse(h_tailwings, self.airplane.wings.get("v_tailwing")).Shape()
            #self.airplane.tailwings=h_tailwings
        else:
            print("Fusing tailwings not posible")
    
    def fuse_all_wings(self):
        self.fuse_mainwings()
        self.fuse_tailwings()
        print("Fusing allwings") 
        if self.airplane.tailwings != None and self.airplane.mainwings!= None:
            self.airplane.allwings=OAlgo.BRepAlgoAPI_Fuse(self.airplane.tailwings, self.airplane.mainwings).Shape()
        else:
            print("Fusing allwing notposible")
    
    def create_fuselage(self):
        self.fuselage_factory.create_fuselage_shape(1)
        self.fuselage_factory.create_holow_fuselage(self.wing_thikness)
        #Swap x and z because we rotate 90 aorund y axis
        self.rib_factory.create_rib_grid(self.rib_spacing,self.wing_thikness,self.fuselage_factory.fuselage.zdiff,self.fuselage_factory.fuselage.ydiff, self.fuselage_factory.fuselage.xdiff)
        self.rib_factory.rotate(gp_OY(),90)
        #self.rib_factory.move_rippen(self.fuselage_factory.fuselage.xmin,self.fuselage_factory.fuselage.ymin,self.fuselage_factory.fuselage.zmin)
        self.rib_factory.move_rippen(0,self.fuselage_factory.fuselage.ymin*1.5,-self.fuselage_factory.fuselage.zmin*1.5)
        self.fuselage_factory.fuse_ribs(self.rib_factory.rib.ribs)
        self.airplane.set_fuselage(self.fuselage_factory.fuselage.with_ribs)
        self.fuselage_factory.export_stl("fuselage.stl")
        