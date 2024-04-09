import logging
import sys
import os

import json
from pathlib import Path

from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

from Airplane.aircraft_topology.components import *
from Airplane.aircraft_topology.Position import Position
from Airplane.aircraft_topology.wing import *
from Airplane.creator.components import *
from Airplane.creator.export_import import *
from Airplane.creator.fuselage import *
from Airplane.creator.cad_operations import *
from Airplane.creator.wing import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)

    logging.root.level = logging.INFO
    base_scale = 38
    printer_resolution = 0.2  # 0.2 mm layer hight

    ribcage_factor = 0.49
    mount_plate_thickness = 5
    engine_screw_hole_circle = 42.0
    engine_mount_box_length = 13.3 * 2.5

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7")
    pwd = os.path.curdir

    fuselage_hull = ConstructionStepNode(
        StepImportCreator("fuselage_hull_imp",
                          step_file=os.path.abspath("../components/aircraft/RV-7/fuselage_inlets.step"),
                          scale=base_scale,
                          loglevel=logging.CRITICAL))
    root_node.append(fuselage_hull)

    # #########
    engine_mount_init = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount_init",
                                engine_index=1,
                                mount_plate_thickness=mount_plate_thickness,
                                cutout_thickness=mount_plate_thickness + 4 * printer_resolution,
                                loglevel=logging.CRITICAL))
    root_node.append(engine_mount_init)

    engine_mount_plate = ConstructionStepNode(
        EngineCoverAndMountPanelAndFuselageShapeCreator(
            "engine_mount_plate", engine_index=1, mount_plate_thickness=mount_plate_thickness,
            full_fuselage_loft="fuselage_hull_imp", loglevel=logging.CRITICAL))
    engine_mount_init.append(engine_mount_plate)

    engine_mount_plate_cutout = ConstructionStepNode(
        Cut2ShapesCreator("engine_mount_plate_cutout",
                          minuend=engine_mount_plate.creator_id,
                          subtrahend=f"{engine_mount_init.creator_id}.cutout",
                          loglevel=logging.CRITICAL))
    engine_mount_plate.append(engine_mount_plate_cutout)

    engine_mount = ConstructionStepNode(
        Fuse2ShapesCreator("engine_mount",
                           shape_a=engine_mount_plate_cutout.creator_id,
                           shape_b=engine_mount_init.creator_id,
                           loglevel=logging.DEBUG))
    engine_mount_plate_cutout.append(engine_mount)
    # engine mount END

    brushless_shape_import = ConstructionStepNode(
        ComponentImporterCreator("brushless",
                                 component_file=os.path.abspath("../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.step"),
                                 component_idx="brushless",
                                 loglevel=logging.DEBUG))
    root_node.append(brushless_shape_import)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path=os.path.abspath("../exports"),
                            shapes_to_export=["engine_mount",
                                              "brushless"]))
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
        trans_x=0.28+0.02,
        trans_y=0.005,
        trans_z=0.044-0.0244)

    servo_rudder = ServoInformation(
        height=0.022,
        width=0.012,
        length=0.023,
        lever_length=0.023,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28+0.02,
        trans_y=-0.005-0.012,
        trans_z=0.044-0.0244)
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

    lipo_information = ComponentInformation(width=0.031, height=0.035, length=0.108,
                                            trans_x=0.129, trans_y=0.0, trans_z=-0.021,
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
