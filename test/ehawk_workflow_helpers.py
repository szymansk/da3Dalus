from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cadquery import Vector

from cad_designer.airplane import ConstructionStepNode
from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
from cad_designer.airplane.aircraft_topology.airplane.AirplaneConfiguration import AirplaneConfiguration
from cad_designer.airplane.aircraft_topology.components import Servo, ServoInformation
from cad_designer.airplane.aircraft_topology.printer3d import Printer3dSettings
from cad_designer.airplane.aircraft_topology.wing import Spare, TrailingEdgeDevice, WingConfiguration
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.creator.cad_operations import FuseMultipleShapesCreator
from cad_designer.airplane.creator.export_import import ExportToStepCreator
from cad_designer.airplane.creator.wing import StandWingSegmentOnPrinterCreator, VaseModeWingCreator


@dataclass
class EhawkWorkflowContext:
    root_node: ConstructionRootNode
    main_wing: WingConfiguration
    airplane_configuration: AirplaneConfiguration
    servo_information: dict[int, ServoInformation]
    printer_settings: Printer3dSettings


def straight_trailing_edge(
    l_middle: Optional[float],
    l_tip: Optional[float],
    s_middle: Optional[float],
    s_tip: Optional[float],
    c_root: Optional[float],
    c_middle: Optional[float],
    c_tip: Optional[float],
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Compute the missing middle chord when trailing-edge points are collinear."""
    if c_middle is None:
        total_length = l_middle + l_tip
        root_te = Vector(c_root, 0)
        middle_le = Vector(s_middle, l_middle)
        tip_te = Vector(c_tip + s_middle + s_tip, total_length)

        root_to_tip_te = tip_te - root_te
        root_to_middle_te = root_to_tip_te * l_middle / total_length
        middle_te = root_to_middle_te + root_te

        middle_chord_vector = middle_te - middle_le
        c_middle = math.sqrt(middle_chord_vector.dot(middle_chord_vector))

    return l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip


def build_ehawk_workflow(repo_root: Path, export_dir: Path) -> EhawkWorkflowContext:
    airfoil_path = str((repo_root / "components" / "airfoils" / "mh32.dat").resolve())

    main_wing = _build_main_wing(airfoil_path)
    elevator_wing = _build_elevator_wing(airfoil_path)

    airplane_configuration = AirplaneConfiguration(
        name="eHawk",
        total_mass_kg=0.6,
        wings=[main_wing, elevator_wing],
        fuselages=None,
    )

    root_node = _build_construction_root(export_dir)

    return EhawkWorkflowContext(
        root_node=root_node,
        main_wing=main_wing,
        airplane_configuration=airplane_configuration,
        servo_information=_build_servo_information(),
        printer_settings=Printer3dSettings(layer_height=0.24, wall_thickness=0.42, rel_gap_wall_thickness=0.075),
    )


def _build_construction_root(export_dir: Path) -> ConstructionRootNode:
    leading_edge_offset = 0.1
    trailing_edge_offset = 0.15
    minimum_rib_angle = 45

    root_node = ConstructionRootNode(creator_id="eHawk-wing")

    vase_wing_loft = ConstructionStepNode(
        VaseModeWingCreator(
            creator_id="vase_wing",
            wing_index="main_wing",
            leading_edge_offset_factor=leading_edge_offset,
            trailing_edge_offset_factor=trailing_edge_offset,
            minimum_rib_angle=minimum_rib_angle,
            wing_side="BOTH",
        )
    )
    root_node.append(vase_wing_loft)

    winglet = ConstructionStepNode(
        FuseMultipleShapesCreator(
            creator_id="winglet",
            shapes=[
                "vase_wing[6]",
                "vase_wing[7]",
                "vase_wing[8]",
                "vase_wing[9]",
                "vase_wing[10]",
                "vase_wing[11]",
            ],
        )
    )
    vase_wing_loft.append(winglet)

    print_stand = ConstructionStepNode(
        StandWingSegmentOnPrinterCreator(
            creator_id="stand_wing_to_print",
            wing_index="main_wing",
            shape_dict={
                0: "vase_wing[0]",
                1: "vase_wing[1]",
                2: "vase_wing[2]",
                3: "vase_wing[3]",
                4: "vase_wing[4]",
                5: "vase_wing[5]",
                6: "winglet",
            },
        )
    )
    vase_wing_loft.append(print_stand)

    aircraft_step_export_node = ConstructionStepNode(
        ExportToStepCreator(
            Path(f"{root_node.identifier}").stem,
            file_path=str(export_dir),
            shapes_to_export=[
                vase_wing_loft.creator_id,
                f"{vase_wing_loft.creator_id}[0].print",
                f"{vase_wing_loft.creator_id}[1].print",
                f"{vase_wing_loft.creator_id}[2].print",
                f"{vase_wing_loft.creator_id}[3].print",
                f"{winglet.creator_id}.print",
                f"{vase_wing_loft.creator_id}.aileron[2]",
                f"{vase_wing_loft.creator_id}.aileron[3]",
                f"{vase_wing_loft.creator_id}.aileron[2]*",
                f"{vase_wing_loft.creator_id}.aileron[3]*",
                f"{vase_wing_loft.creator_id}[2].servo_mount",
            ],
        )
    )
    root_node.append(aircraft_step_export_node)

    return root_node


def _build_servo_information() -> dict[int, ServoInformation]:
    servo_aileron = ServoInformation(
        height=0,
        width=0,
        length=0,
        lever_length=0,
        servo=Servo(
            length=23,
            width=12.5,
            height=31.5,
            leading_length=6,
            latch_z=14.5,
            latch_x=7.25,
            latch_thickness=2.6,
            latch_length=6,
            cable_z=26,
            screw_hole_lx=0,
            screw_hole_d=0,
        ),
    )

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
        trans_z=0.044 * 1000 - 0.0244 * 1000,
    )
    return {1: servo_aileron, 2: servo_rudder}


def _build_main_wing(airfoil_path: str) -> WingConfiguration:
    wing_config = WingConfiguration(
        nose_pnt=(0, 0, 0),
        root_airfoil=Airfoil(airfoil=airfoil_path, chord=162.0, dihedral_as_rotation_in_degrees=1, incidence=0),
        length=20.0,
        sweep=0,
        tip_airfoil=Airfoil(chord=162.0, incidence=0),
        number_interpolation_points=201,
        spare_list=[
            Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_position_factor=0.25),
            Spare(
                spare_support_dimension_width=6.42,
                spare_support_dimension_height=6.42,
                spare_position_factor=0.55,
                spare_vector=(0.0, 1.0, 0.0),
                spare_length=70,
            ),
            Spare(
                spare_support_dimension_width=6.42,
                spare_support_dimension_height=6.42,
                spare_position_factor=0.2,
                spare_vector=(0.0, 1.0, 0.0),
                spare_length=70,
            ),
        ],
    )

    wing_config.add_segment(
        length=200,
        sweep=2.5,
        tip_airfoil=Airfoil(chord=157, incidence=0),
        spare_list=[
            Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_mode="follow"),
            Spare(
                spare_support_dimension_width=6.42,
                spare_support_dimension_height=6.42,
                spare_mode="follow",
                spare_length=60,
            ),
            Spare(
                spare_support_dimension_width=6.42,
                spare_support_dimension_height=6.42,
                spare_mode="follow",
                spare_length=60,
            ),
        ],
    )

    l_middle = 250
    l_tip = 200
    s_middle = 8
    s_tip = 38 - 8
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(
        l_middle,
        l_tip,
        s_middle,
        s_tip,
        c_root,
        c_middle,
        c_tip,
    )

    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, incidence=0),
        spare_list=[Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(
            name="aileron",
            rel_chord_root=0.8,
            rel_chord_tip=0.8,
            hinge_spacing=0.5,
            side_spacing_root=2.0,
            side_spacing_tip=2.0,
            servo=1,
            servo_placement="top",
            rel_chord_servo_position=0.414,
            rel_length_servo_position=0.486,
            positive_deflection_deg=35,
            negative_deflection_deg=35,
            trailing_edge_offset_factor=1.2,
            hinge_type="top",
            symmetric=False,
        ),
    )

    l_middle = 75
    l_tip = l_tip - 75
    s_middle = 13 - 8
    s_tip = 38 - 13
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(
        l_middle,
        l_tip,
        s_middle,
        s_tip,
        c_root,
        c_middle,
        c_tip,
    )

    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, incidence=0),
        spare_list=[Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron"),
    )

    l_middle = 85
    l_tip = l_tip - 85
    s_middle = 24 - 13
    s_tip = 38 - 24 - 2
    c_root = wing_config.segments[-1].tip_airfoil.chord
    c_middle = None
    c_tip = 90
    l_middle, l_tip, s_middle, s_tip, c_root, c_middle, c_tip = straight_trailing_edge(
        l_middle,
        l_tip,
        s_middle,
        s_tip,
        c_root,
        c_middle,
        c_tip,
    )

    wing_config.add_segment(
        length=l_middle,
        sweep=s_middle,
        tip_airfoil=Airfoil(chord=c_middle, incidence=0),
        spare_list=[Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron"),
    )

    wing_config.add_segment(
        length=l_tip,
        sweep=s_tip,
        tip_airfoil=Airfoil(chord=c_tip, incidence=0),
        spare_list=[Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_mode="follow")],
        trailing_edge_device=TrailingEdgeDevice(name="aileron"),
    )

    wing_config.add_segment(
        length=20,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=90 - 7.5 - 3, dihedral_as_rotation_in_degrees=5, incidence=0),
        spare_list=[
            Spare(
                spare_support_dimension_width=4.42,
                spare_support_dimension_height=4.42,
                spare_mode="standard_backward",
            )
        ],
    )

    wing_config.add_tip_segment(
        length=15,
        sweep=7.5,
        tip_airfoil=Airfoil(chord=90 - 2 * 7.5 - 4, dihedral_as_rotation_in_degrees=5, incidence=0),
        tip_type="flat",
    )

    wing_config.add_tip_segment(
        length=15,
        sweep=10,
        tip_airfoil=Airfoil(chord=90 - 2 * 7.5 - 10 - 3, dihedral_as_rotation_in_degrees=5, incidence=0),
        tip_type="flat",
    )

    wing_config.add_tip_segment(
        length=15,
        sweep=12.5,
        tip_airfoil=Airfoil(chord=90 - 2 * 7.5 - 10 - 12.5, dihedral_as_rotation_in_degrees=10, incidence=0),
        tip_type="flat",
    )

    wing_config.add_tip_segment(
        length=10,
        sweep=15,
        tip_airfoil=Airfoil(chord=90 - 2 * 7.5 - 10 - 12.5 - 15 + 3, dihedral_as_rotation_in_degrees=15, incidence=0),
        tip_type="flat",
    )

    wing_config.add_tip_segment(
        length=5,
        sweep=17.5,
        tip_airfoil=Airfoil(chord=90 - 2 * 7.5 - 10 - 12.5 - 15 - 17.5 + 4, incidence=0),
        tip_type="flat",
    )

    return wing_config


def _build_elevator_wing(airfoil_path: str) -> WingConfiguration:
    return WingConfiguration(
        nose_pnt=(650, 0, 0),
        root_airfoil=Airfoil(
            airfoil=airfoil_path,
            chord=85.0,
            dihedral_as_rotation_in_degrees=45,
            incidence=-2,
        ),
        length=210.0,
        sweep=15,
        tip_airfoil=Airfoil(chord=85.0 - 15, incidence=0),
        number_interpolation_points=201,
        spare_list=[
            Spare(spare_support_dimension_width=4.42, spare_support_dimension_height=4.42, spare_position_factor=0.25),
            Spare(
                spare_support_dimension_width=6.42,
                spare_support_dimension_height=6.42,
                spare_position_factor=0.55,
                spare_vector=(0.0, 1.0, 0.0),
                spare_length=70,
            ),
        ],
        trailing_edge_device=TrailingEdgeDevice(
            name="v-tail",
            rel_chord_root=50 / 85,
            rel_chord_tip=50 / 85,
            hinge_spacing=0.5,
            side_spacing_root=2.0,
            side_spacing_tip=2.0,
            positive_deflection_deg=35,
            negative_deflection_deg=35,
            trailing_edge_offset_factor=1.2,
            hinge_type="top",
            symmetric=False,
        ),
    )
