import logging
import sys

import json 
import os

from Airplane.aircraft_topology.ComponentInformation import ComponentInformation
from Airplane.aircraft_topology.ServoInformation import ServoInformation
from Airplane.creator import *
from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import EngineInformation
from Airplane.aircraft_topology.Position import Position

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


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


    base_scale = 0.04*1000
    ribcage_factor = 0.35
    mount_plate_thickness = 0.005*1000
    engine_screw_hole_circle = 0.042*1000
    engine_mount_box_length = 0.0133 * 2.5*1000

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")
    pwd = os.path.curdir

    full_wing_loft_node = ConstructionStepNode(
        StepImportCreator("full_wing_loft",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/wing.step"),
                          scale=base_scale))
    root_node.append(full_wing_loft_node)

    full_fuselage_loft_node = ConstructionStepNode(
        StepImportCreator("full_fuselage",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage.step"),
                          scale=base_scale))
    root_node.append(full_fuselage_loft_node)

    engine_cape_full_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft=full_fuselage_loft_node.creator_id))
    root_node.append(engine_cape_full_node)

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement_0", rib_width=0.0008 * 1000, rib_spacing=0.00 * 1000,
                                          ribcage_factor=ribcage_factor, reinforcement_pipes_diameter=0.002 * 1000,
                                          print_resolution=0.2, fuselage_loft=f"{engine_cape_full_node.creator_id}.loft",
                                          full_wing_loft=full_wing_loft_node.creator_id))
    root_node.append(fuselage_reinforcement_node)

    fuselage_small_hull = ConstructionStepNode(
        SimpleOffsetShapeCreator("fuselage_small_hull",
                                 offset=-0.8,
                                 shape=full_fuselage_loft_node.creator_id))
    root_node.append(fuselage_small_hull)

    fuselage_reinforcement = ConstructionStepNode(
        Intersect2ShapesCreator("fuselage_reinforcement",
                                shape_a=fuselage_reinforcement_node.creator_id,
                                shape_b=fuselage_small_hull.creator_id))
    root_node.append(fuselage_reinforcement)
    fuselage_reinforcement

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
                                     screw_length=0.016*1000)

    # engine_information = {1: CPACSEngineInformation(1, ccpacs_configuration)}
    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031*1000, height=0.035*1000, length=0.108*1000,
                                            trans_x=0.129*1000, trans_y=0.0, trans_z=-0.021*1000,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
                                             servo_information=servo_information,
                                             component_information=component_information)

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
