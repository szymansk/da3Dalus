from typing import List, Optional, Literal
from pydantic import BaseModel, model_validator, PositiveFloat, NonNegativeFloat

from app.models.Servo import Servo

class TrailingEdgeDevice(BaseModel):
    name: Optional[str] = None
    rel_chord_root: Optional[float] = None
    rel_chord_tip: Optional[float] = None
    hinge_spacing: Optional[float] = None
    side_spacing_root: Optional[float] = None
    side_spacing_tip: Optional[float] = None
    servo: Optional[Servo | int] = None
    servo_placement: Literal["top", "bottom"] = 'top'
    rel_chord_servo_position: Optional[float] = None
    rel_length_servo_position: Optional[float] = None
    positive_deflection_deg: Optional[float] = None
    negative_deflection_deg: Optional[float] = None
    trailing_edge_offset_factor: Optional[float] = None
    hinge_type: Literal["middle", "top", "top_simple", "round_inside", "round_outside"] = 'top'

SpareMode = Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"]

class Spare(BaseModel):
    spare_support_dimension_width: float
    spare_support_dimension_height: float
    spare_position_factor: float
    spare_length: Optional[float] = None
    spare_start: float
    spare_mode: SpareMode
    spare_vector: List[float]
    spare_origin: List[float]


class Airfoil(BaseModel):
    airfoil: str
    chord: PositiveFloat
    dihedral_as_rotation_in_degrees: Optional[NonNegativeFloat] = 0
    dihedral_as_translation: Optional[NonNegativeFloat] = 0
    incidence: Optional[float] = 0
    rotation_point_rel_chord: Optional[NonNegativeFloat] = 0.25

    @model_validator(mode='after')
    def check_dihedral_fields(self):
        dihedral_rotation = self.dihedral_as_rotation_in_degrees
        dihedral_translation = self.dihedral_as_translation
        rotation_point_rel_chord = self.rotation_point_rel_chord

        # Ensure that exactly one of the dihedral parameters is zero
        if dihedral_rotation != 0 and dihedral_translation != 0:
            raise ValueError(
                "Exactly one of 'dihedral_as_rotation_in_degrees' or 'dihedral_as_translation' must be zero."
            )

        # If dihedral_translation > 0, then rotation_point_rel_chord must be 0.25
        if dihedral_translation > 0 and rotation_point_rel_chord != 0.25:
            raise ValueError(
                "When 'dihedral_as_translation' > 0, 'rotation_point_rel_chord' must be 0.25 (quater chord)."
            )

        return self


class Segment(BaseModel):
    root_airfoil: Airfoil
    length: float
    sweep: float
    tip_airfoil: Airfoil
    spare_list: Optional[List[Spare]] = None
    trailing_edge_device: Optional[TrailingEdgeDevice] = None
    number_interpolation_points: int
    tip_type: Optional[str] = None

class Wing(BaseModel):
    segments: List[Segment]
    nose_pnt: List[float]

    model_config = {
        "json_schema_extra": {
            "example": {
                "segments": [
                    {
                        "root_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 162.0,
                            "dihedral": 1,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0.3
                        },
                        "length": 20.0,
                        "sweep": 0,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 162.0,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 200,
                        "sweep": 2.5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 157,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 250,
                        "sweep": 8,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 132.88888888888889,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 75,
                        "sweep": 5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 123.05555555555554,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 85,
                        "sweep": 11,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 105.21777777777777,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 40,
                        "sweep": 12,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 90,
                            "dihedral": 0,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 20,
                        "sweep": 7.5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 79.5,
                            "dihedral": 5,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 15,
                        "sweep": 7.5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 71.0,
                            "dihedral": 5,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 15,
                        "sweep": 10,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 62.0,
                            "dihedral": 5,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 15,
                        "sweep": 12.5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 52.5,
                            "dihedral": 10,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 10,
                        "sweep": 15,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 40.5,
                            "dihedral": 15,
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
                            "dihedral": 0,
                            "incidence": 0,
                            "rotation_point_rel_chord": 0
                        },
                        "length": 5,
                        "sweep": 17.5,
                        "tip_airfoil": {
                            "airfoil": "./components/airfoils/rg15.dat",
                            "chord": 24.0,
                            "dihedral": 0,
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
            }
        }
    }
