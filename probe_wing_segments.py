from __future__ import print_function
import enum
from math import radians
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

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRepTools as OTools
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Extend.ShapeFactory as OExs
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo

from Dimensions.ShapeDimensions import ShapeDimensions
from _alt.abmasse import *
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *
import logging
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
import Extra.tigl_extractor as tigl_extractor

if __name__ == "__main__":
    m = ConstructionStepsViewer.instance(True)
    # tigl_handle= tigl_extractor.get_tigl_handler("simple_aircraft_v2")
    tigl_handle = tigl_extractor.get_tigl_handler("aircombat_v11")

    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)

    wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    positionigs: TConfig.CCPACSPositionings = wing.get_positionings()
    print(f"segments: {wing.get_segment_count()}")
    print(f"sections: {wing.get_section_count()}")

    compseg: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(1)
    control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
    trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
    trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(1)

    m.display_this_shape(trailing_edge_device, severity=logging.NOTSET)

    '''
    for i in range(1,wing.get_segment_count()+1):
        segment1:TConfig.CCPACSWingSegment= wing.get_segment(i)
        inner:OTopo.TopoDS_Shape=segment1.get_inner_closure()
        outter:OTopo.TopoDS_Shape=segment1.get_outer_closure()
        m.display_in_origin(inner)
        m.display_in_origin(outter)
    
        
        
    inner_dim=ShapeDimensions(inner)
    print(f"{inner_dim.get_length()=}")
      '''

    m.display_in_origin(wing_shape, logging.NOTSET, "", True)
    print("Done")

    m.start()
