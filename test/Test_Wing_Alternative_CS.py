import sys

import json 
import os

from Airplane.creator import (AddMultipleShapesCreator, WingLoftCreator,
                              VaseModeRibCutoutCreator, VaseModeSpareCreator,
                              VaseModeWingCreator)
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration

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
    
    ribcage_factor: float = 0.5
    mount_plate_thickness: float = 5
    engine_screw_hole_circle: float = 42.0
    engine_mount_box_length: float = 13.3 * 2.5

    printer_wall_thickness: float = 0.42
    spare_support_geometry_is_round: bool = False
    spare_support_dimension_width: float = 6
    spare_support_dimension_height: float = 6
    spare_perpendicular: bool = False
    spare_position_factor: float = 1 / 3  # value betweein (0,1) as fraction of the chord
    leading_edge_offset: float = 10
    trailing_edge_offset: float = 30
    minimum_rib_angle: float = 45

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="RV-7-wing")
    pwd = os.path.curdir

    vase_wing_loft = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing",
                             wing_index="main_wing",
                             wing_side="BOTH",
                             printer_wall_thickness=printer_wall_thickness,
                             spare_support_geometry_is_round=spare_support_geometry_is_round,
                             spare_support_dimension_width=spare_support_dimension_width,
                             spare_support_dimension_height=spare_support_dimension_height,
                             leading_edge_offset=leading_edge_offset,
                             trailing_edge_offset=trailing_edge_offset,
                             offset=printer_wall_thickness,
                             minimum_rib_angle=minimum_rib_angle,
                             loglevel=logging.DEBUG))
    root_node.append(vase_wing_loft)

    full_wing_loft = ConstructionStepNode(
        WingLoftCreator("wing_loft",
                        wing_index="main_wing",
                        wing_side="BOTH",
                        loglevel=logging.DEBUG))
    root_node.append(full_wing_loft)

    fuselage_hull = ConstructionStepNode(
        StepImportCreator("fuselage_hull_imp",
                          step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage_inlets.step"),
                          scale=base_scale,
                          loglevel=logging.INFO))
    root_node.append(fuselage_hull)

    cut_hull = ConstructionStepNode(
        Cut2ShapesCreator("cut_wing_from_fuselage",
                          minuend=fuselage_hull.creator_id,
                          subtrahend=f"{full_wing_loft.creator_id}",
                          loglevel=logging.INFO))
    root_node.append(cut_hull)

    ### CREATE REINFORCET WING IN VASE MODE PRINTING
    # https://www.abbottaerospace.com/aa-sb-001/22-aircraft-specific-design-features-and-design-methods/22-16-57-wings/22-16-2-main-wing-box/
    # steps
    # 1. create hull (done)
    # 2. create offset_hull (done)
    # 3. cut ribs from offset_hull
    # 4. cut offset_rib_hull from hull
    # 5. create spares
    #    a. main spare
    #    b. front spare
    #    c. rear spare
    # 6. join spares with offset_rib_hull
    # 7. add servo
    #    a. servo mount
    #    b. servo cover
    # 8. helper shapes for main rib
    #

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[vase_wing_loft.creator_id]))
    root_node.append(aircraft_step_export_node)

    #####################
    #####################
    #####################

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

    #airfoil = "../components/airfoils/naca23013.5.dat"
    test_wing = 2
    airfoil = "../components/airfoils/naca2415.dat"
    wing_config = WingConfiguration(root_airfoil=airfoil,
                      nose_pnt=(192.113, 0, -44.5),
                      root_chord=183,
                      root_dihedral=3.7,
                      root_incidence=0,
                      length=410,
                      sweep=0,
                      tip_chord=183,
                      tip_dihedral=0,
                      tip_incidence=0)
    if test_wing == 1:
        wing_config.add_segment(length=100,
                               sweep=20,
                               tip_chord=183-20,
                               tip_dihedral=15,
                               tip_incidence=0)
        wing_config.add_segment(length=5,
                               sweep=5,
                               tip_chord=183-20-5,
                               tip_dihedral=15,
                               tip_incidence=0)
        wing_config.add_segment(length=5,
                               sweep=5,
                               tip_chord=183-20-10,
                               tip_dihedral=15,
                               tip_incidence=0)
        wing_config.add_segment(length=5,
                               sweep=5,
                               tip_chord=183-20-15,
                               tip_dihedral=15,
                               tip_incidence=0)
        wing_config.add_segment(length=50,
                               sweep=45+50,
                               tip_chord=183-20-20-40-50,
                               tip_dihedral=0,
                               tip_incidence=0,
                               tip_airfoil="../components/airfoils/nacam2.dat")
    elif test_wing == 2:
        wing_config.add_segment(length=100,
                               sweep=10,
                               tip_chord=183-20,
                               tip_dihedral=5,
                               tip_incidence=0)
        wing_config.add_segment(length=50,
                               sweep=10,
                               tip_chord=183-40,
                               tip_dihedral=10,
                               tip_incidence=0)
        wing_config.add_segment(length=50,
                               sweep=10,
                               tip_chord=183-80,
                               tip_dihedral=5,
                               tip_incidence=0)
    wing_configuration = {"main_wing": wing_config}


    # load the string
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
