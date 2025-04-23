from typing import Literal, Optional

from pydantic import NonNegativeFloat

from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.components.Servo import Servo
from cad_designer.airplane.types import Factor

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
                 rel_chord_root: Optional[Factor] = 0.8,
                 rel_chord_tip: Optional[Factor] = None,
                 hinge_spacing: Optional[float] = None,
                 side_spacing_root: Optional[NonNegativeFloat] = None,
                 side_spacing_tip: Optional[NonNegativeFloat] = None,
                 servo: Optional[Servo | int] = None,
                 servo_placement: ServoPlacement = 'top',
                 rel_chord_servo_position: Optional[Factor] = None,
                 rel_length_servo_position: Optional[Factor] = None,
                 positive_deflection_deg: NonNegativeFloat = 25,
                 negative_deflection_deg: NonNegativeFloat = 25,
                 trailing_edge_offset_factor: Factor = 1.0,
                 hinge_type: HingeType = "top",
                 symmetric=True):
        """
        Initializes a TrailingEdgeDevice instance.

        Args:
            name (str): The name of the trailing edge device.
            rel_chord_root (Optional[Factor]): Relative chord position at the root.
            rel_chord_tip (Optional[Factor]): Relative chord position at the tip.
            hinge_spacing (Optional[float]): Spacing between hinges.
            side_spacing_root (Optional[NonNegativeFloat]): Side spacing at the root.
            side_spacing_tip (Optional[NonNegativeFloat]): Side spacing at the tip.
            servo (Optional[Servo | int]): The associated servo or its ID.
            servo_placement (ServoPlacement): Placement of the servo ('top' or 'bottom').
            rel_chord_servo_position (Optional[Factor]): Relative chord position of the servo.
            rel_length_servo_position (Optional[Factor]): Relative length position of the servo.
            positive_deflection_deg (NonNegativeFloat): Maximum positive deflection angle in degrees.
            negative_deflection_deg (NonNegativeFloat): Maximum negative deflection angle in degrees.
            trailing_edge_offset_factor (Factor): Offset factor for the trailing edge.
            hinge_type (HingeType): Type of hinge used.
            symmetric (bool): Indicates whether the device deflection is symmetric. E.g. an aileron is not symmetric but flaps are.
        """

        self.name = name
        self.rel_chord_root = rel_chord_root
        self.rel_chord_tip = rel_chord_tip if rel_chord_tip is not None else rel_chord_root
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

        self.symmetric = symmetric
        pass

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)

    def __getstate__(self):
        """Return a dictionary of serializable attributes for JSON serialization."""
        data = {}
        for key, value in self.__dict__.items():
            if key == '_servo' and isinstance(value, Servo):
                data[key] = value.__getstate__() if hasattr(value, '__getstate__') else value
            else:
                data[key] = value
        return data

    @staticmethod
    def from_json_dict(data: dict) -> 'TrailingEdgeDevice':
        """
        Create a TrailingEdgeDevice from a JSON dictionary.

        Args:
            data: Dictionary containing the TrailingEdgeDevice data.

        Returns:
            A new TrailingEdgeDevice instance.
        """
        from cad_designer.airplane.aircraft_topology.components.Servo import Servo

        # Handle _servo if it's a Servo object
        servo = data.get('_servo')
        if isinstance(servo, dict) and 'model' in servo:
            servo = Servo.from_json_dict(servo) if hasattr(Servo, 'from_json_dict') else servo

        # Create and return the TrailingEdgeDevice
        device = TrailingEdgeDevice(
            name=data.get('name'),
            rel_chord_root=data.get('rel_chord_root'),
            rel_chord_tip=data.get('rel_chord_tip'),
            hinge_spacing=data.get('hinge_spacing'),
            side_spacing_root=data.get('side_spacing_root'),
            side_spacing_tip=data.get('side_spacing_tip'),
            servo=servo,
            servo_placement=data.get('servo_placement'),
            rel_chord_servo_position=data.get('rel_chord_servo_position'),
            rel_length_servo_position=data.get('rel_length_servo_position'),
            positive_deflection_deg=data.get('positive_deflection_deg'),
            negative_deflection_deg=data.get('negative_deflection_deg'),
            trailing_edge_offset_factor=data.get('trailing_edge_offset_factor'),
            hinge_type=data.get('hinge_type'),
            symmetric=data.get('symmetric')
        )

        return device
