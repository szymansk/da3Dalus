import sys

import json 
import os

from Airplane.creator.EngineCapeShapeCreator import EngineCapeShapeCreator

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from Airplane.ConstructionStepNode import ConstructionStepNode, ConstructionRootNode
from Airplane.FuselageConstructionSteps import *
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    base_scale = 0.04*1000
    ribcage_factor = 0.35
    mount_plate_thickness = 0.005*1000
    engine_screw_hole_circle = 0.042*1000
    engine_mount_box_length = 0.0133 * 2.5*1000

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")
    pwd = os.path.curdir

    full_fuselage_loft_node = ConstructionStepNode(
        StepImportCreator("full_fuselage", file_name=os.path.abspath("../components/aircraft/RV-7/fuselage.step"),
                          scale=base_scale))
    root_node.append(full_fuselage_loft_node)

    # #########
    engine_cape_full_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape", engine_index=1,
                               mount_plate_thickness=mount_plate_thickness,
                               full_fuselage_loft="full_fuselage"))
    root_node.append(engine_cape_full_node)


    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path=os.path.abspath("../exports"),
                            shapes_to_export=["engine_cape.cape",
                                              "engine_cape.loft"
                                              ]))
    root_node.append(aircraft_step_export_node)

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

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

    component_information = {"brushless": engine_info1}

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             engine_information=engine_information,
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
