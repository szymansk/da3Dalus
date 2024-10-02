from typing import Literal, Tuple

from cadquery import Vector
from pydantic import NonNegativeFloat

from airplane.types import Factor

SpareMode = Literal["normal", "follow", "standard", "standard_backward", "orthogonal_backward"]

class Spare:
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
        data = self.__dict__.copy()
        data['spare_vector'] = self.spare_vector.toTuple()
        data['spare_origin'] = self.spare_origin.toTuple()
        return data