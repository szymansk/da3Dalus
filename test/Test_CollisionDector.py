import logging

import OCC.Core.TopoDS as OTopo
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Extra.CollisionDetector as cd
import Extra.ConstructionStepsViewer as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions
from Airplane.Configuration import Configuration

import logging;

CPACS_FILE_NAME = "simple_aircraft"

if __name__ == "__main__":
    logging.debug(f"Start test for Collision Detector with CPACS file {CPACS_FILE_NAME}")
    m = myDisplay.ConstructionStepsViewer.instance(True, 4)

    # try:
    tigl_h = tg.get_tigl_handler("simple_aircraft")
    configuration = Configuration(tigl_h)

    # Setting and display fuselage
    fuselage: TConfig.CCPACSWing = configuration.get_fuselage()
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)
    m.display_in_origin(fuselage_loft, logging.NOTSET, "", True)

    # Setting wing
    wing: TConfig.CCPACSWing = configuration.get_right_main_wing()
    wing_loft: TGeo.CNamedShape = wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
    wing_dimensions = ShapeDimensions(wing_loft)

    comp_segment: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(1)
    control_surface: TConfig.CCPACSControlSurfaces = comp_segment.get_control_surfaces()
    trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
    trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(1)
    ruder_loft: TGeo.CNamedShape = trailing_edge_device.get_loft()

    # Create test cases for wing
    testcase_wing = [(ruder_loft, True), (fuselage_loft, False)]

    testcases_all = {wing_loft: testcase_wing}

    collisions_detector = cd.CollisionDetector()
    collisions_detector.multiple_collision_check(testcases_all)

    logging.debug("Test finished. Display results")
    m.start()
