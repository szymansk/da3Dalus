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
import Dimensions.ShapeDimensions as PDim

class ServoRecessFactory:
    def __init__(self,tigl_handle,wingNr,ruder_pos,servo_size):
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates=PDim.ShapeDimensions(self.wing_shape)
        self.shape:OTopo.TopoDS_Shape=None
        self.shapes:list=[]
        self.ruder_pos=ruder_pos
        self.servo_size=servo_size
        self.m= myDisplay.instance()
        logging.info(f"{self.wing_koordinates=}")

    def create_servoRecess_option1(self):
        box= OPrim.BRepPrimAPI_MakeBox(self.servo_size[1],self.servo_size[2],self.servo_size[3])
        pass

        
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

    def get_trailing_edge_cutOut(self,offset=0.02):
        wing1=self.wing
        compseg:TConfig.CCPACSWingComponentSegment=wing1.get_component_segment(1)
        control_surface:TConfig.CCPACSControlSurfaces=compseg.get_control_surfaces()
        trailing_edge_devices:TConfig.CCPACSTrailingEdgeDevices=control_surface.get_trailing_edge_devices()
        trailing_edge_device:TConfig.CCPACSTrailingEdgeDevice=trailing_edge_devices.get_trailing_edge_device(1)
        cutout_Nshape:TGeo.CNamedShape=trailing_edge_device.get_cut_out_shape()
        cutout_shape:OTopo.TopoDS_Shape=cutout_Nshape.shape()

        cutout_offset:OOff.BRepOffsetAPI_MakeOffsetShape=OOff.BRepOffsetAPI_MakeOffsetShape(cutout_shape, offset,0.000001).Shape()
        #self.m.display_in_origin(cutout_offset,"",True)
        #self.m.display_in_origin(self.wing_shape,"",True)
        print(f"Type of cutout_offset {type(cutout_offset)}")
        cutout_result= OAlgo.BRepAlgoAPI_Fuse(cutout_shape, cutout_offset).Shape()
        #self.m.display_fuse(cutout_result, cutout_offset, cutout_result)
        self.shape= cutout_offset
        return cutout_offset
        

    
