from typing import List, Optional

import math
from pydantic import PositiveFloat, PositiveInt, NonNegativeFloat

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from cad_designer.airplane.types import WingSegmentType, TipType


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

    def __getstate__(self):
        """Return a dictionary of serializable attributes for JSON serialization."""
        data = {}
        for key, value in self.__dict__.items():
            if key == 'root_airfoil' or key == 'tip_airfoil':
                data[key] = value.__getstate__() if value else None
            elif key == 'spare_list':
                data[key] = [spare.__getstate__() for spare in value] if value else None
            elif key == 'trailing_edge_device':
                data[key] = value.__getstate__() if value else None
            else:
                data[key] = value
        return data

    @staticmethod
    def from_json_dict(data: dict) -> 'WingSegment':
        """
        Create a WingSegment from a JSON dictionary.

        Args:
            data: Dictionary containing the WingSegment data.

        Returns:
            A new WingSegment instance.
        """
        from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
        from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
        from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

        # Create root_airfoil and tip_airfoil objects
        root_airfoil = Airfoil.from_json_dict(data.get('root_airfoil')) if data.get('root_airfoil') else None
        tip_airfoil = Airfoil.from_json_dict(data.get('tip_airfoil')) if data.get('tip_airfoil') else None

        # Create spare_list
        spare_list = None
        if data.get('spare_list'):
            spare_list = [Spare.from_json_dict(spare_data) for spare_data in data.get('spare_list')]

        # Create trailing_edge_device
        trailing_edge_device = None
        if data.get('trailing_edge_device'):
            trailing_edge_device = TrailingEdgeDevice.from_json_dict(data.get('trailing_edge_device'))

        # Create and return the WingSegment
        return WingSegment(
            root_airfoil=root_airfoil,
            length=data.get('length'),
            sweep=data.get('sweep', 0),
            sweep_is_angle=False,  # We use the calculated sweep value directly
            tip_airfoil=tip_airfoil,
            spare_list=spare_list,
            trailing_edge_device=trailing_edge_device,
            number_interpolation_points=data.get('number_interpolation_points'),
            tip_type=data.get('tip_type'),
            wing_segment_type=data.get('wing_segment_type', 'segment')
        )
