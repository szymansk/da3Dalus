import sys
import logging
from pathlib import Path

from tigl3.geometry import CCPACSPointAbsRel

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode, JSONStepNode
from Airplane.FuselageConstructionSteps import FullWingLoftShapeCreator, Cut2ShapesCreator, SliceShapesCreator, \
    EngineMountShapeCreator, EngineCapeShapeCreator, FuselageReinforcementShapeCreator, IgesImportCreator, \
    Fuse2ShapesCreator, FuselageWingSupportShapeCreator, FuselageElectronicsAccessCutOutShapeCreator, \
    Intersect2ShapesCreator, SimpleOffsetShapeCreator, WingAttachmentBoltCutoutShapeCreator, ExportToStlCreator, \
    StepImportCreator, ExportToIgesCreator, ExportToStepCreator, FullWingShapeCreator, EngineMountPanelShapeCreator, \
    FullFuselageLoftShapeCreator
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import CPACSEngineInformation, EngineInformation, Position

if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v15"
    NUMBER_OF_CUTS = 5

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.INFO, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="root")

    option = 1
    if option == 0:
        full_fuselage_loft_node = ConstructionStepNode(
            FullFuselageLoftShapeCreator("full_fuselage_loft", fuselage_index=1))
        root_node.append(full_fuselage_loft_node)
    else:
        full_fuselage_loft_node = ConstructionStepNode(
            StepImportCreator("full_fuselage_loft",
                              step_file="../components/aircraft/punisher/fuselage.step",
                              scale=0.0001))
        root_node.append(full_fuselage_loft_node)

    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount", engine_index=1, mount_plate_thickness=0.005,
                                engine_screw_hole_circle=0.042, engine_mount_box_length=0.0133 * 2.5,
                                engine_screw_din_diameter=0.0032, engine_screw_length=0.016,
                                engine_total_cover_length=None, engine_down_thrust_deg=None,
                                engine_side_thrust_deg=None))
    root_node.append(engine_mount_node)

    engine_panel_node = ConstructionStepNode(
        EngineMountPanelShapeCreator("engine_mount_plate", engine_index=1, mount_plate_thickness=0.005,
                                     engine_screw_hole_circle=0.042, engine_mount_box_length=0.0133 * 2.5,
                                     engine_total_cover_length=None, engine_side_thrust_deg=None,
                                     engine_down_thrust_deg=None, full_fuselage_loft="full_fuselage_loft"))
    engine_mount_node.append(engine_panel_node)

    fuse_mount_with_plate = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount"))
    engine_panel_node.append(fuse_mount_with_plate)

    brushless_shape_import = ConstructionStepNode(
        IgesImportCreator("brushless", iges_file="../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.iges",
                          trans_x=.01, trans_y=.04, trans_z=.0, rot_x=.0, rot_y=-2.5, rot_z=-2.5, scale=0.001))
    root_node.append(brushless_shape_import)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(CPACS_FILE_NAME).stem,
                            file_path="../exports",
                            shapes_to_export=["engine_mount",
                                              "brushless",
                                              ]))
    root_node.append(aircraft_step_export_node)
    # "engine_mount", "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    engine_info1 = EngineInformation(down_thrust=-2.5, side_thrust=-2.5 - 180, position=Position(1.048, 0, 0),
                                     length=0.0512, width=0.035, height=0.035, screw_hole_circle=0.042,
                                     mount_box_length=0.0133 * 2.5, screw_din_diameter=0.0032, screw_length=0.016)

    if option == 0:
        engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration, 0.042, 0.0133 * 2.5, 0.0032, 0.016)}
    else:
        engine_information = {1: engine_info1}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration,
                                             engine_information=engine_information)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))

    try:
        # build on basis of deserialized json
        structure = myMap.create_shape()
        from pprint import pprint
        pprint(structure)
        shapeDisplay.start()
    except Exception as err:
        shapeDisplay.start()
        raise err
    pass
