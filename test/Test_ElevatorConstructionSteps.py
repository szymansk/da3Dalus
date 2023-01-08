import sys
import logging
from pathlib import Path

from tigl3.tigl3wrapper import Tigl3

import Extra.tigl_extractor as tg
import json

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode, JSONStepNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.WingConstructionSteps import *
from Airplane.aircraft_topology.EngineInformation import Position
from Airplane.aircraft_topology.WingInformation import CPACSWingInformation


if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.DEBUG, stream=sys.stdout)
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="wings")

    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("full_wing_loft",
                                 right_main_wing_index=2))
    root_node.append(full_wing_loft_node)

    wing_rib_cage_node = ConstructionStepNode(
        WingRibCageCreator("wing_ribs", wing_loft="full_wing_loft.right", wing_index=2, rib_distance=0.04,
                           loglevel=logging.INFO))
    root_node.append(wing_rib_cage_node)

    wing_pipes_node = ConstructionStepNode(
        ReinforcementPipesCreator("pipes", wing_index=2, pipe_diameter=0.002, wall_thickness=0.0004,
                                  pipe_position=[0, 2], loglevel=logging.INFO))
    root_node.append(wing_pipes_node)

    fuse_inernal_node = ConstructionStepNode(
        FuseMultipleShapesCreator("internal_structure",
                                  shapes=["wing_ribs", "pipes"],
                                  loglevel=logging.INFO))
    root_node.append(fuse_inernal_node)

    wing_offset_node = ConstructionStepNode(
        WingOffsetCreator("wing_offset",
                          wing_loft="full_wing_loft.right",
                          loglevel=logging.INFO))
    root_node.append(wing_offset_node)

    cut_internal_structure_node = ConstructionStepNode(
        CutMultipleShapesCreator("right_wing",
                                 minuend="wing_offset",
                                 subtrahends=["internal_structure"],
                                 loglevel=logging.DEBUG))
    root_node.append(cut_internal_structure_node)

    mirror_wing = ConstructionStepNode(
        MirrorShapeCreator("left_wing", shape="right_wing"))
    root_node.append(mirror_wing)

    mirror_aileron = ConstructionStepNode(
        MirrorShapeCreator("left_aileron", shape="aileron"))
    root_node.append(mirror_aileron)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=["right_wing", "left_wing"],
                            loglevel=logging.DEBUG))
    root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    servo_elevator = ServoInformation(
        height=0.022,
        width=0.012,
        length=0.023,
        lever_length=0.023,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28 + 0.02,
        trans_y=0.005,
        trans_z=0.044 - 0.0244)

    servo_rudder = ServoInformation(
        height=0.022,
        width=0.012,
        length=0.023,
        lever_length=0.023,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28 + 0.02,
        trans_y=-0.005 - 0.012,
        trans_z=0.044 - 0.0244)
    servo_information = {1: servo_elevator, 2: servo_rudder}

    engine_info1 = EngineInformation(down_thrust=-2.5,
                                     side_thrust=-2.5,
                                     position=Position(0.0458, 0, 0),
                                     length=0.0452,
                                     width=0.035,
                                     height=0.035,
                                     screw_hole_circle=0.042,
                                     mount_box_length=0.0133 * 2.5,
                                     screw_din_diameter=0.0032,
                                     screw_length=0.016)

    # engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration)}
    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031, height=0.035, length=0.108,
                                            trans_x=0.129, trans_y=0.0, trans_z=-0.021,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    wing_information = {2: CPACSWingInformation(cpacs_configuration=ccpacs_configuration,
                                                wing_index=2,
                                                horizontal_rib_quantity=4)}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
                                             servo_information=servo_information,
                                             component_information=component_information,
                                             cpacs_configuration=ccpacs_configuration,
                                             wing_information=wing_information)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
    json_file_path = f"../components/constructions/{root_node.identifier}.json"
    json_file = open(json_file_path, "w")
    json.dump(fp=json_file, obj=root_node, indent=4, cls=GeneralJSONEncoder)
    json_file.close()

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
