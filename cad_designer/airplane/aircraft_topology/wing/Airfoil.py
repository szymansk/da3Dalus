from typing import Optional

from cadquery import Plane
from pydantic import PositiveFloat

from cad_designer.airplane.aircraft_topology.wing.CoordinateSystem import CoordinateSystem
from cad_designer.airplane.types import DihedralInDegrees


class Airfoil:
    """
    Represents an airfoil with its geometric and aerodynamic properties.

    Used to define the shape and orientation of wing segments. Airfoils are described by Selig-file format,
    and their parameters are used for coordinate system transformations.

    Attributes:
        airfoil (Optional[str]): Identifier or path to the airfoil file.
        chord (Optional[PositiveFloat]): Chord length.
        dihedral_as_rotation_in_degrees (DihedralInDegrees): Dihedral angle as rotation in degrees.
        incidence (float): Angle of incidence (twist).
        coordinate_system (Optional[CoordinateSystem]): Associated coordinate system.
    """

    def __init__(self,
                 airfoil: Optional[str] = None,
                 chord: Optional[PositiveFloat] = None,
                 dihedral_as_rotation_in_degrees: DihedralInDegrees = 0,
                 incidence: float = 0):
        """
        Initializes an Airfoil instance.

        Args:
            airfoil (Optional[str]): The name or identifier of the airfoil.
            chord (Optional[PositiveFloat]): The chord length of the airfoil.
            dihedral_as_rotation_in_degrees (DihedralInDegrees): The dihedral angle as a rotation in degrees.
            incidence (float): The incidence angle of the airfoil.
        """
        self.airfoil: str = airfoil
        self.chord: float = chord
        self.dihedral_as_rotation_in_degrees: float = dihedral_as_rotation_in_degrees
        self.incidence: float = incidence
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
            incidence=data.get('incidence', 0),
        )
