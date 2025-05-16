from typing import Optional

from cadquery import Plane
from pydantic import PositiveFloat

from cad_designer.airplane.aircraft_topology.wing.CoordinateSystem import CoordinateSystem
from cad_designer.airplane.types import Factor, DihedralInDegrees


class Airfoil:
    """
    Represents an airfoil with its geometric and aerodynamic properties.

    The parameters of this class are used to describe a chain of coordinate system transformations.
    Each set of parameters provides relative values for the transformation from one coordinate system to another.
    The main parameters for calculating these transformations are dihedral, incidence, and relative rotation point.

    Attributes:
        airfoil (Optional[str]): The name or identifier of the airfoil.
        chord (Optional[PositiveFloat]): The chord length of the airfoil.
        dihedral_as_rotation_in_degrees (DihedralInDegrees): The dihedral angle as a rotation in degrees, relative to the previous airfoil.
        dihedral_as_translation (float): The dihedral angle as a translation, relative to the previous airfoil.
        incidence (float): The incidence angle of the airfoil, relative to the previous airfoil.
        rotation_point_rel_chord (Factor): The relative position of the rotation point along the chord (default is 0.25 and must be 0.25 for aerosandbox).
        coordinate_system (Optional[CoordinateSystem]): The coordinate system associated with the airfoil.
    """

    def __init__(self,
                 airfoil: Optional[str] = None,
                 chord: Optional[PositiveFloat] = None,
                 dihedral_as_rotation_in_degrees: DihedralInDegrees = 0,
                 dihedral_as_translation: float = 0,
                 incidence: float = 0,
                 rotation_point_rel_chord: Factor = 0.25):
        """
        Initializes an Airfoil instance.

        Args:
            airfoil (Optional[str]): The name or identifier of the airfoil.
            chord (Optional[PositiveFloat]): The chord length of the airfoil.
            dihedral_as_rotation_in_degrees (DihedralInDegrees): The dihedral angle as a rotation in degrees.
            dihedral_as_translation (float): The dihedral angle as a translation.
            incidence (float): The incidence angle of the airfoil.
            rotation_point_rel_chord (Factor): The relative position of the rotation point along the chord.

        Raises:
            ValueError: If both dihedral_as_rotation_in_degrees and dihedral_as_translation are non-zero.
            ValueError: If dihedral_as_translation is non-zero and rotation_point_rel_chord is not 0.25.
        """
        self.airfoil: str = airfoil
        self.chord: float = chord
        self.dihedral_as_rotation_in_degrees: float = dihedral_as_rotation_in_degrees
        self.dihedral_as_translation: float = dihedral_as_translation
        #if self.dihedral_as_rotation_in_degrees != 0 and self.dihedral_as_translation != 0:
        #    raise ValueError("either dihedral_as_rotation_in_radians or dihedral_as_translation must be zero!")
        self.incidence: float = incidence
        self.rotation_point_rel_chord: float = rotation_point_rel_chord
        #if self.dihedral_as_translation != 0 and self.rotation_point_rel_chord != 0.25:
        #    raise ValueError("if dihedral_as_translation is not zero, than rotation_point_rel_chord has to be 0.25!")
        self.coordinate_system = None

    def set_airfoil_coordinate_system(self, cs: Plane):
        """
        Sets the coordinate system for the airfoil.

        Args:
            cs (Plane): The plane representing the coordinate system.
        """
        self.coordinate_system = CoordinateSystem(cs.xDir.toTuple(), cs.yDir.toTuple(), cs.zDir.toTuple(), cs.origin.toTuple())

    def __repr__(self):
        """
        Returns a string representation of the airfoil instance.

        Returns:
            str: A formatted string representation of the airfoil's attributes.
        """
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)

    def __getstate__(self):
        """
        Prepares the airfoil instance for serialization by excluding the coordinate system.

        Returns:
            dict: The state of the airfoil instance without the coordinate system.
        """
        state = self.__dict__.copy()
        del state['coordinate_system']
        return state

    @staticmethod
    def from_json_dict(data: dict) -> 'Airfoil':
        """
        Create an Airfoil from a JSON dictionary.

        Args:
            data: Dictionary containing the Airfoil data.

        Returns:
            A new Airfoil instance.
        """
        return Airfoil(
            airfoil=data.get('airfoil'),
            chord=data.get('chord'),
            dihedral_as_rotation_in_degrees=data.get('dihedral_as_rotation_in_degrees', 0),
            dihedral_as_translation=data.get('dihedral_as_translation', 0),
            incidence=data.get('incidence', 0),
            rotation_point_rel_chord=data.get('rotation_point_rel_chord', 0.25)
        )
