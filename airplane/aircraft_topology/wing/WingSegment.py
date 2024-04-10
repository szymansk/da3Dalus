from typing import Literal, List

from airplane.aircraft_topology.wing.Airfoil import Airfoil
from airplane.aircraft_topology.wing.Spare import Spare
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

WingSegmentType = Literal['root','segment','tip']
TipType = Literal["flat", "round"]


class WingSegment:
    def __init__(self,
                 root_airfoil: Airfoil,
                 length: float,
                 sweep: float = 0,
                 tip_airfoil: Airfoil = None,
                 spare_list: List[Spare] = None,
                 trailing_edge_device: TrailingEdgeDevice = None, number_interpolation_points: int = None,
                 tip_type: TipType = None, wing_segment_type: WingSegmentType = 'segment'):

        self.root_airfoil = root_airfoil

        self.length = length
        self.sweep = sweep

        self.tip_airfoil = tip_airfoil

        self.spare_list = spare_list
        self.trailing_edge_device = trailing_edge_device
        self.number_interpolation_points = number_interpolation_points
        self.tip_type = tip_type
        self.wing_segment_type = wing_segment_type

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
