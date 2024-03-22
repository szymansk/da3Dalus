import logging
import sys
from typing import TypeVar, Any, List, Tuple, Literal, Union

import numpy as np
from cadquery import Workplane, Plane, Vector, Sketch, Matrix
from numpy import ndarray, dtype, generic
from scipy.spatial.transform import Rotation

from Airplane.aircraft_topology.ServoInformation import Servo

T = TypeVar("T", bound="WingConfiguration")
SpareMode = Literal["normal", "follow"]

class TrailingEdgeDevice:

    def __init__(self,
                 name: str,
                 rel_chord_root:float,
                 rel_chord_tip:float,
                 hinge_spacing:float,
                 side_spacing:float,
                 servo: Servo = None,
                 rel_chord_servo_position: float = None,
                 rel_length_servo_position: float = None,
                 positive_deflection_deg: float = 25,
                 negative_deflection_deg: float = 25,
                 trailing_edge_offset_factor: float = 1.0,
                 hinge_type: Literal["middle", "top", "top_simple", "round_inside", "round_outside"] = "top"
                 ):
        self.name = name
        self.rel_chord_root = rel_chord_root
        self.rel_chord_tip = rel_chord_tip
        self.hinge_spacing = hinge_spacing
        self.side_spacing = side_spacing

        self.servo = servo
        self.rel_chord_servo_position = rel_chord_servo_position
        self.rel_length_servo_position = rel_length_servo_position

        self.positive_deflection_deg = positive_deflection_deg
        self.negative_deflection_deg = negative_deflection_deg
        self.trailing_edge_offset_factor = trailing_edge_offset_factor
        self.suspension_type = hinge_type
        pass

class Spare:
    def __init__(self,
                 spare_support_dimension_width:float,
                 spare_support_dimension_height:float,
                 spare_length: float = None,
                 spare_vector: Tuple[float,float,float]= None,
                 spare_origin: Tuple[float,float,float] = None,
                 spare_mode: SpareMode = "normal"):
        self.spare_support_dimension_width = spare_support_dimension_width
        self.spare_support_dimension_height = spare_support_dimension_height
        self.spare_length = spare_length
        self.spare_mode = spare_mode
        self.spare_vector = Vector(spare_vector) if spare_vector is not None else None
        self.spare_origin = Vector(spare_origin) if spare_origin is not None else None

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
                 tip_trailing_edge: float = 1,
                 spare_list: List[Spare] = None,
                 trailing_edge_device: TrailingEdgeDevice = None):
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
        self.spare_list = spare_list
        self.trailing_edge_device = trailing_edge_device

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
                 tip_trailing_edge: float = 1,
                 spare_list: List[Spare] = None,
                trailing_edge_device: TrailingEdgeDevice = None):
        self.nose_pnt: tuple[float, float, float] = nose_pnt
        if tip_airfoil is None:
            tip_airfoil = root_airfoil
        root_segment = WingSegment(root_airfoil, length, root_chord, tip_chord,
                                   sweep, root_dihedral, root_incidence, root_trailing_edge,
                                   tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge,
                                   spare_list=spare_list, trailing_edge_device=trailing_edge_device)
        self.segments: list[WingSegment] = [root_segment]

        # spare vector is perpendicular
        for spare in self.segments[0].spare_list:
            if spare.spare_vector is None:
                spare.spare_vector = self.get_wing_workplane(0).plane.yDir
            else:
                # use spare_vector as offset to the perpendicular vector
                spare.spare_vector = spare.spare_vector.normalized()

            if spare.spare_origin is None:
                spare.spare_origin = Vector(self.segments[0].root_chord/3, 0., 0.)
            else:
                spare.spare_origin = spare.spare_origin
            pass

    def add_segment(self: T,
                    length: float,
                    tip_chord: float,
                    sweep: float = 0,
                    tip_airfoil: str = None,
                    tip_dihedral: float = 0,
                    tip_incidence: float = 0,
                    root_trailing_edge: float = 1,
                    tip_trailing_edge: float = 1,
                    spare_list: List[Spare] = None,
                    trailing_edge_device: TrailingEdgeDevice = None):
        root_airfoil = self.segments[-1].tip_airfoil
        if tip_airfoil is None: #continue with previous airfoil
            tip_airfoil = root_airfoil

        segment = WingSegment(root_airfoil, length, self.segments[-1].tip_chord, tip_chord,
                              sweep, 0, 0, root_trailing_edge,
                              tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge,
                              spare_list=spare_list, trailing_edge_device=trailing_edge_device)
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        for spare_idx in range(len(self.segments[segment_number].spare_list)):
            if self.segments[segment_number].spare_list[spare_idx].spare_mode == "follow":
                # follows the previous spare vector
                self.segments[segment_number].spare_list[spare_idx].spare_vector = self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
                self.segments[segment_number].spare_list[spare_idx].spare_origin = (self.segments[segment_number - 1].spare_list[spare_idx].spare_origin
                                                              + (self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
                                                                 * self.segments[segment_number - 1].length))

            elif self.segments[segment_number].spare_list[spare_idx].spare_mode == "normal":
                seg_plane = self.get_wing_workplane(segment_number).plane
                if self.segments[segment_number].spare_list[spare_idx].spare_vector is None:
                    self.segments[segment_number].spare_list[spare_idx].spare_vector = seg_plane.yDir

                else:
                    # use spare_vector as offset to the perpendicular vector
                    self.segments[segment_number].spare_list[spare_idx].spare_vector = self.segments[segment_number].spare_list[spare_idx].spare_vector.normalized()

                if self.segments[segment_number].spare_list[spare_idx].spare_origin is None:
                    self.segments[segment_number].spare_list[spare_idx].spare_origin = seg_plane.origin + Vector(self.segments[segment_number].root_chord / 3, 0., 0.)
                else:
                    self.segments[segment_number].spare_list[spare_idx].spare_origin = seg_plane.origin + self.segments[segment_number].spare_list[spare_idx].spare_origin
                pass

    def get_wing_workplane(self: T, segment: int = 0) -> Workplane:
        """
        Creating a workplane where the 0-point is located at the wing's nose point
        and the workplane is going through the wing. X is pointin from the nose to the tail,
        y is pointing from the root along the nose to the tip and z ist point upwards.

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
        if isRoot:
            selig_file = self.segments[segment].root_airfoil
            chord = self.segments[segment].root_chord
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

    def get_trailing_edge_device_planes(self: T, segment: int) -> Tuple[Plane, Plane]:
        seg = self.segments[segment]
        ted = seg.trailing_edge_device

        if ted is None:
            logging.warning("No trailing edge device")
            return None, None
        else:
            wing_wp = self.get_wing_workplane(segment)
            wing_wp_tip = self.get_wing_workplane(segment+1)

            origin_root = (wing_wp.plane.origin
                           + wing_wp.plane.xDir * seg.root_chord * ted.rel_chord_root)
            origin_tip = (wing_wp_tip.plane.origin
                          + wing_wp_tip.plane.xDir * seg.tip_chord * ted.rel_chord_tip)

            normal = wing_wp.plane.yDir
            root_plane = Plane(origin=origin_root, xDir=wing_wp.plane.xDir, normal=normal)
            tip_plane = Plane(origin=origin_tip, xDir=wing_wp_tip.plane.xDir, normal=normal)
            return root_plane, tip_plane

    @staticmethod
    def _create_homogeneous_rotation_matrix(axis: str, degrees: float) -> ndarray[Any, dtype[generic | generic | Any]]:
        matrix = Rotation.from_euler(axis, degrees, degrees=True)
        matrix = matrix.as_matrix().copy()
        matrix = np.hstack((matrix, [[0], [0], [0]]))
        matrix = np.vstack((matrix, [0, 0, 0, 1]))
        return matrix

    def get_points_on_surface(self: T, segment:int,
                              relative_chord:float, relative_length: float,
                              coordinate_system: Literal["world","wing","root_airfoil"]="world") -> Tuple[Vector, Vector]:
        """
        Returns the points on the surface (top, bottom) in the airfoil coordinatesystem.
        x points along the airfoil's center line, y points to the top, and z points along the nose

        Remark: only a two point interpolation is implemented, this leads to large deviations from the
        real surface on segments with high curvature (e.g. the nose)
        """
        root_points = self.get_airfoil_points(segment=segment, isRoot=True)
        tip_points = self.get_airfoil_points(segment=segment)

        # as we loft our wings only ruled lay all points on vector from the relative root to tip point
        # therefore we need to calculate the points (top/bottom surface) for root an tip airfoil
        x_root = relative_chord * self.segments[segment].root_chord
        x,y = self._interpolate_y_at_x(root_points, x_root)
        root_top = Vector(x,0,y)
        x,y = self._interpolate_y_at_x(root_points, x_root, reverse=True)
        root_bottom = Vector(x,0,y)

        root_wp = self.get_wing_workplane(segment=segment)
        root_to_world = root_wp.plane.toWorldCoords(root_top.toTuple())
        root_bo_world = root_wp.plane.toWorldCoords(root_bottom.toTuple())

        x_tip = relative_chord * self.segments[segment].tip_chord
        x,y = self._interpolate_y_at_x(tip_points, x_tip)
        tip_top = Vector(x, 0, y)
        x,y = self._interpolate_y_at_x(tip_points, x_tip, reverse=True)
        tip_bottom = Vector(x, 0, y)

        tip_wp = self.get_wing_workplane(segment=segment+1)
        tip_to_world = tip_wp.plane.toWorldCoords(tip_top.toTuple())
        tip_bo_world = tip_wp.plane.toWorldCoords(tip_bottom.toTuple())

        # interpolate along the length
        interpolated_top = (tip_to_world - root_to_world) * relative_length + root_to_world
        interpolated_bottom = (tip_bo_world - root_bo_world) * relative_length + root_bo_world

        if coordinate_system == "world":
            return interpolated_top, interpolated_bottom
        elif coordinate_system == "wing":
            return root_wp.plane.toLocalCoords(interpolated_top), root_wp.plane.toLocalCoords(interpolated_bottom)
        elif coordinate_system == "root_airfoil":
            it = root_wp.plane.toLocalCoords(interpolated_top)
            ib = root_wp.plane.toLocalCoords(interpolated_bottom)
            return Vector(it.x, it.z, it.y), Vector(ib.x, ib.z, ib.y)
        else:
            logging.critical(f"unknown coordinate system {coordinate_system}")
            raise ValueError(f"unknown coordinate system {coordinate_system}")

    def _interpolate_y_at_x(self, points, x, reverse=False) -> Tuple[float, float]:
        #TODO: implement a better interpolation that really follows the spline
        offset = -1
        rng = range(len(points))
        if reverse:
            offset = 1
            rng = reversed(rng)

        for idx in rng:
            x_l, y_l = points[idx]
            if x_l <= x:  # perform a linear interpolation
                x_r, y_r = points[idx + offset]
                u = (x_r - x) / (x_r - x_l)  # factor in this airfoil segment
                y_t = y_r - u * (y_r - y_l)
                x_t = x
                break
        return x_t, y_t