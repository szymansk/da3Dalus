import logging
import sys

import json
import os
from pathlib import Path

from Airplane.aircraft_topology.ComponentInformation import ComponentInformation
from Airplane.creator.ExportToStepCreator import ExportToStepCreator
from Airplane.aircraft_topology.ServoInformation import Servo, ServoInformation
from Airplane.creator import VaseModeWingCreator
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration, Spare, TrailingEdgeDevice

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.ConstructionRootNode import ConstructionRootNode
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Airplane.aircraft_topology.EngineInformation import Position, EngineInformation

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
    root_node = ConstructionRootNode(creator_id="RV-7-wing")
    pwd = os.path.curdir

    vase_wing_loft = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing", wing_index="main_wing",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    root_node.append(vase_wing_loft)

    vase_wing_loft_2 = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing_2", wing_index="main_wing_2",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    #root_node.append(vase_wing_loft_2)

    vase_wing_loft_3 = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing_3", wing_index="main_wing_3",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    #root_node.append(vase_wing_loft_3)

    vase_wing_loft_4 = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing_4", wing_index="main_wing_4",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    #root_node.append(vase_wing_loft_4)

    elevator = ConstructionStepNode(
        VaseModeWingCreator(creator_id="elevator", wing_index="elevator",
                            printer_wall_thickness=printer_wall_thickness,
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH", loglevel=logging.DEBUG))
    #root_node.append(elevator)

    # full_wing_loft = ConstructionStepNode(
    #    WingLoftCreator("wing_loft",
    #                    wing_index="main_wing",
    #                    wing_side="BOTH",
    #                    loglevel=logging.DEBUG))
    # root_node.append(full_wing_loft)
    #
    # fuselage_hull = ConstructionStepNode(
    #    StepImportCreator("fuselage_hull_imp",
    #                      step_file=os.path.abspath(f"../components/aircraft/RV-7/fuselage_inlets.step"),
    #                      scale=base_scale,
    #                      loglevel=logging.INFO))
    # root_node.append(fuselage_hull)
    #
    # cut_hull = ConstructionStepNode(
    #    Cut2ShapesCreator("cut_wing_from_fuselage",
    #                      minuend=fuselage_hull.creator_id,
    #                      subtrahend=f"{full_wing_loft.creator_id}",
    #                      loglevel=logging.INFO))
    # root_node.append(cut_hull)
    #

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[vase_wing_loft.creator_id,
                                              #f"{vase_wing_loft.creator_id}.flaps[1]",
                                              #f"{vase_wing_loft.creator_id}.aileron[2]"
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

    engine_info1 = EngineInformation(down_thrust=-2.5,
                                     side_thrust=-2.5,
                                     position=Position(0.0458 * 1000, 0, 0),
                                     length=0.0452 * 1000,
                                     width=0.035 * 1000,
                                     height=0.035 * 1000,
                                     screw_hole_circle=0.042 * 1000,
                                     mount_box_length=0.0133 * 2.5 * 1000,
                                     screw_din_diameter=0.0032 * 1000,
                                     screw_length=0.016 * 1000,
                                     rot_x=45)

    engine_information = {1: engine_info1}

    lipo_information = ComponentInformation(width=0.031 * 1000, height=0.035 * 1000, length=0.108 * 1000,
                                            trans_x=0.129 * 1000, trans_y=0.0, trans_z=-0.021 * 1000,
                                            rot_x=0.0, rot_y=0.0, rot_z=0)

    component_information = {"brushless": engine_info1, "lipo": lipo_information}

    #### WING ####
    airfoil = "../components/airfoils/naca2415.dat"
    wing_config = WingConfiguration(root_airfoil=airfoil,
                                    # tip_airfoil=airfoil2,
                                    nose_pnt=(192.113, 0, -44.5),
                                    root_chord=183,
                                    root_dihedral=3.7,
                                    root_incidence=0,
                                    length=50,
                                    sweep=0,
                                    tip_chord=183,
                                    tip_dihedral=0,
                                    tip_incidence=0,
                                    spare_list=[
                                        Spare(spare_support_dimension_width=6,
                                              spare_support_dimension_height=6,
                                              spare_vector=(0, 410, 37),
                                              spare_origin=(183 * 0.33, 0, -3)),
                                        Spare(spare_support_dimension_width=2,
                                              spare_support_dimension_height=12,
                                              spare_length=40,
                                              #spare_start=0,
                                              spare_vector=(0, 1, 0),
                                              spare_origin=(190 * 0.63, 0, 6))
                                    ])

    wing_config.add_segment(length=200,
                            sweep=0,
                            tip_chord=183,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=6,
                                      spare_support_dimension_height=6,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="flaps",
                                rel_chord_root=0.8,
                                rel_chord_tip=0.8,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=10,
                                negative_deflection_deg=50,
                                hinge_type="top",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='bottom',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45

                            )
                            )
    wing_config.add_segment(length=200,
                            sweep=0,
                            tip_chord=183,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=6,
                                      spare_support_dimension_height=6,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="aileron",
                                rel_chord_root=0.8,
                                rel_chord_tip=0.8,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=45,
                                negative_deflection_deg=25,
                                hinge_type="top",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='top',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.3
                            )
                            )

    wing_config.add_segment(length=100,
                            sweep=10,
                            tip_chord=183 - 20,
                            tip_dihedral=5,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=6,
                                      spare_support_dimension_height=6,
                                      spare_mode="follow")],
                            )

    wing_config.add_segment(length=50,
                            sweep=10,
                            tip_chord=183 - 40,
                            tip_dihedral=10,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")])
    wing_config.add_segment(length=50,
                            sweep=10,
                            tip_chord=183 - 80,
                            tip_dihedral=5,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            #tip_airfoil="../components/airfoils/nacam2.dat",
                            )

    wing_config.add_tip_segment(length=printer_wall_thickness,
                                sweep=1,
                                tip_chord=100,
                                tip_dihedral=0,
                                tip_incidence=0,
                                tip_airfoil="../components/airfoils/nacam2.dat",
                                number_interpolation_points=35,
                                tip_type="flat"
                                )
    ##### WING_2 ####
    wing_config_2 = WingConfiguration(root_airfoil="../components/airfoils/a18.dat",
                                    # tip_airfoil=airfoil2,
                                    nose_pnt=(0, 0, 0),
                                    root_chord=150,
                                    root_dihedral=10,
                                    root_incidence=3,
                                    length=50,
                                    sweep=0,
                                    tip_chord=150,
                                    tip_dihedral=0,
                                    tip_incidence=0,
                                    number_interpolation_points=301,
                                    spare_list=[
                                        Spare(spare_support_dimension_width=3,
                                              spare_support_dimension_height=3,
                                              spare_position_factor=0.25,
                                              #spare_vector=None,#(0, 550, 0),
                                              #spare_origin=(150 * 0.25, 0, 5.4)
                                              )
                                    ])
    wing_config_2.add_segment(length=250,
                            sweep=25/2.,
                            tip_chord=125,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="flaps",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=10,
                                negative_deflection_deg=50,
                                hinge_type="top",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='top',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            ),
                              tip_airfoil="../components/airfoils/a18.dat"
                            )

    wing_config_2.add_segment(length=250,
                            sweep=25/2.,
                            tip_chord=100,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="standard_backward")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="aileron",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=25,
                                negative_deflection_deg=25,
                                hinge_type="middle",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='bottom',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            ),
                              tip_airfoil="../components/airfoils/a18.dat"
                            )

    ##### WING_3 ####
    wing_config_3 = WingConfiguration(root_airfoil="../components/airfoils/naca2415.dat",
                                    # tip_airfoil=airfoil2,
                                    nose_pnt=(-250, 0, 0),
                                    root_chord=150,
                                    root_dihedral=0,
                                    root_incidence=3,
                                    length=50,
                                    sweep=0,
                                    tip_chord=150,
                                    tip_dihedral=0,
                                    tip_incidence=2,
                                    #number_interpolation_points=301,
                                    spare_list=[
                                        Spare(spare_support_dimension_width=3,
                                              spare_support_dimension_height=3,
                                              spare_vector=None,#(0, 550, 0),
                                              spare_origin=(150 * 0.33, 0, 5))
                                    ])
    wing_config_3.add_segment(length=250,
                            sweep=25,#25/2.,
                            tip_chord=125,
                            tip_dihedral=3,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="flaps",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=10,
                                negative_deflection_deg=50,
                                hinge_type="top",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='top',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            )
                            )

    wing_config_3.add_segment(length=250,
                            sweep=25,#25/2.,
                            tip_chord=100,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="aileron",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=25,
                                negative_deflection_deg=25,
                                hinge_type="middle",
                                servo=Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            cable_z=26),
                                servo_placement='bottom',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            )
                            )

    ##### WING_4 ####
    wing_config_4 = WingConfiguration(root_airfoil="../components/airfoils/naca2415.dat",
                                    # tip_airfoil=airfoil2,
                                    nose_pnt=(-450, 0, 0),
                                    root_chord=150,
                                    root_dihedral=10,
                                    root_incidence=5,
                                    length=50,
                                    sweep=5,
                                    tip_chord=145,
                                    tip_dihedral=0,
                                    tip_incidence=0,
                                    #number_interpolation_points=301,
                                    spare_list=[
                                        Spare(spare_support_dimension_width=3,
                                              spare_support_dimension_height=3,
                                              spare_position_factor=0.25
                                              #spare_vector=None,#(0, 550, 0),
                                              #spare_origin=(150 * 0.33, 0, 5)
    )
                                    ])
    wing_config_4.add_segment(length=250,
                            sweep=10,#25/2.,
                            tip_chord=125,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="flaps",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=10,
                                negative_deflection_deg=50,
                                hinge_type="top",
                                servo= None, #Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                            #latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                            #cable_z=26),
                                servo_placement='top',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            )
                            )

    wing_config_4.add_segment(length=250,
                            sweep=10,#25/2.,
                            tip_chord=100,
                            tip_dihedral=0,
                            tip_incidence=0,
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      spare_mode="follow")],
                            trailing_edge_device=
                            TrailingEdgeDevice(
                                name="aileron",
                                rel_chord_root=0.9,
                                rel_chord_tip=0.9,
                                hinge_spacing=0.5,
                                side_spacing=1.,
                                trailing_edge_offset_factor=1.4,
                                positive_deflection_deg=25,
                                negative_deflection_deg=25,
                                hinge_type="middle",
                                servo=None,#Servo(length=23, width=12.5, height=31.5, leading_length=6,
                                           # latch_z=14.5, latch_x=7.25, latch_thickness=2.6, latch_length=6,
                                           # cable_z=26),
                                servo_placement='bottom',
                                rel_chord_servo_position=0.43,
                                rel_length_servo_position=0.45
                            )
                            )

    ##### RUDDER ####
    rudder_airfoil = "../components/airfoils/naca0008.dat"
    elevator_config = WingConfiguration(root_airfoil=rudder_airfoil,
                                        # tip_airfoil=airfoil2,
                                        nose_pnt=(593.573, 0, 31.608),
                                        root_chord=122,
                                        root_dihedral=0,
                                        root_incidence=0,
                                        length=165,
                                        sweep=29,
                                        tip_chord=76,
                                        tip_dihedral=0,
                                        tip_incidence=0,
                                        spare_list=[
                                            Spare(spare_support_dimension_width=2,
                                                  spare_support_dimension_height=2,
                                                  spare_vector=(0, 1, 0),
                                                  spare_origin=(122 * 0.3, 0, 0)),
                                            Spare(spare_support_dimension_width=2,
                                                  spare_support_dimension_height=2,
                                                  spare_length=30,
                                                  spare_vector=(0, 1, 0),
                                                  spare_origin=(122 * 0.5, 0, 0))
                                        ],
                                        trailing_edge_device=TrailingEdgeDevice(
                                            name="elevator",
                                            rel_chord_root=(122. - 47.) / 122.,
                                            rel_chord_tip=(122. - 47. - 29.) / 76.,
                                            hinge_spacing=0.5,
                                            side_spacing=0.,
                                            trailing_edge_offset_factor=1.,
                                            positive_deflection_deg=30,
                                            negative_deflection_deg=30,
                                            hinge_type="top"
                                        )
                                        )

    #elevator_config.add_segment(length=165 - 7.6,
    #                        sweep=29. ,#- (29./165.) * 7.6,
    #                        tip_chord=76,
    #                        tip_dihedral=0,
    #                        tip_incidence=0,
    #                        spare_list=[
    #                            Spare(spare_support_dimension_width=2.,
    #                                  spare_support_dimension_height=2.,
    #                                  spare_mode="follow")]
    #                        ,
    #                        trailing_edge_device=TrailingEdgeDevice(
    #                            name="elevator",
    #                            rel_chord_root=(122. - 47.) / 122.,
    #                            rel_chord_tip=(122. - 47. - 29.) / 76.,
    #                            hinge_spacing=0.5,
    #                            side_spacing=0.,
    #                            trailing_edge_offset_factor=1.,
    #                            positive_deflection_deg=30,
    #                            negative_deflection_deg=30,
    #                            hinge_type="top"
    #                        )
    #                        )
    wing_configuration = {"main_wing": wing_config,
                          "main_wing_2": wing_config_2,
                          "main_wing_3": wing_config_3,
                          "main_wing_4": wing_config_4,
                          "elevator": elevator_config}

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
