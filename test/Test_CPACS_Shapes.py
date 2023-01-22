import logging

import OCP.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Extra.ConstructionStepsViewer as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

from Airplane.Configuration import Configuration

CPACS_FILE_NAME = "aircombat_v14"

if __name__ == "__main__":
    logging.debug("Start test for CPACS shapes for CPACS file ")
    m = myDisplay.ConstructionStepsViewer.instance(True, 1.5)

    # try:
    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    configuration = Configuration(tigl_h)

    # setting and display fuselage
    fuselage: TConfig.CCPACSWing = configuration.get_fuselage()
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)
    m.display_in_origin(fuselage_loft, logging.NOTSET, "", True)

    cpacs_configuration = configuration.get_cpacs_configuration()

    for i in range(1, cpacs_configuration.get_wing_count() + 1):

        wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(i)
        wing_loft: TGeo.CNamedShape = wing.get_loft()
        wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
        wing_dimensions = ShapeDimensions(wing_loft)
        m.display_in_origin(wing_loft, logging.NOTSET, "", True)
        try:
            mirrored_loft = wing.get_mirrored_loft()
            m.display_in_origin(mirrored_loft, logging.NOTSET, "", True)
        except:
            logging.warning(f"No mirrored {wing_loft.name()}")

    wing: TConfig.CCPACSWing = configuration.get_right_main_wing()

    comp_segment: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(1)
    control_surface: TConfig.CCPACSControlSurfaces = comp_segment.get_control_surfaces()
    trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
    trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(1)
    ruder_loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
    m.display_in_origin(ruder_loft, logging.NOTSET, "", True)

    try:
        mirrored_loft = trailing_edge_device.get_mirrored_loft()
        m.display_in_origin(mirrored_loft, logging.NOTSET, "", True)
    except:
        logging.warning(f"No mirrored {ruder_loft.name()}")

    all_engines = cpacs_configuration.get_engines()

    engine_positions: TConfig.CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
    engine_position: TConfig.CCPACSEnginePosition = engine_positions.get_engine_position(1)
    engine_position_transformation: TGeo.CCPACSTransformation = engine_position.get_transformation()

    rotation: TGeo.CTiglPoint = engine_position_transformation.get_rotation()
    down_thrust_angle = rotation.y
    right_thrust_angle = rotation.z
    logging.debug(f"{down_thrust_angle=}")
    logging.debug(f"{right_thrust_angle=}")

    translation: TGeo.CCPACSPointAbsRel = engine_position_transformation.get_translation()
    logging.debug(f"engine position= ({translation.get_x()},\t {translation.get_y()},\t {translation.get_z()})")

    engine_scaling: TGeo.CTiglPoint = engine_position_transformation.get_scaling()
    engine_length = engine_scaling.x
    engine_width = engine_scaling.y
    engine_height = engine_scaling.z
    logging.debug(
        f"engine size= length: {engine_length},width: {engine_width}, height: {engine_height},\t")

    m.start()
