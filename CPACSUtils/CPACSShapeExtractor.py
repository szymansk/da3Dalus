import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
import OCP.TopoDS as OTopo


class CPACSShapeExtractor:
    def __init__(self, tigl_handle):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)

    def get_wing(self, wing_index):
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wing_index)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.fuselage()
        return self.wing_shape

    def get_fuselage(self, fuselage_index):
        self.fuselage: TConfig.CCPACSWing = self.cpacs_configuration.get_fuselage(fuselage_index)
        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.fuselage()
        return self.fuselage_shape

    def get_trailing_edge_device(self, wing_index, device_index):
        '''
        return the Shape of the Trialing edge device and the shape of the cutout
        '''
        self.get_wing(wing_index)
        compseg: TConfig.CCPACSWingComponentSegment = self.wing.get_component_segment(1)
        control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
        trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
        trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(
            device_index)
        cutout_Nshape: TGeo.CNamedShape = trailing_edge_device.get_cut_out_shape()
        cutout_shape: OTopo.TopoDS_Shape = cutout_Nshape.fuselage()
        shape_nshape: TGeo.CNamedShape = trailing_edge_device.get_loft()
        shape: OTopo.TopoDS_Shape = shape_nshape.fuselage()
        return shape, cutout_shape
