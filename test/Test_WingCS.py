import logging
import sys

import json 
import os

from Airplane.WingConstructionSteps import WingLoftCreator
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration
from Airplane.creator.WingReinforcementShapeCreator import WingReinforcementShapeCreator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position, EngineInformation

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    base_scale = 38
    printer_resolution = 0.2  # 0.2 mm layer height
    
    ribcage_factor = 0.5
    mount_plate_thickness = 5
    engine_screw_hole_circle = 42.0
    engine_mount_box_length = 13.3 * 2.5

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7-wing")
    pwd = os.path.curdir

    full_wing_loft = ConstructionStepNode(
        WingLoftCreator("wing_loft", wing_index="main_wing", wing_side="RIGHT", loglevel=logging.DEBUG))
    root_node.append(full_wing_loft)

    ffull_wing_loft = ConstructionStepNode(
        StepImportCreator("full_wing_loft",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/wing_right.step"),
                          scale=base_scale, loglevel=logging.DEBUG))
    root_node.append(ffull_wing_loft)

    big_full_wing_loft = ConstructionStepNode(
        SimpleOffsetShapeCreator("big_full_wing_loft",
                                 offset=16 * printer_resolution,
                                 shape=full_wing_loft.creator_id,
                                 loglevel=logging.DEBUG))
    root_node.append(big_full_wing_loft)

    small_full_wing_loft = ConstructionStepNode(
        SimpleOffsetShapeCreator("small_full_wing_loft",
                                 offset=-2 * printer_resolution,
                                 shape=full_wing_loft.creator_id,
                                 loglevel=logging.DEBUG))
    root_node.append(small_full_wing_loft)

    wing_shell = ConstructionStepNode(
        FuselageShellShapeCreator("wing_shell",
                                  thickness=0.8,
                                  fuselage=full_wing_loft.creator_id,
                                  loglevel=logging.DEBUG))
    # root_node.append(wing_shell)
    flaps_node = ConstructionStepNode(
    StepImportCreator("flaps",
                      step_file=os.path.abspath(f"../components/aircraft/RV-7/flaps.step"),
                      scale=base_scale))
    #root_node.append(flaps_node)

    aileron_node = ConstructionStepNode(
        StepImportCreator("aileron",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/aileron_right.step"),
                          scale=base_scale))
    #root_node.append(aileron_node)

    fuselage_hull = ConstructionStepNode(
        StepImportCreator("fuselage_hull_imp",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage_inlets.step"),
                          scale=base_scale,
                          loglevel=logging.INFO))
    root_node.append(fuselage_hull)

    fuselage_small_hull = ConstructionStepNode(
        SimpleOffsetShapeCreator("fuselage_small_hull",
                                 offset=-4 * printer_resolution,
                                 shape="fuselage_hull_imp",
                                 loglevel=logging.INFO))
    #fuselage_hull.append(fuselage_small_hull)

    wing_reinforcement = ConstructionStepNode(
        WingReinforcementShapeCreator("wing_reinforcement",
                                      fuselage_loft=big_full_wing_loft.creator_id,
                                      full_wing_loft=full_wing_loft.creator_id,
                                      loglevel=logging.NOTSET))
    root_node.append(wing_reinforcement)

    # wing_hull = ConstructionStepNode(
    #     CutMultipleShapesCreator("wing_hull",
    #                              minuend="big_full_wing_loft",
    #                              subtrahends="wing_reinforcement",
    #                              loglevel=logging.DEBUG))
    # root_node.append(wing_hull)

    elevator = ConstructionStepNode(
        StepImportCreator("elevator",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/full_elevator_straight.step"),
                          scale=base_scale))
    #root_node.append(elevator)

    rudder = ConstructionStepNode(
        StepImportCreator("rudder",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_fix_final.step"),
                          scale=base_scale))
    #root_node.append(rudder)

    rudder_flap = ConstructionStepNode(
        StepImportCreator("rudder_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/rudder_flap.step"),
                          scale=base_scale))
    #root_node.append(rudder_flap)

    elevator_flap = ConstructionStepNode(
        StepImportCreator("elevator_flap",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/elevator_flap_straight.step"),
                          scale=base_scale))
    #root_node.append(elevator_flap)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[wing_reinforcement.creator_id,
                                              big_full_wing_loft.creator_id,
                                              #"elevator_flap",
                                              #"rudder",
                                              #"rudder_flap",
                                              #"flaps",
                                              #"aileron"
                                              ]))
    root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    servo_elevator = ServoInformation(
        height=0.022*1000,
        width=0.012*1000,
        length=0.023*1000,
        lever_length=0.023*1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28*1000+0.02*1000,
        trans_y=0.005*1000,
        trans_z=0.044*1000-0.0244*1000)

    servo_rudder = ServoInformation(
        height=0.022*1000,
        width=0.012*1000,
        length=0.023*1000,
        lever_length=0.023*1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28*1000+0.02*1000,
        trans_y=-0.005*1000-0.012*1000,
        trans_z=0.044*1000-0.0244*1000)
    servo_information = {1: servo_elevator, 2: servo_rudder}

    engine_info1 = EngineInformation(down_thrust=-2.5,
                                     side_thrust=-2.5,
                                     position=Position(0.0458*1000, 0, 0),
                                     length=0.0452*1000,
                                     width=0.035*1000,
                                     height=0.035*1000,
                                     screw_hole_circle=0.042*1000,
                                     mount_box_length=0.0133 * 2.5*1000,
                                     screw_din_diameter=0.0032*1000,
                                     screw_length=0.016*1000,
                                     rot_x=45)

    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031*1000, height=0.035*1000, length=0.108*1000,
                                            trans_x=0.129*1000, trans_y=0.0, trans_z=-0.021*1000,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    airfoil = "../components/airfoils/naca23013.5.dat"
    wing_configuration = {"main_wing": WingConfiguration(root_airfoil=airfoil,
                                           nose_pnt=(192.113, -1, -44.5),
                                           root_chord=183,
                                           root_dihedral=3.7,
                                           root_incidence=0,
                                           length=410,
                                           sweep=0,
                                           tip_chord=183,
                                           tip_dihedral=0,
                                           tip_incidence=0)}
    # wing_configuration.add_segment(length=100,
    #                                sweep=50,
    #                                tip_chord=50,
    #                                tip_dihedral=0,
    #                                tip_incidence=-2)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
                                             servo_information=servo_information,
                                             component_information=component_information,
                                             wing_config=wing_configuration)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
    json_file_path = os.path.abspath(f"../components/constructions/{root_node.identifier}.json")
    json_file = open(json_file_path, "w")
    json.dump(fp=json_file, obj=root_node, indent=4, cls=GeneralJSONEncoder)
    json_file.close()

    try:
        # build on basis of deserialized json
        structure = myMap.create_shape()
        from pprint import pprint

        pprint(structure)
    except Exception as err:
        raise err
    pass
