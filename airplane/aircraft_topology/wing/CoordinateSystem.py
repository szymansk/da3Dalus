from typing import List

import numpy as np
from scipy.spatial.transform import Rotation


class InvalidRotationOrderException(Exception):
    pass


class InvalidRotationMatrixException(Exception):
    pass


class CoordinateSystem:
    def __init__(self, xDir:tuple[float,float,float] | List[float], yDir:tuple[float,float,float] | List[float], zDir:tuple[float,float,float] | List[float], origin:tuple[float,float,float] | List[float]):
        self.xDir = list(xDir)
        self.yDir = list(yDir)
        self.zDir = list(zDir)
        self.origin = list(origin)
        R = np.matrix([xDir, yDir, zDir]).T
        self.euler_xyz: list[float] = CoordinateSystem._rotation_matrix_to_euler_angles( R,'XYZ').tolist()

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
