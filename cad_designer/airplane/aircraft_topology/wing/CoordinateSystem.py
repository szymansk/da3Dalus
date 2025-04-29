from typing import List

import numpy as np
from scipy.spatial.transform import Rotation


class InvalidRotationOrderException(Exception):
    pass


class InvalidRotationMatrixException(Exception):
    pass


class CoordinateSystem:
    """
    Represents a coordinate system with its origin and three direction vectors.

    This class is a fundamental part of the chain of coordinate system transformations described by 
    the Airfoil and WingSegment classes. Each Airfoil has an associated CoordinateSystem that defines 
    its position and orientation in 3D space. The parameters of Airfoils and Segments (such as length, 
    dihedral, incidence, relative rotation point, and sweep) are used to calculate the transformations 
    between these coordinate systems.

    These transformations are relative, meaning each coordinate system is defined relative to the previous 
    one in the chain, creating a hierarchical structure of coordinate systems that defines the complete 
    geometry of the aircraft.
    """
    def __init__(self,
                 xDir: tuple[float,float,float] | List[float],
                 yDir: tuple[float,float,float] | List[float],
                 zDir: tuple[float,float,float] | List[float],
                 origin: tuple[float,float,float] | List[float]):
        """
        Initializes a CoordinateSystem instance.

        Args:
            xDir: The x-direction vector of the coordinate system.
            yDir: The y-direction vector of the coordinate system.
            zDir: The z-direction vector of the coordinate system.
            origin: The origin point of the coordinate system.

        Note:
            The direction vectors form a rotation matrix that, along with the origin, defines the 
            transformation from the parent coordinate system to this one. This is part of the chain 
            of transformations that defines the aircraft geometry.
        """
        self.xDir = list(xDir)
        self.yDir = list(yDir)
        self.zDir = list(zDir)
        self.origin = list(origin)
        R = np.matrix([xDir, yDir, zDir]).T
        self.euler_xyz: list[float] = CoordinateSystem._rotation_matrix_to_euler_angles( R,'XYZ').tolist()

    def __getstate__(self):
        """Convert the CoordinateSystem to a dictionary for JSON serialization."""
        return {
            "xDir": self.xDir,
            "yDir": self.yDir,
            "zDir": self.zDir,
            "origin": self.origin,
            "euler_xyz": self.euler_xyz
        }

    @classmethod
    def _is_valid_rotation_matrix(cls, R):
        """
        Check if a matrix is a valid rotation matrix.

        Parameters:
        R -- a 3x3 matrix

        Returns:
        bool -- True if R is a valid rotation matrix, False otherwise
        """
        if R.shape != (3, 3):
            return False
        should_be_identity = np.allclose(np.dot(R, R.T), np.identity(3), atol=1e-6)
        should_have_det_one = np.isclose(np.linalg.det(R), 1.0, atol=1e-6)
        return should_be_identity and should_have_det_one

    @classmethod
    def _rotation_matrix_to_euler_angles(cls, R_matrix, order='XYZ'):
        """
        Convert a rotation matrix to Euler angles using specified order.

        Parameters:
        R_matrix -- a 3x3 rotation matrix
        order -- a string specifying the rotation order, e.g., 'XYZ', 'ZYX'

        Returns:
        tuple -- Euler angles (alpha, beta, gamma) in degrees
        """
        if not cls._is_valid_rotation_matrix(R_matrix):
            raise InvalidRotationMatrixException("The provided matrix is not a valid rotation matrix.")

        r = Rotation.from_matrix(R_matrix)
        euler_angles = r.as_euler(order.lower(), degrees=True)
        return euler_angles

    @staticmethod
    def from_json_dict(data: dict) -> 'CoordinateSystem':
        """
        Create a CoordinateSystem from a JSON dictionary.

        Args:
            data: Dictionary containing the CoordinateSystem data.

        Returns:
            A new CoordinateSystem instance.
        """
        return CoordinateSystem(
            xDir=data.get('xDir', [1, 0, 0]),
            yDir=data.get('yDir', [0, 1, 0]),
            zDir=data.get('zDir', [0, 0, 1]),
            origin=data.get('origin', [0, 0, 0])
        )

    @staticmethod
    def from_json(file_path: str) -> 'CoordinateSystem':
        """
        Load a CoordinateSystem from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            A new CoordinateSystem instance.
        """
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return CoordinateSystem.from_json_dict(data)

    def save_to_json(self, file_path: str) -> None:
        """
        Save the CoordinateSystem to a JSON file.

        Args:
            file_path: Path to the JSON file.
        """
        import json
        with open(file_path, 'w') as f:
            json.dump(self.__getstate__(), f, indent=4)
