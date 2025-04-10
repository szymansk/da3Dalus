from typing import Optional

from cadquery import Plane
from pydantic import PositiveFloat

from cad_designer.airplane.aircraft_topology.wing.CoordinateSystem import CoordinateSystem
from cad_designer.airplane.types import Factor, DihedralInDegrees


class Airfoil:
    def __init__(self,
                 airfoil: Optional[str] = None,
                 chord: Optional[PositiveFloat] = None,
                 dihedral_as_rotation_in_degrees: DihedralInDegrees = 0,
                 dihedral_as_translation: float = 0,
                 incidence: float = 0,
                 rotation_point_rel_chord: Factor = 0.25):
        self.airfoil: str = airfoil
        self.chord: float = chord
        self.dihedral_as_rotation_in_degrees: float = dihedral_as_rotation_in_degrees
        self.dihedral_as_translation: float = dihedral_as_translation
        if self.dihedral_as_rotation_in_degrees != 0 and self.dihedral_as_translation != 0:
            raise ValueError("either dihedral_as_rotation_in_radians or dihedral_as_translation must be zero!")
        self.incidence: float = incidence
        self.rotation_point_rel_chord: float = rotation_point_rel_chord
        if self.dihedral_as_translation != 0 and self.rotation_point_rel_chord != 0.25:
            raise ValueError("if dihedral_as_translation is not zero, than rotation_point_rel_chord has to be 0.25!")
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