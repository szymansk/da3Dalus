import logging
import sys
import os

import json
from pathlib import Path

from airplane.ConstructionStepNode import ConstructionStepNode
from airplane.ConstructionRootNode import ConstructionRootNode
from airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

from airplane.aircraft_topology.components import *
from airplane.aircraft_topology.Position import Position
from airplane.aircraft_topology.wing import *
from airplane.aircraft_topology.wing.Airfoil import Airfoil
from airplane.creator.components import *
from airplane.creator.export_import import *
from airplane.creator.fuselage import *
from airplane.creator.cad_operations import *
from airplane.creator.wing import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)

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
    leading_edge_offset: float = 0.06  # value betweein (0,1) as fraction of the chord
    trailing_edge_offset: float = 0.17  # value betweein (0,1) as fraction of the chord
    minimum_rib_angle: float = 45

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="eHawk-wing")
    pwd = os.path.curdir

    vase_wing_loft = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing", wing_index="main_wing",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    root_node.append(vase_wing_loft)


    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[vase_wing_loft.creator_id,
                                              f"{vase_wing_loft.creator_id}.aileron[2]",
                                              f"{vase_wing_loft.creator_id}.aileron[3]",
                                              f"{vase_wing_loft.creator_id}.aileron[2]*",
                                              f"{vase_wing_loft.creator_id}.aileron[3]*"
                                              ]))
    root_node.append(aircraft_step_export_node)

    #####################
    #####################
    #####################

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    servo_elevator = ServoInformation(
        height=0.022 * 1000,
        width=0.012 * 1000,
        length=0.023 * 1000,
        lever_length=0.023 * 1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28 * 1000 + 0.02 * 1000,
        trans_y=0.005 * 1000,
        trans_z=0.044 * 1000 - 0.0244 * 1000)

    servo_rudder = ServoInformation(
        height=0.022 * 1000,
        width=0.012 * 1000,
        length=0.023 * 1000,
        lever_length=0.023 * 1000,
        rot_x=180.0,
        rot_y=0.0,
        rot_z=0.0,
        trans_x=0.28 * 1000 + 0.02 * 1000,
        trans_y=-0.005 * 1000 - 0.012 * 1000,
        trans_z=0.044 * 1000 - 0.0244 * 1000)
    servo_information = {1: servo_elevator, 2: servo_rudder}


    # Spannweite	1520mm
    # Länge	        925mm
    # Flächeninhalt	22dm²
    # Gewicht	    600g
    # Profil	    RG15

    #### WING ####
    airfoil = "../components/airfoils/rg15.dat"  # eHawk RG15 Profil
    wing_config = WingConfiguration(
        nose_pnt=(0, 0, 0),
        number_interpolation_points=201,
        root_airfoil=Airfoil(airfoil=airfoil,
                             chord=162.,
                             dihedral=1,
                             incidence=0,
                             rotation_point_rel_chord=0.3),
        length=20.,
        sweep=0,
        tip_airfoil=Airfoil(chord=162., dihedral=0, incidence=0),
        spare_list=[
            Spare(spare_support_dimension_width=4,
                  spare_support_dimension_height=4,
                  spare_position_factor=0.25),
            Spare(spare_support_dimension_width=2,
                  spare_support_dimension_height=2,
                  spare_position_factor=0.61),
            Spare(spare_support_dimension_width=6,
                  spare_support_dimension_height=6,
                  spare_position_factor=0.55,
                  spare_vector=(0.,1.,0.),
                  spare_length=70),
            Spare(spare_support_dimension_width=6,
                  spare_support_dimension_height=6,
                  spare_position_factor=0.2,
                  spare_vector=(0., 1., 0.),
                  spare_length=70)
        ])

    # segment 1
    wing_config.add_segment(
        length=200,
        sweep=2.5,
        tip_airfoil=Airfoil(chord=157, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4,
                  spare_support_dimension_height=4,
                  spare_mode="follow"),
            Spare(spare_support_dimension_width=2,
                  spare_support_dimension_height=2,
                  spare_mode="follow"),
            Spare(spare_support_dimension_width=6,
                  spare_support_dimension_height=6,
                  spare_mode="follow",
                  spare_length=60),
            Spare(spare_support_dimension_width=6,
                  spare_support_dimension_height=6,
                  spare_mode="follow",
                  spare_length=60)
        ])

    L_s2 = 250
    L_s3 = 200
    prop_s2_s3s2 = (L_s2/(L_s2+L_s3))
    # segment 2
    S_s2 = 10
    wing_config.add_segment(
        length=L_s2,
        sweep=(45-2.5) * prop_s2_s3s2 - S_s2,# - (157-90)/2.,
        tip_airfoil=Airfoil(chord=90 + (157-90)*prop_s2_s3s2, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4,
                  spare_support_dimension_height=4,
                  spare_mode="follow"),
            Spare(spare_support_dimension_width=2,
                  spare_support_dimension_height=2,
                  spare_mode="follow"),],
        trailing_edge_device=TrailingEdgeDevice(name="aileron",
                                                rel_chord_root=0.8,
                                                rel_chord_tip=0.8,
                                                hinge_spacing=0.5,
                                                side_spacing_root=3.,
                                                side_spacing_tip=0.,
                                                servo=Servo(length=23,
                                                            width=12.5,
                                                            height=31.5,
                                                            leading_length=6, latch_z=14.5,
                                                            latch_x=7.25, latch_thickness=2.6,
                                                            latch_length=6, cable_z=26,
                                                            screw_hole_lx=None,
                                                            screw_hole_d=None),
                                                servo_placement='top',
                                                rel_chord_servo_position=0.4,
                                                rel_length_servo_position=0.44,
                                                positive_deflection_deg=25,
                                                negative_deflection_deg=25,
                                                trailing_edge_offset_factor=1.4,
                                                hinge_type="top"))

    # segment 3
    wing_config.add_segment(
        length=L_s3,
        sweep=(45-2.5)*prop_s2_s3s2,
        tip_airfoil=Airfoil(chord=90, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4,
                  spare_support_dimension_height=4,
                  spare_mode="follow"),
            Spare(spare_support_dimension_width=2,
                  spare_support_dimension_height=2,
                  spare_mode="follow"),],
        trailing_edge_device=TrailingEdgeDevice(name="aileron",
                                                rel_chord_root=0.8,
                                                rel_chord_tip=0.8,
                                                hinge_spacing=0.5,
                                                side_spacing_root=0.,
                                                side_spacing_tip=3.,
                                                servo=None,
                                                servo_placement='top',
                                                rel_chord_servo_position=0.29,
                                                rel_length_servo_position=0.2,
                                                positive_deflection_deg=25,
                                                negative_deflection_deg=25,
                                                trailing_edge_offset_factor=1.4,
                                                hinge_type="top"))

    wing_config.add_segment(
        length=20,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=70-2.5, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4,
                  spare_support_dimension_height=4,
                  spare_mode="standard_backward"),
            Spare(spare_support_dimension_width=2,
                  spare_support_dimension_height=2,
                  spare_mode="standard_backward")],
    )

    # segment 4
    wing_config.add_tip_segment(
        length=5,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=60, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=5,
        sweep=10,
        tip_airfoil=Airfoil(chord=50, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=5,
        sweep=12.5,
        tip_airfoil=Airfoil(chord=40, dihedral=10, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=5,
        sweep=25,
        tip_airfoil=Airfoil(chord=20, dihedral=0, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    # wing_config.add_tip_segment(length=printer_wall_thickness,
    #                             sweep=1,
    #                             tip_type="flat"
    #                             )

    wing_configuration = {"main_wing": wing_config}

    # load the string
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             servo_information=servo_information,
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
