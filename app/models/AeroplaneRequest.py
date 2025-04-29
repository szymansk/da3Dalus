import json
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union, OrderedDict, Literal

from pydantic import BaseModel, Json

from app.models.Printer3dSettings import Printer3dSettings
from app.models.Servo import Servo
from app.models.wing import Wing


class Fuselage(BaseModel):
    pass


class ServoSettings(BaseModel):
    height: float
    width: float
    length: float
    lever_length: float

    rot_x: float = 0.0
    rot_y: float = 0.0
    rot_z: float = 0.0

    trans_x: float = 0.0
    trans_y: float = 0.0
    trans_z: float = 0.0,

    servo: Optional[Servo]

class AeroplaneSettings(BaseModel):
    printer_settings: Optional[Printer3dSettings]
    servo_information: Optional[Dict[int, ServoSettings]]

class CreatorUrlType(str, Enum):
    WING_LOFT = "wing_loft"
    VASE_MODE_WING = "vase_mode_wing"

class ExporterUrlType(str, Enum):
    STL = "stl"
    STEP = "step"
    AMF = "amf"
    IGES = "iges"

class CreateWingLoftRequest(BaseModel):
    wings: Optional[Dict[str, Wing]]
    settings: Optional[AeroplaneSettings]

    class Config:
        json_encoders = {
            dict: lambda v: json.dumps(v, sort_keys=False)
        }

        json_schema_extra = {
            "example": {
                "wings": {
                    "main_wing": {
                        "segments": [
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 1,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0.3
                                },
                                "length": 20.0,
                                "sweep": 0,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [0.03673996532422339, 0.9992005450970961, 0.0157621580261394
                                                         ],
                                        "spare_origin": [
                                            40.5,
                                            -0.04546757240303877,
                                            2.604835478413867
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.55,
                                        "spare_length": 70,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            89.10000000000001,
                                            -0.0469884150916505,
                                            2.6919644976908543
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.2,
                                        "spare_length": 70,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            32.4,
                                            -0.04157221844287501,
                                            2.3816707994978588
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 200,
                                "sweep": 2.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            41.23479930648447,
                                            19.938543329538884,
                                            2.9200786389366553
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": 60,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            89.10000000000001,
                                            19.95301158490835,
                                            2.6919644976908543
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": 60,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            32.4,
                                            19.958427781557123,
                                            2.3816707994978588
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 250,
                                "sweep": 8,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            48.58279237132915,
                                            219.7786523489581,
                                            6.072510244164535
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "rel_chord_root": 0.8,
                                    "rel_chord_tip": 0.8,
                                    "hinge_spacing": 0.5,
                                    "side_spacing_root": 2.0,
                                    "side_spacing_tip": 2.0,
                                    "servo": 1,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": 0.414,
                                    "rel_length_servo_position": 0.486,
                                    "positive_deflection_deg": 35,
                                    "negative_deflection_deg": 35,
                                    "trailing_edge_offset_factor": 1.2,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 75,
                                "sweep": 5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            57.767783702384996,
                                            469.57878862323213,
                                            10.013049750699386
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 85,
                                "sweep": 11,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            60.52328110170175,
                                            544.5188295055143,
                                            11.19521160265984
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 40,
                                "sweep": 12,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            63.64617815426074,
                                            629.4508758387675,
                                            12.534995034881689
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 20,
                                "sweep": 7.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard_backward",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            65.11577676722968,
                                            669.4188976426514,
                                            13.165481355927264
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 7.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 10,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 12.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 10,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 10,
                                "sweep": 15,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 15,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 5,
                                "sweep": 17.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 24.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            }
                        ],
                        "nose_pnt": [
                            0,
                            0,
                            0
                        ]
                    },
                },
                "settings": {
                    "servo_information": {
                        "1": {
                            "height": 0,
                            "width": 0,
                            "length": 0,
                            "lever_length": 0,
                            "rot_x": 0.0,
                            "rot_y": 0.0,
                            "rot_z": 0.0,
                            "trans_x": 0.0,
                            "trans_y": 0.0,
                            "trans_z": 0.0,
                            "servo": {
                                "length": 23,
                                "width": 12.5,
                                "height": 31.5,
                                "leading_length": 6,
                                "latch_z": 14.5,
                                "latch_x": 7.25,
                                "latch_thickness": 2.6,
                                "latch_length": 6,
                                "cable_z": 26,
                                "screw_hole_lx": 0,
                                "screw_hole_d": 0
                            }
                        }
                    },
                    "printer_settings": {
                        "layer_height": 0.24,
                        "wall_thickness": 0.42,
                        "rel_gap_wall_thickness": 0.075
                    }
                }
            }
        }


class CreateAeroPlaneRequest(BaseModel):
    blueprint: Union[Path, Any]
    wings: Optional[Dict[str, Wing]]
    fuselages: Optional[OrderedDict[str, Fuselage]]
    settings: Optional[AeroplaneSettings]

    class Config:
        json_encoders = {
            dict: lambda v: json.dumps(v, sort_keys=False)
        }

        json_schema_extra = {
            "example": {
                "blueprint": {
                    "successors": {
                        "avase_wing": {
                            "successors": {
                                "a_winglet": {
                                    "successors": {},
                                    "creator": {
                                        "shapes": [
                                            "avase_wing[6]",
                                            "avase_wing[7]",
                                            "avase_wing[8]",
                                            "avase_wing[9]",
                                            "avase_wing[10]",
                                            "avase_wing[11]"
                                        ],
                                        "loglevel": 20,
                                        "creator_id": "a_winglet",
                                        "$TYPE": "FuseMultipleShapesCreator"
                                    },
                                    "loglevel": 50,
                                    "creator_id": "a_winglet",
                                    "$TYPE": "ConstructionStepNode"
                                },
                                "x_printable": {
                                    "successors": {},
                                    "creator": {
                                        "shape_dict": {
                                            "0": "avase_wing[0]",
                                            "1": "avase_wing[1]",
                                            "2": "avase_wing[2]",
                                            "3": "avase_wing[3]",
                                            "4": "avase_wing[4]",
                                            "5": "avase_wing[5]",
                                            "6": "a_winglet"
                                        },
                                        "wing_index": "main_wing",
                                        "loglevel": 10,
                                        "creator_id": "x_printable",
                                        "$TYPE": "StandWingSegmentOnPrinterCreator"
                                    },
                                    "loglevel": 50,
                                    "creator_id": "",
                                    "$TYPE": "ConstructionStepNode"
                                }
                            },
                            "creator": {
                                "leading_edge_offset_factor": 0.1,
                                "trailing_edge_offset_factor": 0.15,
                                "minimum_rib_angle": 45,
                                "wing_side": "BOTH",
                                "wing_index": "main_wing",
                                "loglevel": 10,
                                "creator_id": "avase_wing",
                                "$TYPE": "VaseModeWingCreator"
                            },
                            "loglevel": 50,
                            "creator_id": "avase_wing",
                            "$TYPE": "ConstructionStepNode"
                        },
                        "eHawk-wing": {
                            "successors": {},
                            "creator": {
                                "file_path": "./tmp/exports",
                                "shapes_to_export": [
                                    "avase_wing",
                                    "avase_wing[0].print",
                                    "avase_wing[1].print",
                                    "avase_wing[2].print",
                                    "avase_wing[3].print",
                                    "a_winglet.print",
                                    "avase_wing.aileron[2]",
                                    "avase_wing.aileron[3]",
                                    "avase_wing.aileron[2]*",
                                    "avase_wing.aileron[3]*",
                                    "avase_wing[2].servo_mount"
                                ],
                                "loglevel": 20,
                                "creator_id": "eHawk-wing",
                                "$TYPE": "ExportToStepCreator"
                            },
                            "loglevel": 50,
                            "creator_id": "eHawk-wing",
                            "$TYPE": "ConstructionStepNode"
                        }
                    },
                    "loglevel": 50,
                    "creator_id": "eHawk-wing.root",
                    "$TYPE": "ConstructionRootNode"
                },
                "wings": {
                    "main_wing": {
                        "segments": [
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 1,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0.3
                                },
                                "length": 20.0,
                                "sweep": 0,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [0.03673996532422339, 0.9992005450970961, 0.0157621580261394
                                                         ],
                                        "spare_origin": [
                                            40.5,
                                            -0.04546757240303877,
                                            2.604835478413867
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.55,
                                        "spare_length": 70,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            89.10000000000001,
                                            -0.0469884150916505,
                                            2.6919644976908543
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.2,
                                        "spare_length": 70,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            32.4,
                                            -0.04157221844287501,
                                            2.3816707994978588
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 200,
                                "sweep": 2.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            41.23479930648447,
                                            19.938543329538884,
                                            2.9200786389366553
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": 60,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            89.10000000000001,
                                            19.95301158490835,
                                            2.6919644976908543
                                        ]
                                    },
                                    {
                                        "spare_support_dimension_width": 6.42,
                                        "spare_support_dimension_height": 6.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": 60,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.0,
                                            1.0,
                                            0.0
                                        ],
                                        "spare_origin": [
                                            32.4,
                                            19.958427781557123,
                                            2.3816707994978588
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 250,
                                "sweep": 8,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            48.58279237132915,
                                            219.7786523489581,
                                            6.072510244164535
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "rel_chord_root": 0.8,
                                    "rel_chord_tip": 0.8,
                                    "hinge_spacing": 0.5,
                                    "side_spacing_root": 2.0,
                                    "side_spacing_tip": 2.0,
                                    "servo": 1,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": 0.414,
                                    "rel_length_servo_position": 0.486,
                                    "positive_deflection_deg": 35,
                                    "negative_deflection_deg": 35,
                                    "trailing_edge_offset_factor": 1.2,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 75,
                                "sweep": 5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            57.767783702384996,
                                            469.57878862323213,
                                            10.013049750699386
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 85,
                                "sweep": 11,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            60.52328110170175,
                                            544.5188295055143,
                                            11.19521160265984
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 40,
                                "sweep": 12,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            63.64617815426074,
                                            629.4508758387675,
                                            12.534995034881689
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "servo_placement": "top",
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top"
                                },
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 20,
                                "sweep": 7.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard_backward",
                                        "spare_vector": [
                                            0.03673996532422339,
                                            0.9992005450970961,
                                            0.0157621580261394
                                        ],
                                        "spare_origin": [
                                            65.11577676722968,
                                            669.4188976426514,
                                            13.165481355927264
                                        ]
                                    }
                                ],
                                "number_interpolation_points": 201,
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 7.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 10,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 15,
                                "sweep": 12.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 10,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 10,
                                "sweep": 15,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 15,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": 0,
                                    "rotation_point_rel_chord": 0
                                },
                                "length": 5,
                                "sweep": 17.5,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/rg15.dat",
                                    "chord": 24.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "incidence": -0.5,
                                    "rotation_point_rel_chord": 0
                                },
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                            }
                        ],
                        "nose_pnt": [
                            0,
                            0,
                            0
                        ]
                    },
                },
                "fuselages": {},
                "settings": {
                    "servo_information": {
                        "1": {
                            "height": 0,
                            "width": 0,
                            "length": 0,
                            "lever_length": 0,
                            "rot_x": 0.0,
                            "rot_y": 0.0,
                            "rot_z": 0.0,
                            "trans_x": 0.0,
                            "trans_y": 0.0,
                            "trans_z": 0.0,
                            "servo": {
                                "length": 23,
                                "width": 12.5,
                                "height": 31.5,
                                "leading_length": 6,
                                "latch_z": 14.5,
                                "latch_x": 7.25,
                                "latch_thickness": 2.6,
                                "latch_length": 6,
                                "cable_z": 26,
                                "screw_hole_lx": 0,
                                "screw_hole_d": 0
                            }
                        }
                    },
                    "printer_settings": {
                        "layer_height": 0.24,
                        "wall_thickness": 0.42,
                        "rel_gap_wall_thickness": 0.075
                    }
                }
            }
        }

