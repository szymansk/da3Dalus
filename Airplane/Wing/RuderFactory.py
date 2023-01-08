from __future__ import print_function

import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *


class RuderFactory:
    '''
    This Class provides different methods to create ruder for the wings
    '''

    def __init__(self, cpacs_configuration, wing_index):
        '''
         Initialize the class with the tigle handle with the CPACS configuration and the index of the wing to be created
         '''
        logging.info(f"Initilizin Ruder Factory")
        self.cpacs_configuration: TConfig.CCPACSConfiguration = cpacs_configuration

        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wing_index)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)

        self.namedshape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list = []
        self.m = ConstructionStepsViewer.instance()

    def create_ruder(self, factor_ruderarm_pos=0.333) -> TGeo.CNamedShape:
        """
        Creates the Ruder with the ruderarm at the given position.
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

    @classmethod
    def get_trailing_edge_shape(cls, wing, component_segment_index=1, device_index=1) -> TGeo.CNamedShape:
        """
        gets the trailing edge decice shape from the CPACS configuration
        :param wing:
        :param component_segment_index: index of the componente segment default set to 1
        :param device_index: index of the device, setting defaul index to1
        :return:
        """
        logging.info(f"Getting trailing edge device from {component_segment_index=} {device_index=}")
        try:
            compseg: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(component_segment_index)
        except IndexError:
            logging.info(f"cannot find trailing edge device")
            return None
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
        ConstructionStepsViewer.instance().display_this_shape(loft, logging.NOTSET)
        return loft

    @classmethod
    def get_trailing_edge_cutout(cls, wing, offset=0.02, component_segment_index=1, device_index=1) \
            -> tuple[TGeo.CNamedShape, TGeo.CNamedShape]:
        """
        Returns the cutout shape with a given offset
        :param wing:
        :param offset: how much bigger should the cutout be
        :param component_segment_index: index of the componente segment default set to 1
        :param device_index: index of the device, setting defaul index to1
        :return:
        """
        logging.info(f"Getting trailing edge cutout from {component_segment_index=} {device_index=}")
        try:
            compseg: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(component_segment_index)
        except IndexError:
            return None, None
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()

        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        cutout_namedshape_a: TGeo.CNamedShape = trailing_edge_device.get_cut_out_shape()
        cutout_shape: OTopo.TopoDS_Shape = cutout_namedshape_a.shape()

        toleranz = 0.000001
        cutout_offset: OTopo.TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(cutout_shape, offset, toleranz).Shape()
        cutout_namedshape = TGeo.CNamedShape(cutout_offset, "")

        return cutout_namedshape, cutout_namedshape_a
