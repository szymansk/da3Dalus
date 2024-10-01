from typing import Optional

from cadquery import Plane
from pydantic import PositiveFloat

from airplane.aircraft_topology.wing.CoordinateSystem import CoordinateSystem
from airplane.types import Factor


class Airfoil:
    def __init__(self,
                 airfoil: Optional[str] = None,
                 chord: Optional[PositiveFloat] = None,
                 dihedral: float = 0,
                 incidence: float = 0,
                 rotation_point_rel_chord: Factor = 0.25):
        self.airfoil: str = airfoil
        self.chord: float = chord
        self.dihedral: float = dihedral
        self.incidence: float = incidence
        self.rotation_point_rel_chord: float = rotation_point_rel_chord
        self.coordinate_system = None

    def set_airfoil_coordinate_system(self, cs: Plane):
        self.coordinate_system = CoordinateSystem(cs.xDir.toTuple(), cs.yDir.toTuple(), cs.zDir.toTuple(), cs.origin.toTuple())

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['coordinate_system']
        return state