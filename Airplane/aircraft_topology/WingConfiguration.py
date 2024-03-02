from typing import TypeVar, Any, List, Tuple

import numpy as np
from cadquery import Workplane, Plane
from numpy import ndarray, dtype, generic
from scipy.spatial.transform import Rotation

T = TypeVar("T", bound="WingConfiguration")

class WingSegment:
    def __init__(self, root_airfoil: str,
                 length: float,
                 root_chord: float,
                 tip_chord: float,
                 sweep: float = 0,
                 root_dihedral: float = 0,
                 root_incidence: float = 0,
                 root_trailing_edge: float = 1,
                 tip_airfoil: str = None,
                 tip_dihedral: float = 0,
                 tip_incidence: float = 0,
                 tip_trailing_edge: float = 1):
        self.tip_trailing_edge = tip_trailing_edge
        self.root_trailing_edge = root_trailing_edge
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


class WingConfiguration:
    """
    This class holds the definition of the wing defined by connected segments. The first segment
    defined by this class is the root segment.
    """
    def __init__(self, root_airfoil: str,
                 nose_pnt: tuple[float, float, float],
                 length: float,
                 root_chord: float,
                 tip_chord: float,
                 sweep: float = 0,
                 root_dihedral: float = 0,
                 root_incidence: float = 0,
                 root_trailing_edge: float = 1,
                 tip_airfoil: str = None,
                 tip_dihedral: float = 0,
                 tip_incidence: float = 0,
                 tip_trailing_edge: float = 1):
        self.nose_pnt: tuple[float, float, float] = nose_pnt
        root_segment = WingSegment(root_airfoil, length, root_chord, tip_chord,
                                   sweep, root_dihedral, root_incidence, root_trailing_edge,
                                   tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge)
        self.segments: list[WingSegment] = [root_segment]

    def add_segment(self: T,
                    length: float,
                    tip_chord: float,
                    sweep: float = 0,
                    tip_airfoil: str = None,
                    tip_dihedral: float = 0,
                    tip_incidence: float = 0,
                    root_trailing_edge: float = 1,
                    tip_trailing_edge: float = 1 ):
        airfoil = self.segments[-1].root_airfoil if self.segments[-1].tip_airfoil is None else self.segments[-1].tip_airfoil
        tip_airfoil = airfoil if tip_airfoil is None else tip_airfoil
        segment = WingSegment(airfoil, length, self.segments[-1].tip_chord, tip_chord,
                              sweep, 0, 0, root_trailing_edge, tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge)
        self.segments.append(segment)

    def get_wing_workplane(self: T, segment: int = 0) -> Workplane:
        """
        Creating a workplane where the 0-point is located at the wing's nose point
        and the workplane is going through the wing.

        Remark: an incident angle at the wing_tip cannot be covered with this
        workplane.
        """
        seg = 0
        all_trans = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]]

        for seg in reversed(range(segment)):
            t_sweep_length = [
                [1, 0, 0, self.segments[seg].sweep],
                [0, 1, 0, self.segments[seg].length],
                [0, 0, 1, 0],
                [0, 0, 0, 1]]

            r_tip_dihedral = self._create_homogeneous_rotation_matrix('x', self.segments[seg].tip_dihedral)
            r_tip_incidence = self._create_homogeneous_rotation_matrix('y', self.segments[seg].tip_incidence)

            all_trans = np.matmul(r_tip_dihedral, all_trans)
            all_trans = np.matmul(r_tip_incidence, all_trans)
            all_trans = np.matmul(t_sweep_length, all_trans)

        r_root_incidence = self._create_homogeneous_rotation_matrix('y', self.segments[seg].root_incidence)
        r_root_dihedral = self._create_homogeneous_rotation_matrix('x', self.segments[seg].root_dihedral)

        all_trans = np.matmul(r_root_dihedral, all_trans)
        all_trans = np.matmul(r_root_incidence, all_trans)

        normal = all_trans.transpose()[2]
        origin = all_trans.transpose()[3]
        xdir = all_trans.transpose()[0]

        plane = Plane(origin=origin.tolist()[:3], xDir=xdir.tolist()[:3], normal=normal.tolist()[:3])

        wp_plane = (Workplane(inPlane=plane, origin=origin))

        return wp_plane

    def get_airfoil_points(self: T, segment: int, isRoot: bool = False) -> list[tuple[float, float]]:
        if segment == 0 and isRoot:
            selig_file = self.segments[segment].root_airfoil
            chord = self.segments[segment].root_chord
        elif isRoot:
            selig_file = self.segments[segment-1].tip_airfoil
            chord = self.segments[segment-1].tip_chord
        else:
            selig_file = self.segments[segment].tip_airfoil
            chord = self.segments[segment].tip_chord

        file = open(selig_file, "r")
        point_list = []
        for line_num, line in enumerate(file):
            line: str = line
            if line_num < 1:
                pass
            else:
                tokens = [n for n in line.strip().split(" ") if n != ""]
                tok_y = float(tokens[1])
                tok_x = float(tokens[0])
                point_list.append((tok_x, tok_y))

        scaled_point_list: list[tuple[float, float]] = [(p[0] * chord, p[1] * chord) for p in point_list]
        file.close()

        return scaled_point_list

    @staticmethod
    def _create_homogeneous_rotation_matrix(axis: str, degrees: float) -> ndarray[Any, dtype[generic | generic | Any]]:
        matrix = Rotation.from_euler(axis, degrees, degrees=True)
        matrix = matrix.as_matrix().copy()
        matrix = np.hstack((matrix, [[0], [0], [0]]))
        matrix = np.vstack((matrix, [0, 0, 0, 1]))
        return matrix
