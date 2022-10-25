from __future__ import print_function
import enum
import math 
from turtle import Shape
from unicodedata import mirrored, name


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories
import tigl3.tigl3wrapper as wr

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
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from stl_exporter.Ausgabeservice import write_stl_file2
from _alt.abmasse import *
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
import Extra.tigl_extractor as tigl_extractor
import Extra.patterns as pat
import dimensions.ShapeDimensions as PDim

class RuderFactory:
    def __init__(self,tigl_handle,wingNr):
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates=PDim.ShapeDimensions(self.wing_shape)
        self.shape:OTopo.TopoDS_Shape=None
        self.shapes:list=[]
        self.m= myDisplay.instance()
        logging.info(f"{self.wing_koordinates=}")

    def create_ruder_option1(self,factor=(1/3)):
        logging.info(f"Creating ribs option1")
        ribs=[]
        logging.info(f" segment Count: {self.wing.get_segment_count()}")
        
    def get_shape(self):
        return self.shape
        
    def get_create_trailing_edge_shape(self):
        wing1=self.wing
        compseg:TConfig.CCPACSWingComponentSegment=wing1.get_component_segment(1)
        control_surface:TConfig.CCPACSControlSurfaces=compseg.get_control_surfaces()
        trailing_edge_devices:TConfig.CCPACSTrailingEdgeDevices=control_surface.get_trailing_edge_devices()
        count=trailing_edge_devices.get_trailing_edge_device_count()
        logging.info(f"{count=}")
        trailing_edge_device:TConfig.CCPACSTrailingEdgeDevice=trailing_edge_devices.get_trailing_edge_device(1)
        loft:TGeo.CNamedShape=trailing_edge_device.get_loft()
        shape=loft.shape()
        self.m.display_this_shape(shape)
        return shape

    def get_trailing_edge_cutOut(self,offset=0.002):
        shape=self.get_create_trailing_edge_shape()
        #self.m.display_in_origin(shape)
        #offt:OOff.BRepOffsetAPI_MakeOffsetShape=OOff.BRepOffsetAPI_MakeOffsetShape(shape, offset,0.000001)
        #offt.Build()
        #bnd_box=offt.Shape()
        #print(type(bnd_box))
        wing1=self.wing
        compseg:TConfig.CCPACSWingComponentSegment=wing1.get_component_segment(1)
        control_surface:TConfig.CCPACSControlSurfaces=compseg.get_control_surfaces()
        trailing_edge_devices:TConfig.CCPACSTrailingEdgeDevices=control_surface.get_trailing_edge_devices()
        count=trailing_edge_devices.get_trailing_edge_device_count()
        trailing_edge_device:TConfig.CCPACSTrailingEdgeDevice=trailing_edge_devices.get_trailing_edge_device(1)
        ccutout:TGeo.CNamedShape=trailing_edge_device.get_cut_out_shape()
        cutout=ccutout.shape()
        self.m.display_this_shape(cutout)
        return cutout
        

if __name__ == "__main__":
    #tigl_handle= tigl_extractor.get_tigl_handler("aircombat_v7")
    tigl_handle= tigl_extractor.get_tigl_handler("simple_aircraft_v2")
    m=myDisplay.instance(True,6)
    a=RuderFactory(tigl_handle,1)
    cutout=a.get_trailing_edge_cutOut(0.002)
    #m.display_in_origin(a.wing_shape,"",True)
    wing_cut=OAlgo.BRepAlgoAPI_Cut(a.wing_shape,cutout).Shape()
    #m.display_this_shape(wing_cut)
    m.display_cut(wing_cut,a.wing_shape,cutout)
    #m.display_in_origin(a.get_trailing_edge_cutOut(),"",True)
    m.display_in_origin(wing_cut,"",True)
    m.display_in_origin(a.get_create_trailing_edge_shape())
    #a._create_trailing_edge()
    a.m.start()
    
