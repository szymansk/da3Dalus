from __future__ import print_function

import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
from OCC.Core.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class RuderFactory:
    def __init__(self, tigl_handle, wingNr):
        logging.info(f"Initilizin Ruder Factory")
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        print(f"Wing count: {self.cpacs_configuration.get_wing_count()}")
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)
        self.namedshape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list = []
        self.m = myDisplay.instance()

    def create_ruder_option1(self, factor_ruderarm_pos) -> TGeo.CNamedShape:
        """
        Creates the Ruder with the ruderarm at the given position
        :param factor_ruderarm_pos:
        :return:
        """
        logging.info(f"Creating ribs option1")
        logging.info(f"Segment Count: {self.wing.get_segment_count()}")
        # TODO: Implementaions of create ruder
        result: TGeo.CNamedShape = TGeo.CNamedShape()
        return result

    def get_namedshape(self) -> TGeo.CNamedShape:
        return self.namedshape

    def get_trailing_edge_shape(self, component_segment_index=1, device_index=1) -> TGeo.CNamedShape:
        """
        gets the trailing edge decice shape from the CPACS configuration
        :param component_segment_index: int default 1
        :param device_index: int default 1
        :return:
        """
        logging.info(f"Getting trailing edge device from {component_segment_index=} {device_index=}")
        compseg: TConfig.CCPACSWingComponentSegment = self.wing.get_component_segment(component_segment_index)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
        self.m.display_this_shape(loft)
        return loft

    def get_trailing_edge_cutout(self, offset=0.02, component_segment_index=1, device_index=1) -> TGeo.CNamedShape:
        """
        Returns the cutout shape with a given offset
        :param offset: float
        :param component_segment_index: int
        :param device_index: int
        :return:
        """
        logging.info(f"Getting trailing edge cutout from {component_segment_index=} {device_index=}")
        compseg: TConfig.CCPACSWingComponentSegment = self.wing.get_component_segment(component_segment_index)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        cutout_nshape: TGeo.CNamedShape = trailing_edge_device.get_cut_out_shape()
        cutout_shape: OTopo.TopoDS_Shape = cutout_nshape.shape()
        cutout_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(cutout_shape, offset,
                                                                               0.000001).Shape()
        cutout_nshape.set_shape(cutout_offset)
        return cutout_nshape
