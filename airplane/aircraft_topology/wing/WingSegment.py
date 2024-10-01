from typing import List, Optional

import math
from pydantic.v1 import PositiveFloat, PositiveInt, NonNegativeFloat

from airplane.aircraft_topology.wing.Airfoil import Airfoil
from airplane.aircraft_topology.wing.Spare import Spare
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from airplane.types import WingSegmentType, TipType


class WingSegment:
    def __init__(self, root_airfoil: Airfoil,
                 length: PositiveFloat,
                 sweep: NonNegativeFloat = 0,
                 sweep_is_angle: bool = False,
                 tip_airfoil: Optional[Airfoil] = None,
                 spare_list: List[Spare] = None,
                 trailing_edge_device: Optional[TrailingEdgeDevice] = None,
                 number_interpolation_points: Optional[PositiveInt] = None,
                 tip_type: Optional[TipType] = None,
                 wing_segment_type: WingSegmentType = 'segment'):

        self.root_airfoil = root_airfoil

        self.length = length

        self.sweep = sweep

        if sweep_is_angle:
            self.sweep_angle = sweep
            self.sweep = length * math.tan(math.radians(sweep))
        else:
            sweep_angle_rad = math.atan(sweep / length)
            self.sweep_angle = math.degrees(sweep_angle_rad)

        self.tip_airfoil = tip_airfoil

        self.spare_list = spare_list
        self.trailing_edge_device = trailing_edge_device
        self.number_interpolation_points = number_interpolation_points
        self.tip_type = tip_type
        self.wing_segment_type = wing_segment_type

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
