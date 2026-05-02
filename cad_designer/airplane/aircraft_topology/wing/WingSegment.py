from typing import List, Optional

import math
from pydantic import PositiveFloat, PositiveInt, NonNegativeFloat

from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from cad_designer.airplane.types import WingSegmentType, TipType


class WingSegment:
    """
    Represents a segment of a wing with its geometric and structural properties.

    Each segment connects to the previous one via a chain of coordinate system transformations,
    defined by parameters such as length, sweep, dihedral, and incidence angles in the root and tip airfoils.

    Attributes:
        root_airfoil (Airfoil): The airfoil at the root of the segment.
        tip_airfoil (Airfoil): The airfoil at the tip of the segment.
        length (PositiveFloat): The length of the segment (loft along y-axis).
        sweep (NonNegativeFloat): The sweep of the segment (x-offset or angle).
        sweep_is_angle (bool): If True, sweep is interpreted as an angle.
        spare_list (List[Spare]): List of spares in the segment.
        trailing_edge_device (Optional[TrailingEdgeDevice]): Trailing edge device attached to the segment.
        number_interpolation_points (Optional[PositiveInt]): Number of points for airfoil interpolation.
        tip_type (Optional[TipType]): The type of the tip ('flat', 'round').
        wing_segment_type (WingSegmentType): The type of the segment ('root', 'segment', 'tip').

    Note:
        The root airfoil of a segment is equal to the tip airfoil of the previous segment.
        Tip segments can have a special tip type and do not have spares or trailing edge devices.
    """
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
        """
        Initializes a WingSegment instance.

        Args:
            root_airfoil (Airfoil): The airfoil at the root of the segment. Its parameters (dihedral, 
                incidence) define the relative transformation from the previous segment.
            length (PositiveFloat): The length of the segment, a key parameter for the coordinate 
                system transformation.
            sweep (NonNegativeFloat): The sweep of the segment, either as a distance or an angle 
                depending on sweep_is_angle. This is a key parameter for the coordinate system transformation.
            sweep_is_angle (bool): If True, sweep is interpreted as an angle in degrees; otherwise, 
                it's interpreted as a distance.
            tip_airfoil (Optional[Airfoil]): The airfoil at the tip of the segment. If provided, its 
                parameters define the transformation at the end of the segment.
            spare_list (List[Spare]): List of spares in the segment.
            trailing_edge_device (Optional[TrailingEdgeDevice]): The trailing edge device attached to the segment.
            number_interpolation_points (Optional[PositiveInt]): Number of points to use for interpolation.
            tip_type (Optional[TipType]): The type of the tip of the segment.
            wing_segment_type (WingSegmentType): The type of the wing segment.
        """

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
                data[key] = [spare.__getstate__() for spare in value] if value is not None else None
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
        if data.get('spare_list') is not None:
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
