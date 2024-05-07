from typing import Literal, Optional

from airplane.aircraft_topology.components.Servo import Servo

ServoPlacement = Literal["top", "bottom"]
HingeType = Literal["middle", "top", "top_simple", "round_inside", "round_outside"]

class TrailingEdgeDevice:

    def __init__(self, name: str,
                 rel_chord_root: Optional[float] = None,
                 rel_chord_tip: Optional[float] = None,
                 hinge_spacing: Optional[float] = None,
                 side_spacing_root: Optional[float] = None,
                 side_spacing_tip: Optional[float] = None,
                 servo: Optional[Servo] = None,
                 servo_placement: ServoPlacement = 'top',
                 rel_chord_servo_position: Optional[float] = None,
                 rel_length_servo_position: Optional[float] = None,
                 positive_deflection_deg: float = 25,
                 negative_deflection_deg: float = 25,
                 trailing_edge_offset_factor: float = 1.0,
                 hinge_type: HingeType = "top"):
        self.name = name
        self.rel_chord_root = rel_chord_root
        self.rel_chord_tip = rel_chord_tip
        self.hinge_spacing = hinge_spacing
        self.side_spacing_root = side_spacing_root
        self.side_spacing_tip = side_spacing_tip

        self.servo = servo
        self.servo_placement = servo_placement
        self.rel_chord_servo_position = rel_chord_servo_position
        self.rel_length_servo_position = rel_length_servo_position

        self.positive_deflection_deg = positive_deflection_deg
        self.negative_deflection_deg = negative_deflection_deg
        self.trailing_edge_offset_factor = trailing_edge_offset_factor
        self.suspension_type = hinge_type
        pass

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
