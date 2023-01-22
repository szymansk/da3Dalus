from __future__ import print_function

import logging

import OCP.BRepOffsetAPI as OOff
from OCP.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from cadquery import Workplane

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
        self.wing_loft: Workplane = self.wing.get_loft()
        self.wing_shape: TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)

        self.namedshape: Workplane = Workplane()
        self.shapes: list = []
        self.m = ConstructionStepsViewer.instance()

    def create_ruder(self, factor_ruderarm_pos=0.333) -> Workplane:
        """
        Creates the Ruder with the ruderarm at the given position.
        :param factor_ruderarm_pos:
        :return:
        """
        logging.info(f"Creating ribs option1")
        logging.info(f"Segment Count: {self.wing.get_segment_count()}")
        # TODO: Implementaions of create ruder
        result: Workplane = Workplane()
        return result

    def get_namedshape(self) -> Workplane:
        return self.namedshape

    @classmethod
    def get_trailing_edge_shape(cls, wing, component_segment_index=1, device_index=1) -> Workplane:
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
        loft: Workplane = trailing_edge_device.get_loft()
        ConstructionStepsViewer.instance().display_this_shape(loft, logging.NOTSET)
        return loft

    @classmethod
    def get_trailing_edge_cutout(cls, wing, offset=0.02, component_segment_index=1, device_index=1) \
            -> tuple[Workplane, Workplane]:
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
        cutout_namedshape_a: Workplane = trailing_edge_device.get_cut_out_shape()
        cutout_shape: TopoDS_Shape = cutout_namedshape_a.shape()

        toleranz = 0.000001
        cutout_offset: TopoDS_Shape = OOff.BRepOffsetAPI_MakeOffsetShape(cutout_shape, offset, toleranz).Shape()
        cutout_namedshape = Workplane(cutout_offset, "")

        return cutout_namedshape, cutout_namedshape_a
