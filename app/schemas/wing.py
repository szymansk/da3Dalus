from typing import List, Optional, Literal
from pydantic import AliasChoices, BaseModel, PositiveFloat, Field

from app.schemas.Servo import Servo

# --- Shared literal constant (S1192) ---
_DEFAULT_AIRFOIL_RG15 = "./components/airfoils/rg15.dat"


class TrailingEdgeDevice(BaseModel):
    """
    Represents a trailing edge device (control surface) on a wing, such as an aileron, flap, or elevator.

    This model defines the geometry and configuration of control surfaces that are attached to the 
    trailing edge of a wing segment.
    """
    name: Optional[str] = Field(
        default=None, 
        description="Name of the trailing edge device (e.g., 'aileron', 'flap', 'elevator')"
    )
    rel_chord_root: Optional[float] = Field(
        default=None, 
        description="Relative position of the hinge line at the root of the device as a fraction of chord length (0.0-1.0)"
    )
    rel_chord_tip: Optional[float] = Field(
        default=None, 
        description="Relative position of the hinge line at the tip of the device as a fraction of chord length (0.0-1.0)"
    )
    hinge_spacing: Optional[float] = Field(
        default=None, 
        description="Spacing between hinges in millimeters"
    )
    side_spacing_root: Optional[float] = Field(
        default=None, 
        description="Spacing from the root edge of the segment in millimeters"
    )
    side_spacing_tip: Optional[float] = Field(
        default=None, 
        description="Spacing from the tip edge of the segment in millimeters"
    )
    servo: Servo | int | None = Field(
        default=None,
        validation_alias=AliasChoices("servo", "_servo"),
        serialization_alias="servo",
        description="Servo object or servo index used to actuate the trailing edge device"
    )
    servo_placement: Literal["top", "bottom"] = Field(
        default='top', 
        description="Placement of the servo on the wing surface ('top' or 'bottom')"
    )
    rel_chord_servo_position: Optional[float] = Field(
        default=None, 
        description="Relative chord-wise position of the servo as a fraction of chord length (0.0-1.0)"
    )
    rel_length_servo_position: Optional[float] = Field(
        default=None, 
        description="Relative span-wise position of the servo as a fraction of segment length (0.0-1.0)"
    )
    positive_deflection_deg: Optional[float] = Field(
        default=None, 
        description="Maximum positive deflection angle in degrees"
    )
    negative_deflection_deg: Optional[float] = Field(
        default=None, 
        description="Maximum negative deflection angle in degrees"
    )
    trailing_edge_offset_factor: Optional[float] = Field(
        default=None, 
        description="Factor to determine the offset of the trailing edge for manufacturing purposes"
    )
    hinge_type: Literal["middle", "top", "top_simple", "round_inside", "round_outside"] = Field(
        default='top', 
        description="Type of hinge mechanism used for the trailing edge device"
    )
    symmetric: bool = Field(
        default=True,
        description=(
            "Whether the trailing edge device deflects symmetrically between left/right wings "
            "(e.g. flaps/elevator) or anti-symmetrically (e.g. aileron)."
        ),
    )

SpareMode = Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"]
"""
Defines the different modes for spares. The "follow" mode behaviour is only applied on spares that have the same index:
- normal: The spare goes along the normal vector of the cross section plane in tip direction
- follow: The spare vector will follow the direction of the previous one, so the spare vector will be the previous spare vector expressed in the current segment’s coordinate system.
- standard: The standard spare vector is calculated in that way, that the spare vector will point from the mean camber point at the given relative chord (spare position factor) of the root airfoil to the corresponding point of the tip airfoil. 
- standard_backward: It is calculate like the "standard" mode but in direction of the root. It adjusts all spares in "follow" mode, that are found in root direction.
- orthogonal_backward: Like the "standard_backward" mode, but the spare vector is orthogonal to the tip airfoils plane, it also adjusts the spare vectors of all spares in "follow" mode in root direction.
"""

class Spare(BaseModel):
    """
    Represents a structural spar within a wing segment.

    Spars are the main load-bearing elements of a wing that run spanwise (from root to tip)
    and provide structural integrity and stiffness to the wing.
    """
    spare_support_dimension_width: float = Field(
        description="Width of the spar support structure in millimeters"
    )
    spare_support_dimension_height: float = Field(
        description="Height of the spar support structure in millimeters"
    )
    spare_position_factor: float = Field(
        description="Relative chord-wise position of the spar as a fraction of chord length (0.0-1.0) from the leading edge"
    )
    spare_length: Optional[float] = Field(
        default=None, 
        description="Length of the spar in millimeters; if None, spans the entire segment"
    )
    spare_start: float = Field(
        description="Starting position of the spar along the span in millimeters"
    )
    spare_mode: SpareMode = Field(
        description="Mode determining how the spar is oriented and positioned within the wing"
    )
    spare_vector: List[float] = Field(
        description="3D vector [x, y, z] defining the direction of the spar"
    )
    spare_origin: List[float] = Field(
        description="3D coordinates [x, y, z] of the spar's origin point"
    )


class Airfoil(BaseModel):
    """
    Represents an airfoil profile used in a wing segment.

    An airfoil is the cross-sectional shape of a wing that determines its aerodynamic properties.
    This model defines the geometry and orientation of an airfoil within a wing segment.
    """
    airfoil: str = Field(
        description="Path to the airfoil data file or name of the airfoil profile"
    )
    chord: PositiveFloat = Field(
        description="Length of the airfoil chord in millimeters"
    )
    dihedral_as_rotation_in_degrees: Optional[float] = Field(
        default=0,
        ge=-180.0,
        le=180.0,
        description="Dihedral angle in degrees, representing the upward angle of this cross section. Positive is wingtip upwards, negative is anhedral."
    )
    incidence: Optional[float] = Field(
        default=0,
        description="Incidence angle in degrees. Positive is leading edge upwards."
    )



class Segment(BaseModel):
    """
    Represents a segment of a wing.

    A wing is typically divided into multiple segments, each with its own geometric properties.
    Each segment has a root and tip airfoil, that define a segments cross-sections.
    A segment may contain spars and trailing-edge-devices.

    A segment that follows the previous segment, in direction of the tip, will have the equal
    geometric properties of its root airfoil as the tip airfoil of the previous segment.
    """
    root_airfoil: Airfoil = Field(
        description="Airfoil profile at the root (inner end) of the segment"
    )
    length: float = Field(
        description="Length of the segment in millimeters, measured along the span"
    )
    sweep: float = Field(
        description="Sweep in millimeters, representing the backward translation of the segments tip cross section relative to the segments root cross section."
    )
    tip_airfoil: Airfoil = Field(
        description="Airfoil profile at the tip (outer end) of the segment"
    )
    spare_list: Optional[List[Spare]] = Field(
        default=None,
        description="List of structural spars within the segment. The first spare_list[0] is the main spare of the wing."
    )
    trailing_edge_device: Optional[TrailingEdgeDevice] = Field(
        default=None,
        description="Control surface attached to the trailing edge of the segment"
    )
    number_interpolation_points: Optional[int] = Field(
        default=None,
        description="Number of points used for interpolation between root and tip airfoils"
    )
    wing_segment_type: Optional[Literal["root", "segment", "tip"]] = Field(
        default=None,
        description="Segment classification: 'root', 'segment', or 'tip'"
    )
    tip_type: Optional[str] = Field(
        default=None,
        description="Type of wing tip for this segment (e.g., 'flat', 'rounded')"
    )

class Wing(BaseModel):
    """
    Represents a complete wing of an aircraft.

    A wing consists of one or more segments and is positioned relative to the aircraft's
    coordinate system using a nose point.
    """
    segments: List[Segment] = Field(
        description="List of wing segments from root to tip"
    )
    nose_pnt: List[float] = Field(
        description="3D coordinates [x, y, z] of the wing's nose point in the aircraft coordinate system"
    )
    symmetric: bool = Field(
        default=True,
        description="Whether the wing is mirrored along the aircraft's symmetry plane",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "segments": [
                    {
                        "root_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 162.0,
                            "dihedral": 1,
                            "incidence": 0,
                        },
                        "length": 20.0,
                        "sweep": 0,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 162.0,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 162.0,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 200,
                        "sweep": 2.5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 157,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 157,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 250,
                        "sweep": 8,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 132.88888888888889,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 132.88888888888889,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 75,
                        "sweep": 5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 123.05555555555554,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 123.05555555555554,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 85,
                        "sweep": 11,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 105.21777777777777,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 105.21777777777777,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 40,
                        "sweep": 12,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 90,
                            "dihedral": 0,
                            "incidence": 0,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 90,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 20,
                        "sweep": 7.5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 79.5,
                            "dihedral": 5,
                            "incidence": -0.5,
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
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 79.5,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 15,
                        "sweep": 7.5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 71.0,
                            "dihedral": 5,
                            "incidence": -0.5,
                        },
                        "number_interpolation_points": 201,
                        "tip_type": "flat",
                    },
                    {
                        "root_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 71.0,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 15,
                        "sweep": 10,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 62.0,
                            "dihedral": 5,
                            "incidence": -0.5,
                        },
                        "number_interpolation_points": 201,
                        "tip_type": "flat",
                    },
                    {
                        "root_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 62.0,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 15,
                        "sweep": 12.5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 52.5,
                            "dihedral": 10,
                            "incidence": -0.5,
                        },
                        "number_interpolation_points": 201,
                        "tip_type": "flat",
                    },
                    {
                        "root_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 52.5,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 10,
                        "sweep": 15,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 40.5,
                            "dihedral": 15,
                            "incidence": -0.5,
                        },
                        "number_interpolation_points": 201,
                        "tip_type": "flat",
                    },
                    {
                        "root_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 40.5,
                            "dihedral": 0,
                            "incidence": 0,
                        },
                        "length": 5,
                        "sweep": 17.5,
                        "tip_airfoil": {
                            "airfoil": _DEFAULT_AIRFOIL_RG15,
                            "chord": 24.0,
                            "dihedral": 0,
                            "incidence": -0.5,
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
