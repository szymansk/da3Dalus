from typing import Literal, Optional

from pydantic.v1 import NonNegativeFloat

from airplane.aircraft_topology.components import ServoInformation
from airplane.aircraft_topology.components.Servo import Servo
from airplane.types import Factor

ServoPlacement = Literal["top", "bottom"]
HingeType = Literal["middle", "top", "top_simple", "round_inside", "round_outside"]

class TrailingEdgeDevice:

    def servo(self, servo_information: dict[int, ServoInformation]|None) -> Servo | None:
        if self._servo is None:
            return None

        if servo_information is not None:
            if type(self._servo) is int:
                if self._servo in servo_information.keys():
                    return servo_information[self._servo].servo
                else:
                    raise ValueError(f"No servo information for servo '{self._servo}' provided.")
            elif type(self._servo) is Servo:
                return self._servo
        else:
            if type(self._servo) is int:
                raise ValueError("No servo information provided.")
            elif type(self._servo) is Servo:
                return self._servo


    def __init__(self, name: str,
                 rel_chord_root: Optional[Factor] = None,
                 rel_chord_tip: Optional[Factor] = None,
                 hinge_spacing: Optional[float] = None,
                 side_spacing_root: Optional[NonNegativeFloat] = None,
                 side_spacing_tip: Optional[NonNegativeFloat] = None,
                 servo: Optional[Servo|int] = None,
                 servo_placement: ServoPlacement = 'top',
                 rel_chord_servo_position: Optional[Factor] = None,
                 rel_length_servo_position: Optional[Factor] = None,
                 positive_deflection_deg: NonNegativeFloat = 25,
                 negative_deflection_deg: NonNegativeFloat = 25,
                 trailing_edge_offset_factor: Factor = 1.0,
                 hinge_type: HingeType = "top"):
        self.name = name
        self.rel_chord_root = rel_chord_root
        self.rel_chord_tip = rel_chord_tip
        self.hinge_spacing = hinge_spacing
        self.side_spacing_root = side_spacing_root
        self.side_spacing_tip = side_spacing_tip

        self._servo = servo
        self.servo_placement = servo_placement
        self.rel_chord_servo_position = rel_chord_servo_position
        self.rel_length_servo_position = rel_length_servo_position

        self.positive_deflection_deg = positive_deflection_deg
        self.negative_deflection_deg = negative_deflection_deg
        self.trailing_edge_offset_factor = trailing_edge_offset_factor
        self.hinge_type = hinge_type
        pass

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
