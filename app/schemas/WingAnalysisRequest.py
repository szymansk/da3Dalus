from typing import Dict, Optional, List
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.wing import Wing
from app.schemas.AeroplaneRequest import AeroplaneSettings


class WingAnalysisRequest(BaseModel):
    """
    Request model for wing analysis using AVL.

    This model is used for the POST endpoint that analyzes wings using AVL.
    It includes the wing configuration and operating point parameters.
    """
    wings: Dict[str, Wing] = Field(..., description="Dictionary of wings to analyze")
    settings: Optional[AeroplaneSettings] = Field(None, description="Aeroplane settings")

    # Operating point parameters
    velocity: float = Field(10.0, description="Velocity in m/s")
    alpha: float = Field(0.0, description="Angle of attack in degrees")
    beta: float = Field(0.0, description="Sideslip angle in degrees")
    p: float = Field(0.0, description="Roll rate in rad/s")
    q: float = Field(0.0, description="Pitch rate in rad/s")
    r: float = Field(0.0, description="Yaw rate in rad/s")

    xyz_ref: List[float] \
        = Field([0.0, 0.0, 0.0], description="default location in meters about which moments and rotation rates are defined (if doing trim calculations, XYZref must be the CG location)")

    # Atmosphere parameters
    altitude: float = Field(0.0, description="Altitude in meters")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wings": {
                    "main_wing" : {
                        "segments": [
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 1,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 20.0,
                                "sweep": 0,
                                "sweep_angle": 0.0,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            40.5,
                                            -0.06030645607992892,
                                            3.4549545549062066
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
                                            -0.06454941004861466,
                                            3.6980332249732912
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
                                            -0.05490891668391669,
                                            3.1457297300081533
                                        ]
                                    }
                                ],
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "root"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 162.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 200,
                                "sweep": 2.5,
                                "sweep_angle": 0.7161599454704085,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            41.23516523995501,
                                            19.923960787106175,
                                            3.752603379665839
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
                                            19.935450589951387,
                                            3.6980332249732912
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
                                            19.945091083316083,
                                            3.1457297300081533
                                        ]
                                    }
                                ],
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 157,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 250,
                                "sweep": 8,
                                "sweep_angle": 1.8328395059420592,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            48.58681763950507,
                                            219.76663321896723,
                                            6.729091627262164
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
                                    "_servo": 1,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": 0.414,
                                    "rel_length_servo_position": 0.486,
                                    "positive_deflection_deg": 35,
                                    "negative_deflection_deg": 35,
                                    "trailing_edge_offset_factor": 1.2,
                                    "hinge_type": "top",
                                    "symmetric": False
                                },
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 132.88888888888889,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 75,
                                "sweep": 5,
                                "sweep_angle": 3.8140748342903543,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            57.77638313894265,
                                            469.56997375879354,
                                            10.44970193675757
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "rel_chord_root": 0.8,
                                    "rel_chord_tip": 0.8,
                                    "hinge_spacing": None,
                                    "side_spacing_root": None,
                                    "side_spacing_tip": None,
                                    "_servo": None,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": None,
                                    "rel_length_servo_position": None,
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top",
                                    "symmetric": True
                                },
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 123.05555555555554,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 85,
                                "sweep": 11,
                                "sweep_angle": 7.373766361330216,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            60.53325278877392,
                                            544.5109759207414,
                                            11.565885029606193
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "rel_chord_root": 0.8,
                                    "rel_chord_tip": 0.8,
                                    "hinge_spacing": None,
                                    "side_spacing_root": None,
                                    "side_spacing_tip": None,
                                    "_servo": None,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": None,
                                    "rel_length_servo_position": None,
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top",
                                    "symmetric": True
                                },
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 105.21777777777777,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 40,
                                "sweep": 12,
                                "sweep_angle": 16.69924423399362,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "follow",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            63.6577050585827,
                                            629.4441117042824,
                                            12.83089253483463
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "aileron",
                                    "rel_chord_root": 0.8,
                                    "rel_chord_tip": 0.8,
                                    "hinge_spacing": None,
                                    "side_spacing_root": None,
                                    "side_spacing_tip": None,
                                    "_servo": None,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": None,
                                    "rel_length_servo_position": None,
                                    "positive_deflection_deg": 25,
                                    "negative_deflection_deg": 25,
                                    "trailing_edge_offset_factor": 1.0,
                                    "hinge_type": "top",
                                    "symmetric": True
                                },
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 90,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 20,
                                "sweep": 7.5,
                                "sweep_angle": 20.556045219583467,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard_backward",
                                        "spare_vector": [
                                            0.03675826199775033,
                                            0.9992133621593052,
                                            0.014882441237981625
                                        ],
                                        "spare_origin": [
                                            65.12803553849271,
                                            669.4126461906545,
                                            13.426190184353896
                                        ]
                                    }
                                ],
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "segment"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 79.5,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 15,
                                "sweep": 7.5,
                                "sweep_angle": 26.56505117707799,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": None,
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                                "wing_segment_type": "tip"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 71.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 15,
                                "sweep": 10,
                                "sweep_angle": 33.690067525979785,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": None,
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                                "wing_segment_type": "tip"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 62.0,
                                    "dihedral_as_rotation_in_degrees": 5,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "length": 15,
                                "sweep": 12.5,
                                "sweep_angle": 39.8055710922652,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 10,
                                    "dihedral_as_translation": 0,
                                    "incidence": -0.0,
                                },
                                "spare_list": None,
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                                "wing_segment_type": "tip"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 52.5,
                                    "dihedral_as_rotation_in_degrees": 10,
                                    "dihedral_as_translation": 0,
                                    "incidence": -0.0,
                                },
                                "length": 10,
                                "sweep": 15,
                                "sweep_angle": 56.309932474020215,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 15,
                                    "dihedral_as_translation": 0,
                                    "incidence": -0.0,
                                },
                                "spare_list": None,
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                                "wing_segment_type": "tip"
                            },
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 40.5,
                                    "dihedral_as_rotation_in_degrees": 15,
                                    "dihedral_as_translation": 0,
                                    "incidence": -0.0,
                                },
                                "length": 5,
                                "sweep": 17.5,
                                "sweep_angle": 74.05460409907715,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 24.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": -0.0,
                                },
                                "spare_list": None,
                                "trailing_edge_device": None,
                                "number_interpolation_points": 201,
                                "tip_type": "flat",
                                "wing_segment_type": "tip"
                            }
                        ],
                        "nose_pnt": [
                            0,
                            0,
                            0
                        ],
                        "symmetric": True
                    },
                    "v-tail": {
                        "segments": [
                            {
                                "root_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 85.0,
                                    "dihedral_as_rotation_in_degrees": 45,
                                    "dihedral_as_translation": 0,
                                    "incidence": -2,
                                },
                                "length": 210.0,
                                "sweep": 15,
                                "sweep_angle": 4.085616779974877,
                                "tip_airfoil": {
                                    "airfoil": "./components/airfoils/mh32.dat",
                                    "chord": 70.0,
                                    "dihedral_as_rotation_in_degrees": 0,
                                    "dihedral_as_translation": 0,
                                    "incidence": 0,
                                },
                                "spare_list": [
                                    {
                                        "spare_support_dimension_width": 4.42,
                                        "spare_support_dimension_height": 4.42,
                                        "spare_position_factor": 0.25,
                                        "spare_length": None,
                                        "spare_start": 0.0,
                                        "spare_mode": "standard",
                                        "spare_vector": [
                                            0.05351516795938699,
                                            0.7058484920285241,
                                            0.7063384692194934
                                        ],
                                        "spare_origin": [
                                            670.7907626482797,
                                            -17.321732711341372,
                                            17.32173271134137
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
                                            696.2707769328415,
                                            -18.04115740932608,
                                            18.041157409326075
                                        ]
                                    }
                                ],
                                "trailing_edge_device": {
                                    "name": "v-tail",
                                    "rel_chord_root": 0.5882352941176471,
                                    "rel_chord_tip": 0.5882352941176471,
                                    "hinge_spacing": 0.5,
                                    "side_spacing_root": 2.0,
                                    "side_spacing_tip": 2.0,
                                    "_servo": None,
                                    "servo_placement": "top",
                                    "rel_chord_servo_position": None,
                                    "rel_length_servo_position": None,
                                    "positive_deflection_deg": 35,
                                    "negative_deflection_deg": 35,
                                    "trailing_edge_offset_factor": 1.2,
                                    "hinge_type": "top",
                                    "symmetric": False
                                },
                                "number_interpolation_points": 201,
                                "tip_type": None,
                                "wing_segment_type": "root"
                            }
                        ],
                        "nose_pnt": [
                            650,
                            0,
                            0
                        ],
                        "symmetric": True
                    }
                },
                "velocity": 15.0,
                "alpha": 0.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "altitude": 0.0,
                "xyz_ref": [0.055, 0.0, 0.0],
            }
        },
    )
