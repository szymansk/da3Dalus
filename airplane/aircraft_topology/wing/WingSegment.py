from typing import Literal, List

from airplane.aircraft_topology.wing.Spare import Spare
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

WingSegmentType = Literal['root','segment','tip']


class WingSegment:
    def __init__(self, root_airfoil: str, length: float, root_chord: float, tip_chord: float, sweep: float = 0,
                 root_dihedral: float = 0, root_incidence: float = 0, tip_airfoil: str = None, tip_dihedral: float = 0,
                 tip_incidence: float = 0, spare_list: List[Spare] = None,
                 trailing_edge_device: TrailingEdgeDevice = None, number_interpolation_points: int = None,
                 tip_type: Literal['round'] = None, wing_segment_type: WingSegmentType = 'segment'):
        self.tip_airfoil = tip_airfoil
        self.root_airfoil = root_airfoil
        self.length = length
        self.root_chord = root_chord
        self.tip_chord = tip_chord
        self.sweep = sweep
        self.root_dihedral = root_dihedral
        self.root_incidence = root_incidence
        self.tip_dihedral = tip_dihedral
        self.tip_incidence = tip_incidence
        self.spare_list = spare_list
        self.trailing_edge_device = trailing_edge_device
        self.number_interpolation_points = number_interpolation_points
        self.tip_type = tip_type
        self.wing_segment_type = wing_segment_type

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)
