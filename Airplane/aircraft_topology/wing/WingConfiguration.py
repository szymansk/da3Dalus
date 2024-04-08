import logging
import math
from typing import TypeVar, Any, List, Tuple, Literal

import numpy as np
from cadquery import Workplane, Plane, Vector
from numpy import ndarray, dtype, generic
from scipy.spatial.transform import Rotation
from scipy.interpolate import interp1d

from Airplane.aircraft_topology.wing.Spare import Spare
from Airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from Airplane.aircraft_topology.wing.WingSegment import WingSegment

T = TypeVar("T", bound="WingConfiguration")

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
                 number_interpolation_points: int=None,
                 spare_list: List[Spare] = None,
                 trailing_edge_device: TrailingEdgeDevice = None):
        self.nose_pnt: tuple[float, float, float] = nose_pnt
        if tip_airfoil is None:
            tip_airfoil = root_airfoil

        root_segment = WingSegment(root_airfoil, length, root_chord, tip_chord,
                                   sweep, root_dihedral, root_incidence, root_trailing_edge,
                                   tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge,
                                   spare_list=spare_list, trailing_edge_device=trailing_edge_device,
                                   number_interpolation_points=number_interpolation_points,
                                   wing_segment_type='root')

        self.segments: list[WingSegment] = [root_segment]
        self.wing_workplanes: dict[int, Workplane] = {}
        self.wing_workplanes[0] = self.get_wing_workplane(0)

        self.scaled_point_list: dict[str, list[tuple[float, float]]] = {}

        for spare in [ spare for spare in (self.segments[0].spare_list or [])]:
            self._set_standard_spare_origin_vector(0, spare)

    def _get_standard_spare_origin_and_vector(self, start_segment, end_segment, spare_position_factor):
        if start_segment > end_segment:
            raise ValueError(f"start_segment {start_segment} cannot be greater than end_segment {end_segment}")

        tip_idx = end_segment + 1
        root_plane = self.get_wing_workplane(start_segment).plane
        tip_plane = self.get_wing_workplane(tip_idx).plane
        # the spare starts at the chord*spare_position_factor
        root_chamber, diff_root = self.get_chamber_y_at_rel_chord(segment=start_segment,
                                                       relative_chord=spare_position_factor)

        tip_chamber, diff_tip = self.get_chamber_y_at_rel_chord(segment=end_segment,
                                                      relative_chord=spare_position_factor,
                                                      relative_length=1.)
        spare_origin = (root_plane.origin
                        + root_plane.xDir * (self.segments[start_segment].root_chord * spare_position_factor)
                        + root_plane.zDir * (root_chamber+diff_root))
        spare_end = (tip_plane.origin
                     + tip_plane.xDir * (self.segments[end_segment].tip_chord * spare_position_factor)
                     + tip_plane.zDir * (tip_chamber+diff_tip))
        spare_vector = (spare_end - spare_origin).normalized()
        return spare_vector, spare_origin

    def add_tip_segment(self: T,
                     tip_type: Literal['round','flat'],
                     length: float,
                     tip_chord: float,
                     sweep: float = 0,
                     tip_airfoil: str = None,
                     tip_dihedral: float = 0,
                     tip_incidence: float = 0,
                     number_interpolation_points: int = None):
        if self.segments[-1].wing_segment_type == 'tip':
            raise ValueError(f"The previous wing segment cannot be a '{self.segments[-1].wing_segment_type}'")

        root_airfoil = self.segments[-1].tip_airfoil
        if tip_airfoil is None:  # continue with previous airfoil
            tip_airfoil = root_airfoil

        nip = number_interpolation_points if number_interpolation_points is not None else self.segments[
            0].number_interpolation_points
        root_trailing_edge: float = 1.
        tip_trailing_edge: float = 1.
        segment = WingSegment(root_airfoil, length, self.segments[-1].tip_chord, tip_chord,
                              sweep, 0, 0, root_trailing_edge,
                              tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge,
                              number_interpolation_points=nip,
                              tip_type=tip_type,
                              wing_segment_type='tip')
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        self.wing_workplanes[segment_number] = self.get_wing_workplane(segment_number)

    def add_segment(self: T,
                    length: float,
                    tip_chord: float,
                    sweep: float = 0,
                    tip_airfoil: str = None,
                    tip_dihedral: float = 0,
                    tip_incidence: float = 0,
                    root_trailing_edge: float = 1,
                    tip_trailing_edge: float = 1,
                    number_interpolation_points: int = None,
                    spare_list: List[Spare] = None,
                    trailing_edge_device: TrailingEdgeDevice = None):
        if self.segments[-1].wing_segment_type == 'tip':
            raise ValueError(f"The previous wing segment cannot be a '{self.segments[-1].wing_segment_type}'")

        root_airfoil = self.segments[-1].tip_airfoil
        if tip_airfoil is None: #continue with previous airfoil
            tip_airfoil = root_airfoil

        nip = number_interpolation_points if number_interpolation_points is not None else self.segments[0].number_interpolation_points

        segment = WingSegment(root_airfoil, length, self.segments[-1].tip_chord, tip_chord,
                              sweep, 0, 0, root_trailing_edge,
                              tip_airfoil, tip_dihedral, tip_incidence, tip_trailing_edge,
                              spare_list=spare_list, trailing_edge_device=trailing_edge_device,
                              number_interpolation_points=nip,
                              tip_type=None,
                              wing_segment_type='segment')
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        self.wing_workplanes[segment_number] = self.get_wing_workplane(segment_number)

        if self.segments[segment_number].spare_list is not None:
            for spare_idx in range(len(self.segments[segment_number].spare_list)):
                spare = self.segments[segment_number].spare_list[spare_idx]

                if spare.spare_position_factor is None:
                    spare.spare_position_factor = 0.25

                if spare.spare_mode == "follow":
                    # follows the previous spare vector
                    self._set_follow_spare_origin_vector(segment_number, spare, spare_idx)
                elif spare.spare_mode == "standard_backward":
                    start_segment = 0
                    for seg_num in reversed(range(segment_number)):
                        if len(self.segments[seg_num].spare_list) > spare_idx:
                            if self.segments[seg_num].spare_list[spare_idx].spare_mode != "follow":
                                found_spare = self.segments[seg_num].spare_list[spare_idx]
                                start_segment = seg_num
                                break

                    found_spare.spare_vector, found_spare.spare_origin = self._get_standard_spare_origin_and_vector(
                        start_segment=start_segment,
                        end_segment=segment_number,
                        spare_position_factor=found_spare.spare_position_factor)

                    for seg_num in range(start_segment+1, segment_number+1):
                        follows_spare = self.segments[seg_num].spare_list[spare_idx]
                        self._set_follow_spare_origin_vector(seg_num, follows_spare, spare_idx)

                    pass

                elif spare.spare_mode == "standard":
                    self._set_standard_spare_origin_vector(segment_number, spare)
                elif spare.spare_mode == "normal":
                    seg_plane = self.get_wing_workplane(segment_number).plane
                    if spare.spare_vector is None:
                        spare.spare_vector = seg_plane.yDir

                    else:
                        # use spare_vector as offset to the perpendicular vector
                        spare.spare_vector = spare.spare_vector.normalized()

                    if spare.spare_origin is None:
                        spare.spare_origin = seg_plane.origin + seg_plane.xDir * (self.segments[segment_number].root_chord*spare.spare_position_factor)
                    else:
                        spare.spare_origin = seg_plane.origin + spare.spare_origin
                    pass

    def _set_follow_spare_origin_vector(self, segment_number, spare, spare_idx):
        spare.spare_vector = self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
        spare.spare_origin = (self.segments[segment_number - 1].spare_list[spare_idx].spare_origin
                              + (self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
                                 * self.segments[segment_number - 1].length))

    def _set_standard_spare_origin_vector(self, segment_number, spare):
        if spare.spare_vector is None and spare.spare_position_factor is not None:
            # make spare vector following the spare_position_factor
            # that is centered inside of the airfoil at the chamber (middle of surfaces)
            spare.spare_vector, _ = self._get_standard_spare_origin_and_vector(start_segment=segment_number,
                                                                               end_segment=segment_number,
                                                                               spare_position_factor=spare.spare_position_factor)
        elif spare.spare_vector is None:
            # make a perpendicular spare
            spare.spare_vector = self.get_wing_workplane(segment_number).plane.yDir
        else:
            # use spare_vector
            spare.spare_vector = spare.spare_vector.normalized()
        if spare.spare_origin is None:
            _, spare.spare_origin = self._get_standard_spare_origin_and_vector(start_segment=segment_number,
                                                                               end_segment=segment_number,
                                                                               spare_position_factor=spare.spare_position_factor)

    def get_wing_workplane(self: T, segment: int = 0) -> Workplane:
        """
        Creating a workplane where the 0-point is located at the wing's nose point
        and the workplane is going through the wing. X is pointin from the nose to the tail,
        y is pointing from the root along the nose to the tip and z ist point upwards.

        Remark: an incident angle at the wing_tip cannot be covered with this
        workplane.
        """

        if segment in self.wing_workplanes.keys():
            return self.wing_workplanes[segment]

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

            all_trans = np.matmul(r_tip_incidence, all_trans)
            all_trans = np.matmul(r_tip_dihedral, all_trans)
            all_trans = np.matmul(t_sweep_length, all_trans)

        r_root_incidence = self._create_homogeneous_rotation_matrix('y', self.segments[seg].root_incidence)
        r_root_dihedral = self._create_homogeneous_rotation_matrix('x', self.segments[seg].root_dihedral)

        all_trans = np.matmul(r_root_incidence, all_trans)
        all_trans = np.matmul(r_root_dihedral, all_trans)

        normal = all_trans.transpose()[2]
        origin = all_trans.transpose()[3]
        xdir = all_trans.transpose()[0]

        plane = Plane(origin=origin.tolist()[:3], xDir=xdir.tolist()[:3], normal=normal.tolist()[:3])

        wp_plane = (Workplane(inPlane=plane, origin=origin))

        self.wing_workplanes[segment] = wp_plane
        return wp_plane

    def get_airfoil_points(self: T, segment: int, isRoot: bool = False) -> list[tuple[float, float]]:
        """
        Returns the airfoils points as list
        """
        # lazy loading
        key = f"{segment}.{isRoot}"
        if key in self.scaled_point_list:
            return self.scaled_point_list[key]

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

        self.scaled_point_list[key] = [(p[0] * chord, p[1] * chord) for p in point_list]
        file.close()

        return self.scaled_point_list[key]

    def get_chamber_y_at_rel_chord(self: T, segment: int, relative_chord:float, relative_length: float = 0.) -> Tuple[float,Vector]:
        upper,  lower = self.get_points_on_surface(segment, relative_chord=relative_chord, relative_length=relative_length)
        up_ar = np.asarray(upper.toTuple())
        low_ar  = np.asarray(lower.toTuple())

        root_plane = self.get_wing_workplane(segment).plane
        tip_plane = self.get_wing_workplane(segment+1).plane

        # calculate the offset from the lower surface to the chord
        root_point = root_plane.origin + root_plane.xDir * (self.segments[segment].root_chord * relative_chord)
        tip_point = tip_plane.origin + tip_plane.xDir * (self.segments[segment].tip_chord * relative_chord)
        chord_point = root_point + (tip_point - root_point)*relative_length

        chord_to_lower_surface = lower - chord_point
        chord_to_lower_height = np.linalg.norm(np.asarray(chord_to_lower_surface.toTuple())) * np.sign(chord_to_lower_surface.z)

        return np.linalg.norm(up_ar - low_ar)/2, chord_to_lower_height

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

            root_plane = Plane(origin=origin_root, xDir=wing_wp.plane.xDir, normal=wing_wp.plane.yDir)
            tip_plane = Plane(origin=origin_tip, xDir=wing_wp_tip.plane.xDir, normal=wing_wp_tip.plane.yDir)
            return root_plane, tip_plane

    @staticmethod
    def _create_homogeneous_rotation_matrix(axis: str, degrees: float) -> ndarray[Any, dtype[generic | generic | Any]]:
        matrix = Rotation.from_euler(axis, degrees, degrees=True)
        matrix = matrix.as_matrix().copy()
        matrix = np.hstack((matrix, [[0], [0], [0]]))
        matrix = np.vstack((matrix, [0, 0, 0, 1]))
        return matrix

    def get_points_on_surface(self: T, segment:int,
                              relative_chord:float,
                              relative_length: float = 0.,
                              coordinate_system: Literal["world","wing","root_airfoil","tip_airfoil"]="world",
                              x_offset: float = .0,
                              z_offset: float = .0) -> Tuple[Vector, Vector]:
        """
        Returns the points on the surface (top, bottom) in the airfoil coordinate system.
        x points along the airfoil's center line, y points to the top, and z points along the nose

        Remark: only a two point interpolation is implemented, this leads to large deviations from the
        real surface on segments with high curvature (e.g. the nose)
        """
        root_points = self.get_airfoil_points(segment=segment, isRoot=True)
        tip_points = self.get_airfoil_points(segment=segment)

        # as we loft our wings only ruled. All points lie on vector from the relative root to tip point
        # therefore we need to calculate the points (top/bottom surface) for root and tip airfoil
        x_root = relative_chord * self.segments[segment].root_chord
        x,y = self._interpolate_y_at_x(root_points, x_root + x_offset)
        root_top = Vector(x,0,y)
        x,y = self._interpolate_y_at_x(root_points, x_root + x_offset, reverse=True)
        root_bottom = Vector(x,0,y)

        root_wp = self.get_wing_workplane(segment=segment)
        root_to_world = root_wp.plane.toWorldCoords(root_top.toTuple())
        root_bo_world = root_wp.plane.toWorldCoords(root_bottom.toTuple())

        x_tip = relative_chord * self.segments[segment].tip_chord
        x,y = self._interpolate_y_at_x(tip_points, x_tip + x_offset)
        tip_top = Vector(x, 0, y)
        x,y = self._interpolate_y_at_x(tip_points, x_tip + x_offset, reverse=True)
        tip_bottom = Vector(x, 0, y)

        tip_wp = self.get_wing_workplane(segment=segment+1)
        tip_to_world = tip_wp.plane.toWorldCoords(tip_top.toTuple())
        tip_bo_world = tip_wp.plane.toWorldCoords(tip_bottom.toTuple())

        # interpolate along the length
        interpolated_top = ((tip_to_world - root_to_world) * (relative_length + z_offset/self.segments[segment].length)
                            + root_to_world)
        interpolated_bottom = ((tip_bo_world - root_bo_world) * (relative_length + z_offset/self.segments[segment].length)
                               + root_bo_world)

        if coordinate_system == "world":
            return interpolated_top, interpolated_bottom
        elif coordinate_system == "wing":
            return root_wp.plane.toLocalCoords(interpolated_top), root_wp.plane.toLocalCoords(interpolated_bottom)
        elif coordinate_system == "root_airfoil":
            it = root_wp.plane.toLocalCoords(interpolated_top)
            ib = root_wp.plane.toLocalCoords(interpolated_bottom)
            return Vector(it.x, it.z, it.y), Vector(ib.x, ib.z, ib.y)
        elif coordinate_system == "tip_airfoil":
            tip_wp = self.get_wing_workplane(segment=segment+1)
            it = tip_wp.plane.toLocalCoords(interpolated_top)
            ib = tip_wp.plane.toLocalCoords(interpolated_bottom)
            return Vector(it.x, it.z, it.y), Vector(ib.x, ib.z, ib.y)
        else:
            logging.critical(f"unknown coordinate system {coordinate_system}")
            raise ValueError(f"unknown coordinate system {coordinate_system}")

    def _interpolate_y_at_x(self, points, x, reverse=False) -> Tuple[float, float]:
        # Extrahiere x- und y-Werte aus den Punkten
        if not reverse:
            x_values = [point[0] for point in points[:math.ceil(len(points)/2)]]
            y_values = [point[1] for point in points[:math.ceil(len(points)/2)]]
        else:
            x_values = [point[0] for point in points[math.floor(len(points)/2):]]
            y_values = [point[1] for point in points[math.floor(len(points)/2):]]

        # Erstelle eine Interpolationsfunktion
        interpolation_function = interp1d(x_values, y_values, kind='cubic')

        # Interpoliere den y-Wert für den gegebenen x-Wert
        interpolated_y = interpolation_function(x)
        return x, interpolated_y

    def __repr__(self):
        from pprint import pformat
        return pformat(vars(self), indent=4, width=1)