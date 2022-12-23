from __future__ import print_function

import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *


class RuderFactory:
    """
    This Class provides different methods to create ruder for the wings
    """

    def __init__(self, wing):
        """
         Initialize the class with the tigle handle with the CPACS configuration and the index of the wing to be created
         """
        logging.debug(f"Initialize Ruder Factory")

        self.wing: TConfig.CCPACSWing = wing
        self.named_shape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.m = ConstructionStepsViewer.instance()

    def create_ruder(self, factor_ruderarm_pos=0.333) -> TGeo.CNamedShape:
        """
        Creates the Ruder with the ruderarm at the given position.
        :param factor_ruderarm_pos:
        :return:
        """
        logging.debug(f"Creating ribs option1")
        logging.debug(f"Segment Count: {self.wing.get_segment_count()}")
        # TODO: Implementaions of create ruder
        result: TGeo.CNamedShape = TGeo.CNamedShape()
        return result

    def get_named_shape(self) -> TGeo.CNamedShape:
        return self.named_shape

    def get_trailing_edge_shape(self, component_segment_index=1, device_index=1) -> TGeo.CNamedShape:
        """
        gets the trailing edge decice shape from the CPACS configuration
        :param component_segment_index: index of the componente segment default set to 1
        :param device_index: index of the device, setting defaul index to1
        :return:
        """
        logging.debug(f"Getting trailing edge device from {component_segment_index=} {device_index=}")
        compseg: TConfig.CCPACSWingComponentSegment = self.wing.get_component_segment(component_segment_index)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
        self.m.display_this_shape(loft, severity=logging.NOTSET)
        return loft

    def get_trailing_edge_cutout(self, offset=0.02, component_segment_index=1, device_index=1) -> TGeo.CNamedShape:
        """
        Returns the cutout shape with a given offset
        :param offset: how much bigger should the cutout be
        :param component_segment_index: index of the componente segment default set to 1
        :param device_index: index of the device, setting defaul index to1
        :return:
        """
        logging.debug(f"Getting trailing edge cutout from {component_segment_index=} {device_index=}")
        compseg: TConfig.CCPACSWingComponentSegment = self.wing.get_component_segment(component_segment_index)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()

        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        cutout_namedshape: TGeo.CNamedShape = trailing_edge_device.get_cut_out_shape()
        cutout_shape: OTopo.TopoDS_Shape = cutout_namedshape.shape()

        toleranz = 0.000001
        cutout_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(cutout_shape, offset, toleranz).Shape()
        cutout_namedshape.set_shape(cutout_offset)

        return cutout_namedshape
