import logging
import sys
import os

import json
from pathlib import Path
from typing import Optional

import math
from cadquery import Vector

from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder, GeneralJSONEncoder, WingLoftCreator
from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode

from cad_designer.airplane.aircraft_topology.printer3d import Printer3dSettings
from cad_designer.airplane.aircraft_topology.wing import Spare, WingConfiguration
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.creator.export_import import ExportToStepCreator
from cad_designer.airplane.creator.wing import VaseModeWingCreator
from cad_designer.aerosandbox.convert2aerosandbox import export_asb_wing_to_stl

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
    root_node = ConstructionRootNode(creator_id="configurator-test-wing")
    pwd = os.path.curdir

    loft_only = True
    if loft_only:
        vase_wing_loft = ConstructionStepNode(
            WingLoftCreator(creator_id="wing_loft",
                            wing_index="main_wing",
                            wing_side="BOTH",
                            loglevel=logging.DEBUG))
    else:
        vase_wing_loft = ConstructionStepNode(
            VaseModeWingCreator(creator_id="vase_wing",
                                wing_index="main_wing",
                                leading_edge_offset_factor=leading_edge_offset,
                                trailing_edge_offset_factor=trailing_edge_offset,
                                minimum_rib_angle=minimum_rib_angle,
                                wing_side="BOTH",
                                loglevel=logging.DEBUG))
    root_node.append(vase_wing_loft)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(f"{root_node.identifier}").stem,
                            file_path="../exports",
                            shapes_to_export=[vase_wing_loft.creator_id]
                            ))
    root_node.append(aircraft_step_export_node)



    #####################
    #####################
    #####################

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    #### WING ####
    airfoil = "../components/airfoils/naca0010.dat"
    # segment 0
    wing_config: WingConfiguration = WingConfiguration(nose_pnt=(100, 0, 0),
                                                       root_airfoil=Airfoil(
                                                           airfoil=airfoil,
                                                           chord=200.,
                                                           dihedral_as_rotation_in_degrees=8,
                                                           #dihedral_as_translation=50,
                                                           incidence=0,
                                                           rotation_point_rel_chord=0.25),
                                                       length=500.,
                                                       sweep=10,
                                                       sweep_is_angle=True,
                                                       tip_airfoil=Airfoil(
                                                           chord=200.,
                                                           dihedral_as_rotation_in_degrees=-8,
                                                           #dihedral_as_translation=-100,
                                                           incidence=5,
                                                           rotation_point_rel_chord=0.25),
                                                       #number_interpolation_points=201,
                                                       spare_list=[
            Spare(spare_support_dimension_width=3,
                  spare_support_dimension_height=3,
                  spare_position_factor=0.25),
        ])
    wing_config.add_segment(length=500, sweep=-10, sweep_is_angle= True,
                            tip_airfoil=Airfoil(chord=150, dihedral_as_rotation_in_degrees=8, incidence=-10, rotation_point_rel_chord=0.25),
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      # spare_mode="follow"
                                      ),
                            ])
    wing_config.add_segment(length=500, sweep=10, sweep_is_angle= True,
                            tip_airfoil=Airfoil(chord=100, dihedral_as_rotation_in_degrees=0, incidence=0, rotation_point_rel_chord=0.25),
                            spare_list=[
                                Spare(spare_support_dimension_width=3,
                                      spare_support_dimension_height=3,
                                      # spare_mode="follow"
                                      ),
                            ])

    asb_wing = wing_config.asb_wing()
    export_asb_wing_to_stl(asb_wing, f"../exports/{vase_wing_loft.creator_id}_asb.stl")

    wing_configuration = {"main_wing": wing_config}

    printer_settings = Printer3dSettings(layer_height=0.24,
                                         wall_thickness=0.42,
                                         rel_gap_wall_thickness=0.075)

    # load the string
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             wing_config=wing_configuration,
                                             printer_settings=printer_settings)

    # dump wingconfig
    import jsonpickle

    wing_pickled = jsonpickle.encode(wing_config, indent=2)
    print(wing_pickled)

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
