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

# TODO: * cutouts for hinges
#       * cutout for elevator flap rod (carbon 1mm) in elvator and in rudder
#       * wings with servos for aileron and flaps
#       * cutouts for elevator and rudder rods (anlenkung carbonstab 1mm)
#       * ruderhörner der Anlenkpunkt sollte über der Drehachse liegen und der Abstand beider
#         Drehpunkte sollte mit dem Abstand der Anschlusspunkte übereinstimmen vergleich:
#         (https://www.rc-network.de/threads/die-kinematik-ungewollter-differenzierung.11779720/)

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

    base_scale = 0.04
    ribcage_factor = 0.35
    mount_plate_thickness = 0.005
    engine_screw_hole_circle = 0.042
    engine_mount_box_length = 0.0133 * 2.5

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="wings")

    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("full_wing_loft",
                                 right_main_wing_index=1))
    root_node.append(full_wing_loft_node)

    # full_wing_loft_node = ConstructionStepNode(
    #     StepImportCreator("right_wing_loft",
    #                       step_file="../components/aircraft/RV-7/wing_right.step",
    #                       scale=base_scale))
    # root_node.append(full_wing_loft_node)

    # flaps_node = ConstructionStepNode(
    #     StepImportCreator("flaps",
    #                       step_file="../components/aircraft/RV-7/ flaps.step",
    #                       scale=base_scale))
    # root_node.append(flaps_node)
    #
    # aileron_node = ConstructionStepNode(
    #     StepImportCreator("aileron",
    #                       step_file="../components/aircraft/RV-7/aileron_right.step",
    #                       scale=base_scale))
    # root_node.append(aileron_node)
    #
    # full_fuselage_loft_node = ConstructionStepNode(
    #     StepImportCreator("full_fuselage",
    #                       step_file="../components/aircraft/RV-7/fuselage.step",
    #                       scale_x=base_scale,
    #                       scale_y=base_scale - base_scale*0.01,
    #                       scale_z=base_scale - base_scale*0.01))
    # root_node.append(full_fuselage_loft_node)
    #
    # offset_fuselage_node = ConstructionStepNode(
    #     StepImportCreator("offset_fuselage",
    #                       step_file="../components/aircraft/RV-7/fuselage_inlets.step",
    #                       scale=base_scale))
    # root_node.append(offset_fuselage_node)

    wing_rib_cage_node = ConstructionStepNode(
        WingRibCageCreator("wing_ribs", wing_loft="full_wing_loft.right", wing_index=1, rib_distance=0.04,
                           loglevel=logging.INFO))
    root_node.append(wing_rib_cage_node)

    wing_pipes_node = ConstructionStepNode(
        ReinforcementPipesCreator("pipes", wing_index=1, pipe_diameter=0.006, wall_thickness=0.0004,
                                  pipe_position=[0, 1], loglevel=logging.INFO))
    root_node.append(wing_pipes_node)

    aileron_shape_node = ConstructionStepNode(
        CPACSTrailingEdgeDeviceCreator("aileron",
                                       wing_index=1,
                                       component_segment_index=1,
                                       device_index=1,
                                       loglevel=logging.INFO))
    root_node.append(aileron_shape_node)

    aileron_cut_out_shape_node = ConstructionStepNode(
        CPACSTrailingEdgeDeviceCutOutCreator("aileron_cut_out",
                                             wing_index=1,
                                             component_segment_index=1,
                                             device_index=1,
                                             loglevel=logging.INFO))
    root_node.append(aileron_cut_out_shape_node)

    servo_node = ConstructionStepNode(
        CPACSServoCutOutCreator("servo",
                                aileron="aileron",
                                wing_index=1,
                                loglevel=logging.INFO))
    root_node.append(servo_node)

    fuse_inernal_node = ConstructionStepNode(
        FuseMultipleShapesCreator("internal_structure",
                                  shapes=["wing_ribs", "pipes", "servo.servo", "servo.cable"],
                                  loglevel=logging.INFO))
    root_node.append(fuse_inernal_node)

    wing_offset_node = ConstructionStepNode(
        WingOffsetCreator("wing_offset",
                          wing_loft="full_wing_loft.right",
                          loglevel=logging.INFO))
    root_node.append(wing_offset_node)

    cut_internal_structure_node = ConstructionStepNode(
        CutMultipleShapesCreator("final_wing",
                                 minuend="wing_offset",
                                 subtrahends=["internal_structure", "aileron_cut_out.offset"],
                                 loglevel=logging.DEBUG))
    root_node.append(cut_internal_structure_node)

    mirror_wing = ConstructionStepNode(
        MirrorShapeCreator("left_wing", shape="final_wing"))
    root_node.append(mirror_wing)

    mirror_aileron = ConstructionStepNode(
        MirrorShapeCreator("left_aileron", shape="aileron"))
    root_node.append(mirror_aileron)

    rest_wing_node = ConstructionStepNode(
        WingRestCreator("rest", wing_loft="full_wing_loft.right",
                        wing_index=1,
                        internal_structure="cut_internal_structure",
                        wing_offset="wing_offset",
                        loglevel=logging.DEBUG))
    #root_node.append(rest_wing_node)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=["final_wing", "aileron", "left_wing"],
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

    wing_information = {1: CPACSWingInformation(cpacs_configuration=ccpacs_configuration,
                                                wing_index=1,
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
