from typing import Literal, Tuple

from cadquery import Vector
from pydantic import NonNegativeFloat

from cad_designer.airplane.types import Factor

SpareMode = Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"]

class Spare:
    """
    Represents a structural spare within a wing segment.

    Attributes:
        spare_support_dimension_width (NonNegativeFloat): Width of the spare support.
        spare_support_dimension_height (NonNegativeFloat): Height of the spare support.
        spare_position_factor (Factor): Position factor along the chord.
        spare_length (NonNegativeFloat): Length of the spare.
        spare_start (NonNegativeFloat): Start position of the spare.
        spare_vector (Vector): Direction vector of the spare.
        spare_origin (Vector): Origin point of the spare.
        spare_mode (SpareMode): Mode of the spare ('normal', 'follow', 'standard', etc.).

    Methods:
        from_json_dict(data): Creates a Spare from a JSON dictionary.

    Note:
        The spare mode determines how the spare is positioned and oriented within the segment.
    """
    def __init__(self,
                 spare_support_dimension_width: NonNegativeFloat,
                 spare_support_dimension_height: NonNegativeFloat,
                 spare_position_factor: Factor = None,
                 spare_length: NonNegativeFloat = None,
                 spare_start: NonNegativeFloat = 0.0,
                 spare_vector: Tuple[float,float,float]= None,
                 spare_origin: Tuple[float,float,float] = None,
                 spare_mode: SpareMode = "standard"):
        self.spare_support_dimension_width = spare_support_dimension_width
        self.spare_support_dimension_height = spare_support_dimension_height
        self.spare_position_factor: float = spare_position_factor
        self.spare_length = spare_length
        self.spare_start = spare_start
        self.spare_mode = spare_mode
        self.spare_vector = Vector(spare_vector) if spare_vector is not None else None
        self.spare_origin = Vector(spare_origin) if spare_origin is not None else None

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)

    def __getstate__(self):
        """Return a dictionary of serializable attributes for JSON serialization."""
        data = self.__dict__.copy()
        if self.spare_vector is not None:
            data['spare_vector'] = self.spare_vector.toTuple()
        if self.spare_origin is not None:
            data['spare_origin'] = self.spare_origin.toTuple()
        return data

    @staticmethod
    def from_json_dict(data: dict) -> 'Spare':
        """
        Create a Spare from a JSON dictionary.

        Args:
            data: Dictionary containing the Spare data.

        Returns:
            A new Spare instance.
        """
        # Create and return the Spare
        return Spare(
            spare_support_dimension_width=data.get('spare_support_dimension_width', 0),
            spare_support_dimension_height=data.get('spare_support_dimension_height', 0),
            spare_position_factor=data.get('spare_position_factor'),
            spare_length=data.get('spare_length'),
            spare_start=data.get('spare_start', 0.0),
            spare_vector=data.get('spare_vector'),
            spare_origin=data.get('spare_origin'),
            spare_mode=data.get('spare_mode', 'standard')
        )
