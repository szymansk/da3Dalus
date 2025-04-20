import logging
import math
from typing import TypeVar, Any, List, Tuple, Union, Optional

import numpy as np
import aerosandbox as asb

from cadquery import Workplane, Plane, Vector
from numpy import ndarray, dtype, generic
from pydantic import PositiveFloat, PositiveInt, NonNegativeInt, NonNegativeFloat
from scipy.spatial.transform import Rotation
from scipy.interpolate import interp1d

from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment
from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
from cad_designer.airplane.types import Factor, TipType, CoordinateSystemBase

T = TypeVar("T", bound="WingConfiguration")

class WingConfiguration:
    """
    This class holds the definition of the wing defined by connected segments. The first segment
    defined by this class is the root segment.
    """
    def __init__(self: T,
                 nose_pnt: tuple[float, float, float],
                 root_airfoil: Airfoil,
                 length: PositiveFloat,
                 sweep: NonNegativeFloat = 0,
                 sweep_is_angle: bool = False,
                 tip_airfoil: Optional[Airfoil] = None,
                 number_interpolation_points: Optional[PositiveInt] = None,
                 spare_list: Optional[List[Spare]] = None,
                 trailing_edge_device: Optional[TrailingEdgeDevice] = None) -> T:
        self.segments: Union[list[WingSegment], None] = None
        self.nose_pnt: tuple[float, float, float] = nose_pnt

        if tip_airfoil.airfoil is None:
            tip_airfoil.airfoil = root_airfoil.airfoil

        root_segment = WingSegment(root_airfoil=root_airfoil, length=length, sweep=sweep, sweep_is_angle=sweep_is_angle, tip_airfoil=tip_airfoil,
                                   spare_list=spare_list, trailing_edge_device=trailing_edge_device,
                                   number_interpolation_points=number_interpolation_points, wing_segment_type='root')

        self.segments: list[WingSegment] = [root_segment]
        self._wing_workplanes: dict[Tuple[int,bool], Workplane] = {}
        self._wing_workplanes[(0, False)] = self.get_wing_workplane(0)
        self.segments[0].root_airfoil.set_airfoil_coordinate_system((self._wing_workplanes[(0,False)].plane))

        self._scaled_point_list: dict[str, list[tuple[float, float]]] = {}
        self._asb_wing: Optional[asb.Wing] = None

        for spare in [ spare for spare in (self.segments[0].spare_list or [])]:
            self._set_standard_spare_origin_vector(0, spare)

    def _get_standard_spare_origin_and_vector(self, start_segment, end_segment, spare_position_factor):
        if start_segment > end_segment:
            raise ValueError(f"start_segment {start_segment} cannot be greater than end_segment {end_segment}")

        tip_idx = end_segment + 1
        root_plane = self.get_wing_workplane(start_segment).plane
        tip_plane = self.get_wing_workplane(tip_idx).plane
        # the spare starts at the chord*spare_position_factor
        root_camber, diff_root = self.get_camber_y_at_rel_chord(segment=start_segment,
                                                       relative_chord=spare_position_factor)

        tip_camber, diff_tip = self.get_camber_y_at_rel_chord(segment=end_segment,
                                                      relative_chord=spare_position_factor,
                                                      relative_length=1.)
        spare_origin = (root_plane.origin
                        + root_plane.xDir * (self.segments[start_segment].root_airfoil.chord * spare_position_factor)
                        + root_plane.zDir * (root_camber+diff_root))
        spare_end = (tip_plane.origin
                     + tip_plane.xDir * (self.segments[end_segment].tip_airfoil.chord * spare_position_factor)
                     + tip_plane.zDir * (tip_camber+diff_tip))
        spare_vector = (spare_end - spare_origin).normalized()

        v = root_plane.toLocalCoords(spare_vector)
        o = root_plane.toLocalCoords(spare_origin)
        o.x = o.x + v.x
        v.x = 0
        spare_ortho_vector = root_plane.toWorldCoords(v)
        spare_ortho_origin = root_plane.toWorldCoords(o)

        return spare_vector, spare_origin, spare_ortho_vector, spare_ortho_origin

    def add_tip_segment(self: T,
                        tip_type: TipType,
                        length: PositiveFloat,
                        sweep: NonNegativeFloat = 0,
                        tip_airfoil: Optional[Airfoil] = None,
                        number_interpolation_points: Optional[PositiveInt] = None
                        ) -> None:
        tip_airfoil = tip_airfoil if tip_airfoil is not None else Airfoil()

        root_airfoil = Airfoil(airfoil= self.segments[-1].tip_airfoil.airfoil,
                               chord=self.segments[-1].tip_airfoil.chord,
                               dihedral_as_rotation_in_degrees=self.segments[-1].tip_airfoil.dihedral_as_rotation_in_degrees,
                               dihedral_as_translation=self.segments[-1].tip_airfoil.dihedral_as_translation,
                               incidence=self.segments[-1].tip_airfoil.incidence,
                               rotation_point_rel_chord=self.segments[-1].tip_airfoil.rotation_point_rel_chord)

        tip_airfoil.airfoil = tip_airfoil.airfoil if tip_airfoil.airfoil is not None else root_airfoil.airfoil
        tip_airfoil.chord = tip_airfoil.chord if tip_airfoil.chord is not None else self.segments[-1].tip_airfoil.chord
        nip = number_interpolation_points if number_interpolation_points is not None else self.segments[0].number_interpolation_points

        segment = WingSegment(root_airfoil=root_airfoil, length=length, sweep=sweep, tip_airfoil=tip_airfoil,
                              number_interpolation_points=nip, tip_type=tip_type, wing_segment_type='tip')
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        self._wing_workplanes[(segment_number, False)] = self.get_wing_workplane(segment_number)
        self.segments[segment_number].tip_airfoil.set_airfoil_coordinate_system((self._wing_workplanes[(segment_number,False)].plane))

    def add_segment(self: T,
                    length: PositiveFloat,
                    sweep: NonNegativeFloat = 0,
                    sweep_is_angle = False,
                    tip_airfoil: Optional[Airfoil] = None,
                    number_interpolation_points: Optional[PositiveInt] = None,
                    spare_list: Optional[List[Spare]] = None,
                    trailing_edge_device: Optional[TrailingEdgeDevice] = None
                    ) -> None:
        if self.segments[-1].wing_segment_type == 'tip':
            raise ValueError(f"The previous wing segment cannot be a '{self.segments[-1].wing_segment_type}'")

        root_airfoil = Airfoil(airfoil= self.segments[-1].tip_airfoil.airfoil,
                               chord=self.segments[-1].tip_airfoil.chord,
                               dihedral_as_rotation_in_degrees=self.segments[-1].tip_airfoil.dihedral_as_rotation_in_degrees,
                               dihedral_as_translation=self.segments[-1].tip_airfoil.dihedral_as_translation,
                               incidence=self.segments[-1].tip_airfoil.incidence,
                               rotation_point_rel_chord=self.segments[-1].tip_airfoil.rotation_point_rel_chord)

        tip_airfoil.airfoil = tip_airfoil.airfoil if tip_airfoil.airfoil is not None else root_airfoil.airfoil
        tip_airfoil.chord = tip_airfoil.chord if tip_airfoil.chord is not None else self.segments[-1].tip_airfoil.chord
        nip = number_interpolation_points if number_interpolation_points is not None else self.segments[
            0].number_interpolation_points

        segment = WingSegment(root_airfoil=root_airfoil, length=length, sweep=sweep, sweep_is_angle=sweep_is_angle,
                              tip_airfoil=tip_airfoil,
                              spare_list=spare_list, trailing_edge_device=trailing_edge_device,
                              number_interpolation_points=nip, tip_type=None, wing_segment_type='segment')
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        self._wing_workplanes[(segment_number, False)] = self.get_wing_workplane(segment_number)
        self.segments[segment_number].tip_airfoil.set_airfoil_coordinate_system((self._wing_workplanes[(segment_number, False)].plane))

        if self.segments[segment_number].spare_list is not None:
            for spare_idx in range(len(self.segments[segment_number].spare_list)):
                spare = self.segments[segment_number].spare_list[spare_idx]

                if spare.spare_position_factor is None:
                    spare.spare_position_factor = 0.25

                if spare.spare_mode == "follow":
                    # follows the previous spare vector
                    self._set_follow_spare_origin_vector(segment_number, spare, spare_idx)
                elif spare.spare_mode == "standard_backward" or spare.spare_mode == "orthogonal_backward":
                    start_segment = 0
                    for seg_num in reversed(range(segment_number)):
                        if len(self.segments[seg_num].spare_list) > spare_idx:
                            if self.segments[seg_num].spare_list[spare_idx].spare_mode != "follow":
                                found_spare = self.segments[seg_num].spare_list[spare_idx]
                                start_segment = seg_num
                                break

                    found_spare.spare_vector, found_spare.spare_origin, spare_orthogonal_vector, spare_orthogonal_origin = (
                        self._get_standard_spare_origin_and_vector(
                        start_segment=start_segment,
                        end_segment=segment_number,
                        spare_position_factor=found_spare.spare_position_factor))

                    if spare.spare_mode == 'orthogonal_backward':
                        found_spare.spare_vector = spare_orthogonal_vector
                        found_spare.spare_origin = spare_orthogonal_origin

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
                        spare.spare_origin = seg_plane.origin + seg_plane.xDir * (self.segments[segment_number].root_airfoil.chord*spare.spare_position_factor)
                    else:
                        spare.spare_origin = seg_plane.origin + spare.spare_origin
                    pass

    def _set_follow_spare_origin_vector(self, segment_number, spare, spare_idx):
        spare.spare_vector = self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
        spare.spare_origin = (self.segments[segment_number - 1].spare_list[spare_idx].spare_origin
                              + (self.segments[segment_number - 1].spare_list[spare_idx].spare_vector
                                 * self.segments[segment_number - 1].length))

    def _set_standard_spare_origin_vector(self, segment_number, spare):
        if spare.spare_position_factor is None:
            spare.spare_position_factor = 0.25
        if spare.spare_vector is None and spare.spare_position_factor is not None:
            # make spare vector following the spare_position_factor
            # that is centered inside of the airfoil at the camber (middle of surfaces)
            spare.spare_vector, _, _, _ = self._get_standard_spare_origin_and_vector(start_segment=segment_number,
                                                                               end_segment=segment_number,
                                                                               spare_position_factor=spare.spare_position_factor)
        elif spare.spare_vector is None:
            # make a perpendicular spare
            spare.spare_vector = self.get_wing_workplane(segment_number).plane.yDir
        else:
            # use spare_vector
            spare.spare_vector = spare.spare_vector.normalized()
        if spare.spare_origin is None:
            _, spare.spare_origin, _, _ = self._get_standard_spare_origin_and_vector(start_segment=segment_number,
                                                                               end_segment=segment_number,
                                                                               spare_position_factor=spare.spare_position_factor)

    def get_wing_workplane(self: T, segment: NonNegativeInt = 0, ignore_nose_point: bool = False) -> Workplane:
        """
        Creates a workplane for a specific wing segment.

        The workplane's origin (0-point) is located at the wing's nose point, and the plane is aligned with the wing's geometry.
        The X-axis points from the nose to the tail, the Y-axis points from the root along the nose to the tip, and the Z-axis points upwards.

        Parameters:
            segment (NonNegativeInt): The index of the wing segment for which the workplane is created. Defaults to 0 (root segment).
            ignore_nose_point (bool): If True, the nose point is ignored when calculating the workplane's origin (no translation of the wing). Defaults to False.

        Returns:
            Workplane: A `cadquery.Workplane` object representing the workplane for the specified wing segment.

        Remarks:
            - This method does not account for an incident angle at the wing tip.
            - The workplane is cached for each segment to improve performance.
        """

        if (segment, ignore_nose_point) in self._wing_workplanes.keys():
            return self._wing_workplanes[(segment, ignore_nose_point)]

        seg = 0
        if not ignore_nose_point:
            all_trans = [
                [1, 0, 0, self.nose_pnt[0]],
                [0, 1, 0, self.nose_pnt[1]],
                [0, 0, 1, self.nose_pnt[2]],
                [0, 0, 0, 1]]
        else:
            all_trans = [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]]

        for seg in reversed(range(segment)):
            airfoil_ref = self.segments[seg].tip_airfoil
            t_neg_rel_chord = [
                [1, 0, 0, -airfoil_ref.rotation_point_rel_chord * airfoil_ref.chord],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]]
            r_tip_incidence = self._create_homogeneous_rotation_matrix('y', airfoil_ref.incidence)
            r_tip_dihedral = self._create_homogeneous_rotation_matrix('x', airfoil_ref.dihedral_as_rotation_in_degrees)
            t_sweep_length = [
                [1, 0, 0, self.segments[seg].sweep],
                [0, 1, 0, self.segments[seg].length],
                [0, 0, 1, self.segments[seg].root_airfoil.dihedral_as_translation],
                [0, 0, 0, 1]]
            t_rel_chord = [
                [1, 0, 0, airfoil_ref.rotation_point_rel_chord * airfoil_ref.chord],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]]

            all_trans = np.matmul(t_neg_rel_chord, all_trans)
            all_trans = np.matmul(r_tip_incidence, all_trans)
            all_trans = np.matmul(r_tip_dihedral, all_trans)
            all_trans = np.matmul(t_sweep_length, all_trans)
            all_trans = np.matmul(t_rel_chord, all_trans)

        # process also the root airfoil for segment 0
        r_rel_chord = [
            [1, 0, 0, self.segments[seg].root_airfoil.rotation_point_rel_chord * self.segments[seg].root_airfoil.chord],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]]
        r_root_incidence = self._create_homogeneous_rotation_matrix('y', self.segments[seg].root_airfoil.incidence)
        r_root_dihedral = self._create_homogeneous_rotation_matrix('x', self.segments[seg].root_airfoil.dihedral_as_rotation_in_degrees)
        r_neg_rel_chord = [
            [1, 0, 0, -self.segments[seg].root_airfoil.rotation_point_rel_chord * self.segments[seg].root_airfoil.chord],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]]

        all_trans = np.matmul(r_neg_rel_chord, all_trans)
        all_trans = np.matmul(r_root_incidence, all_trans)
        all_trans = np.matmul(r_root_dihedral, all_trans)
        all_trans = np.matmul(r_rel_chord, all_trans)

        normal = all_trans.transpose()[2]
        origin = all_trans.transpose()[3]
        xdir = all_trans.transpose()[0]

        plane = Plane(origin=origin.tolist()[:3], xDir=xdir.tolist()[:3], normal=normal.tolist()[:3])

        wp_plane = (Workplane(inPlane=plane, origin=origin))

        self._wing_workplanes[(segment, ignore_nose_point)] = wp_plane
        return wp_plane

    def get_airfoil_points(self: T, segment: NonNegativeInt, isRoot: bool = False) -> list[tuple[float, float]]:
        """
        Returns the airfoils points as list
        """
        # lazy loading
        key = f"{segment}.{isRoot}"
        if key in self._scaled_point_list:
            return self._scaled_point_list[key]

        if isRoot:
            selig_file = self.segments[segment].root_airfoil.airfoil
            chord = self.segments[segment].root_airfoil.chord
        else:
            selig_file = self.segments[segment].tip_airfoil.airfoil
            chord = self.segments[segment].tip_airfoil.chord

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

        self._scaled_point_list[key] = [(p[0] * chord, p[1] * chord) for p in point_list]
        file.close()

        return self._scaled_point_list[key]

    def get_camber_y_at_rel_chord(self: T, segment: NonNegativeInt, relative_chord: Factor, relative_length: float = 0.) -> Tuple[float, float]:
        upper,  lower = self.get_points_on_surface(segment, relative_chord=relative_chord, relative_length=relative_length)
        up_ar = np.asarray(upper.toTuple())
        low_ar  = np.asarray(lower.toTuple())

        root_plane = self.get_wing_workplane(segment).plane
        tip_plane = self.get_wing_workplane(segment+1).plane

        # calculate the offset from the lower surface to the chord
        root_point = root_plane.origin + root_plane.xDir * (self.segments[segment].root_airfoil.chord * relative_chord)
        tip_point = tip_plane.origin + tip_plane.xDir * (self.segments[segment].tip_airfoil.chord * relative_chord)
        chord_point = root_point + (tip_point - root_point)*relative_length

        chord_to_lower_surface = lower - chord_point
        chord_to_lower_height = np.linalg.norm(np.asarray(chord_to_lower_surface.toTuple())) * np.sign(chord_to_lower_surface.z)

        return np.linalg.norm(up_ar - low_ar)/2, chord_to_lower_height

    def get_trailing_edge_device_planes(self: T, start_segment: NonNegativeInt, end_segment: NonNegativeInt) -> Tuple[Plane, Plane]:
        start_seg = self.segments[start_segment]
        start_ted = start_seg.trailing_edge_device
        end_seg = self.segments[end_segment]

        if start_ted is None:
            logging.warning("No trailing edge device")
            return None, None
        else:
            wing_wp = self.get_wing_workplane(start_segment)
            wing_wp_tip = self.get_wing_workplane(end_segment+1)

            origin_root = (wing_wp.plane.origin
                           + wing_wp.plane.xDir * start_seg.root_airfoil.chord * start_ted.rel_chord_root)
            origin_tip = (wing_wp_tip.plane.origin
                          + wing_wp_tip.plane.xDir * end_seg.tip_airfoil.chord * start_ted.rel_chord_tip)

            root_plane = Plane(origin=origin_root, xDir=wing_wp.plane.xDir, normal=wing_wp.plane.yDir)
            tip_plane = Plane(origin=origin_tip, xDir=wing_wp_tip.plane.xDir, normal=wing_wp_tip.plane.yDir)
            return root_plane, tip_plane

    def get_asb_wing(self, symmetric:bool = True) -> asb.Wing:
        # TODO: aerosandbox is in meters and not in mm we need to scale it
        if self._asb_wing is not None:
            return self._asb_wing
        sections = []

        is_root = True
        incidence_angle = 0
        ignore_nose_point = True
        import os
        for i, segment in enumerate(self.segments):
            if is_root:

                root_plane = self.get_wing_workplane(i, ignore_nose_point=ignore_nose_point).plane
                root_af = segment.root_airfoil

                if root_af.rotation_point_rel_chord != 0.25:
                    raise ValueError(f"WingXSec: {i} --> rotation_point_rel_chord must be 0.25 for aerosandbox")

                if segment.trailing_edge_device is not None:
                    if segment.trailing_edge_device.rel_chord_root != segment.trailing_edge_device.rel_chord_tip:
                        raise ValueError(f"WingXSec: {i} --> trailing_edge_device rel_chord should be the same for root and tip")

                control_surface = asb.ControlSurface(
                    name = segment.trailing_edge_device.name,
                    symmetric  = segment.trailing_edge_device.symmetric,
                    deflection = 0.0,
                    hinge_point = segment.trailing_edge_device.rel_chord_root,
                    trailing_edge = True,
                    analysis_specific_options = None) if segment.trailing_edge_device is not None else None

                incidence_angle += root_af.incidence
                root_origin = root_plane.origin
                root_section = asb.WingXSec(
                    chord=root_af.chord,
                    airfoil=asb.Airfoil(name=os.path.abspath(root_af.airfoil)),
                    twist=incidence_angle,
                    control_surfaces=[control_surface],
                ).translate([root_origin.x, root_origin.y, root_origin.z])
                sections.append(root_section)
                is_root = False

            tip_plane = self.get_wing_workplane(i + 1, ignore_nose_point=ignore_nose_point).plane
            tip_af = segment.tip_airfoil

            if tip_af.rotation_point_rel_chord != 0.25:
                raise ValueError(f"WingXSec: {i + 1} --> rotation_point_rel_chord must be 0.25 for aerosandbox")

            control_surface = asb.ControlSurface(
                name = segment.trailing_edge_device.name,
                symmetric = segment.trailing_edge_device.symmetric,
                deflection = 0.0,
                hinge_point = segment.trailing_edge_device.rel_chord_root,
                trailing_edge = True,
                analysis_specific_options = None) if segment.trailing_edge_device is not None else None

            incidence_angle += tip_af.incidence
            tip_origin = tip_plane.origin
            tip_section = asb.WingXSec(
                chord=tip_af.chord,
                airfoil=asb.Airfoil(name=os.path.abspath(tip_af.airfoil)),
                twist=incidence_angle,
                control_surfaces=[control_surface],
            ).translate([tip_origin.x, tip_origin.y, tip_origin.z])

            sections.append(tip_section)
            pass

        # create the aerosandbox wing
        self._asb_wing = (asb.Wing(xsecs=sections, symmetric=symmetric)
                            # translate the wing to the nose point
                            .translate(list(self.nose_pnt)))
        return self._asb_wing

    @staticmethod
    def _create_homogeneous_rotation_matrix(axis: str, degrees: float) -> ndarray[Any, dtype[generic | generic | Any]]:
        matrix = Rotation.from_euler(axis, degrees, degrees=True)
        matrix = matrix.as_matrix().copy()
        matrix = np.hstack((matrix, [[0], [0], [0]]))
        matrix = np.vstack((matrix, [0, 0, 0, 1]))
        return matrix

    def get_points_on_surface(self: T,
                              segment: NonNegativeInt,
                              relative_chord: Factor,
                              relative_length: float = 0.,
                              coordinate_system: CoordinateSystemBase = "world",
                              x_offset: float = .0,
                              z_offset: float = .0
                              ) -> Tuple[Vector, Vector]:
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
        x_root = relative_chord * self.segments[segment].root_airfoil.chord
        x,y = self._interpolate_y_at_x(root_points, x_root + x_offset)
        root_top = Vector(x,0,y)
        x,y = self._interpolate_y_at_x(root_points, x_root + x_offset, reverse=True)
        root_bottom = Vector(x,0,y)

        root_wp = self.get_wing_workplane(segment=segment)
        root_to_world = root_wp.plane.toWorldCoords(root_top.toTuple())
        root_bo_world = root_wp.plane.toWorldCoords(root_bottom.toTuple())

        x_tip = relative_chord * self.segments[segment].tip_airfoil.chord
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

    def __getstate__(self):
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                data[key] = value
        return data
