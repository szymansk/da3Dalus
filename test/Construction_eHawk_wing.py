import logging
import sys
import os

import json
from pathlib import Path
from typing import Optional

import math
from cadquery import Vector

from airplane.ConstructionStepNode import ConstructionStepNode
from airplane.ConstructionRootNode import ConstructionRootNode
from airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

from airplane.aircraft_topology.components import *
from airplane.aircraft_topology.Position import Position
from airplane.aircraft_topology.printer3d import Printer3dSettings
from airplane.aircraft_topology.wing import *
from airplane.aircraft_topology.wing.Airfoil import Airfoil
from airplane.creator.components import *
from airplane.creator.export_import import *
from airplane.creator.fuselage import *
from airplane.creator.cad_operations import *
from airplane.creator.wing import *

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

def straight_trailing_edge(l_middle: Optional[float],
                           l_tip: Optional[float],
                           s_middle: Optional[float],
                           s_tip: Optional[float],
                           c_root: Optional[float],
                           c_middle: Optional[float],
                           c_tip: Optional[float]):
    """
    We want to calculate the missing value. All points on the trailing edge are on one line
    """
    if c_middle is None:
        L = l_middle + l_tip
        P_r_le = Vector(0, 0)
        P_r_te = Vector(c_root, 0)
        P_m_le = Vector(s_middle, l_middle)
        P_t_te= Vector(c_tip + s_middle + s_tip, L)
        P_t_le = Vector(s_middle + s_tip, L)

        L_rte_tte = P_t_te - P_r_te
        L_rte_mte = L_rte_tte * l_middle / L
        P_m_te= L_rte_mte + P_r_te

        L_mle_mte = P_m_te - P_m_le
        c_middle = math.sqrt(L_mle_mte.dot(L_mle_mte))

    return (l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip)

if __name__ == "__main__":

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)

    leading_edge_offset: float = 0.1  # value between (0,1) as fraction of the chord
    trailing_edge_offset: float = 0.15  # value between (0,1) as fraction of the chord
    minimum_rib_angle: float = 45

    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="eHawk-wing")
    pwd = os.path.curdir

    vase_wing_loft = ConstructionStepNode(
        VaseModeWingCreator(creator_id="vase_wing",
                            wing_index="main_wing",
                            leading_edge_offset_factor=leading_edge_offset,
                            trailing_edge_offset_factor=trailing_edge_offset,
                            minimum_rib_angle=minimum_rib_angle,
                            wing_side="BOTH",
                            loglevel=logging.DEBUG))
    root_node.append(vase_wing_loft)

    winglet = ConstructionStepNode(
        FuseMultipleShapesCreator(
            creator_id="winglet",
            shapes= ['vase_wing[6]',
                     'vase_wing[7]',
                     'vase_wing[8]',
                     'vase_wing[9]',
                     'vase_wing[10]',
                     'vase_wing[11]']
        )
    )
    vase_wing_loft.append(winglet)

    print_stand = ConstructionStepNode(
        StandWingSegmentOnPrinterCreator(
            creator_id="",
            wing_index="main_wing",
            shape_dict= {
                0 : "vase_wing[0]",
                1 : "vase_wing[1]",
                2 : "vase_wing[2]",
                3 : "vase_wing[3]",
                4 : "winglet"},
            loglevel=logging.DEBUG))
    #vase_wing_loft.append(print_stand)

    aircraft_3mf_export_node = ConstructionStepNode(
        ExportTo3mfCreator(Path(f"{root_node.identifier}_3mf").stem,
                            angular_tolerance=0.01,
                            tolerance=0.05,
                            file_path="../exports",
                            shapes_to_export=[#vase_wing_loft.creator_id,
                                              f"{vase_wing_loft.creator_id}[0].print",
                                              f"{vase_wing_loft.creator_id}[1].print",
                                              f"{vase_wing_loft.creator_id}[2].print",
                                              f"{vase_wing_loft.creator_id}[3].print",
                                              f"{winglet.creator_id}.print",
                                              #f"{vase_wing_loft.creator_id}.aileron[2]",
                                              #f"{vase_wing_loft.creator_id}.aileron[3]",
                                              #f"{vase_wing_loft.creator_id}.aileron[2]*",
                                              #f"{vase_wing_loft.creator_id}.aileron[3]*"
                                              ]))
    #root_node.append(aircraft_3mf_export_node)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[vase_wing_loft.creator_id,
                                              f"{vase_wing_loft.creator_id}[0].print",
                                              f"{vase_wing_loft.creator_id}[1].print",
                                              f"{vase_wing_loft.creator_id}[2].print",
                                              f"{vase_wing_loft.creator_id}[3].print",
                                              f"{winglet.creator_id}.print",
                                              f"{vase_wing_loft.creator_id}.aileron[2]",
                                              f"{vase_wing_loft.creator_id}.aileron[3]",
                                              f"{vase_wing_loft.creator_id}.aileron[2]*",
                                              f"{vase_wing_loft.creator_id}.aileron[3]*"
                                              ]))
    #root_node.append(aircraft_step_export_node)
    #aircraft_step_export_node.append(aircraft_3mf_export_node)


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
    # segment 0
    wing_config: WingConfiguration = WingConfiguration(
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
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_position_factor=0.25),
            Spare(spare_support_dimension_width=6.42,
                  spare_support_dimension_height=6.42,
                  spare_position_factor=0.55,
                  spare_vector=(0.,1.,0.),
                  spare_length=70),
            Spare(spare_support_dimension_width=6.42,
                  spare_support_dimension_height=6.42,
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
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="follow"),
            Spare(spare_support_dimension_width=6.42,
                  spare_support_dimension_height=6.42,
                  spare_mode="follow",
                  spare_length=60),
            Spare(spare_support_dimension_width=6.42,
                  spare_support_dimension_height=6.42,
                  spare_mode="follow",
                  spare_length=60)
        ])

    l_middle = 250
    l_tip = 200
    s_middle = 8
    s_tip = 38 - 8
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip)

    # segment 2
    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(
            name="aileron",
            rel_chord_root=0.8,
            rel_chord_tip=0.8,
            hinge_spacing=0.5,
            side_spacing_root=2.,
            side_spacing_tip=2.,
            servo=Servo(length=23,
                        width=12.5,
                        height=31.5,
                        leading_length=6, latch_z=14.5,
                        latch_x=7.25, latch_thickness=2.6,
                        latch_length=6, cable_z=26,
                        screw_hole_lx=None,
                        screw_hole_d=None),
            servo_placement='top',
            rel_chord_servo_position=0.414,
            rel_length_servo_position=0.486,
            positive_deflection_deg=35,
            negative_deflection_deg=35,
            trailing_edge_offset_factor=1.2,
            hinge_type="top")
    )

    l_middle = 75
    l_tip = l_tip - 75
    s_middle = 13 - 8
    s_tip = 38 - 13
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip)

    # segment 3
    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron")
    )

    l_middle = 75
    l_tip = l_tip - 75
    s_middle = 24-13
    s_tip = 38-24
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip)

    # segment 4
    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron")
    )

    #segment 5
    wing_config.add_segment(
        length=l_tip,
        sweep=s_tip,
        tip_airfoil=Airfoil(chord=c_tip, dihedral=0, incidence=0, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron")
    )

    # here we start with the winglet
    wing_config.add_segment(
        length=20,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=90-7.5-3, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42,
                  spare_support_dimension_height=4.42,
                  spare_mode="standard_backward")],
    )

    # segment 7
    wing_config.add_tip_segment(
        length=15,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=90-2*7.5-4, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=15,
        sweep=10,
        tip_airfoil=Airfoil(chord=90-2*7.5-10-3, dihedral=5, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=15,
        sweep=12.5,
        tip_airfoil=Airfoil(chord=90-2*7.5-10-12.5, dihedral=10, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=10,
        sweep=15,
        tip_airfoil=Airfoil(chord=90-2*7.5-10-12.5-15+3, dihedral=15, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    wing_config.add_tip_segment(
        length=5,
        sweep=17.5,
        tip_airfoil=Airfoil(chord=90-2*7.5-10-12.5-15-17.5+4, dihedral=0, incidence=-0.5, rotation_point_rel_chord=0),
        tip_type='flat'
    )

    # wing_config.add_tip_segment(length=printer_wall_thickness,
    #                             sweep=1,
    #                             tip_type="flat"
    #                             )

    wing_configuration = {"main_wing": wing_config}

    printer_settings = Printer3dSettings(layer_height=0.24,
                                         wall_thickness=0.42,
                                         rel_gap_wall_thickness=0.075)


    # load the string
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             servo_information=servo_information,
                                             wing_config=wing_configuration,
                                             printer_settings=printer_settings)

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
