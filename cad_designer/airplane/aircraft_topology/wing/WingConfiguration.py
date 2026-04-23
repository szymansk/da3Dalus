from __future__ import annotations

import logging
from types import SimpleNamespace

from cad_designer.decorators.general_decorators import fluent_init

logger = logging.getLogger(__name__)

from functools import cached_property, cache

import math
from typing import TypeVar, Any, Literal

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


@fluent_init
class WingConfiguration:
    """
    Represents the configuration of a wing, defined by a sequence of connected segments.

    The WingConfiguration starts with a root segment and can be extended by additional segments and tip segments.
    Each segment is defined by its geometric and aerodynamic parameters, including airfoils, length, sweep, dihedral, and incidence.

    Attributes:
        nose_pnt (tuple[float, float, float]): The nose point of the wing, used as the origin for coordinate systems.
        segments (list[WingSegment]): Ordered list of wing segments, starting with the root segment.
        parameters (Literal["relative", "aerosandbox"]): Determines how coordinate systems are calculated.
        symmetric (bool): Whether the wing is symmetric.

    Methods:
        add_segment(...): Adds a new segment to the wing.
        add_tip_segment(...): Adds a tip segment to the wing.
        get_wing_workplane(...): Returns a workplane for a given segment, optionally ignoring the nose point.
        _get_relative_segment_coordinate_system(...): Calculates the relative coordinate system for a segment.
        _get_standard_spare_origin_and_vector(...): Calculates the origin and vector for a spare.
        _set_standard_spare_origin_vector(...): Sets the standard origin and vector for a spare.
        _set_follow_spare_origin_vector(...): Sets the origin and vector for a spare that follows another spare.

    Note:
        The documentation follows the Python implementation as the single point of truth.
        Nullable dihedral fields are normalized to numeric zeros for geometry calculations.
    """

    @staticmethod
    def _normalize_airfoil_dihedral_members(airfoil: Airfoil) -> None:
        """
        Geometry code expects numeric values. Convert nullable fields to zeros.
        """
        if airfoil.dihedral_as_rotation_in_degrees is None:
            airfoil.dihedral_as_rotation_in_degrees = 0.0

    def __init__(self: T,
                 nose_pnt: tuple[float, float, float],
                 root_airfoil: Airfoil,
                 length: PositiveFloat,
                 sweep: NonNegativeFloat = 0,
                 sweep_is_angle: bool = False,
                 tip_airfoil: Airfoil | None = None,
                 number_interpolation_points: PositiveInt | None = None,
                 spare_list: list[Spare] | None = None,
                 trailing_edge_device: TrailingEdgeDevice | None = None,
                 symmetric: bool = True,
                 parameters: Literal["relative", "aerosandbox"] = "relative") -> T:
        self.segments: list[WingSegment] | None = None
        self.nose_pnt: tuple[float, float, float] = nose_pnt
        self.parameters: Literal["relative", "aerosandbox"] = parameters

        tip_airfoil = tip_airfoil if tip_airfoil is not None else Airfoil()
        if tip_airfoil.airfoil is None:
            tip_airfoil.airfoil = root_airfoil.airfoil

        self._normalize_airfoil_dihedral_members(root_airfoil)
        self._normalize_airfoil_dihedral_members(tip_airfoil)

        root_segment = WingSegment(root_airfoil=root_airfoil, length=length, sweep=sweep, sweep_is_angle=sweep_is_angle,
                                   tip_airfoil=tip_airfoil,
                                   spare_list=spare_list, trailing_edge_device=trailing_edge_device,
                                   number_interpolation_points=number_interpolation_points, wing_segment_type='root')

        self.segments: list[WingSegment] = [root_segment]
        self._wing_workplanes: dict[tuple[int, bool], Workplane] = {}
        self._wing_workplanes[(0, False)] = self.get_wing_workplane(0)
        self.segments[0].root_airfoil.set_airfoil_coordinate_system((self._wing_workplanes[(0, False)].plane))

        self._scaled_point_list: dict[str, list[tuple[float, float]]] = {}
        self._asb_wing: asb.Wing | None = None

        self.symmetric: bool = symmetric

        for spare in [spare for spare in (self.segments[0].spare_list or [])]:
            self._set_standard_spare_origin_vector(0, spare)

    @property
    def length(self) -> float:
        """
        Returns the length of the root segment.

        Returns:
            float: The length of the first segment, which defines the spanwise extent of the root segment.
        """
        return self.segments[0].length if self.segments else 0.0

    @length.setter
    def length(self, value: float) -> None:
        """
        Sets the length of the root segment.

        Parameters:
            value (float): The new length for the root segment.
        """
        if not self.segments:
            raise AttributeError("WingConfiguration has no segments.")
        self.segments[0].length = value

    @property
    def sweep(self) -> float:
        """
        Returns the sweep of the root segment.

        Returns:
            float: The sweep value (either distance or angle) for the root segment.
        """
        return self.segments[0].sweep if self.segments else 0.0

    @sweep.setter
    def sweep(self, value: float) -> None:
        """
        Sets the sweep of the root segment.

        Parameters:
            value (float): The new sweep value for the root segment.
        """
        if not self.segments:
            raise AttributeError("WingConfiguration has no segments.")
        self.segments[0].sweep = value

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
                        + root_plane.zDir * (root_camber + diff_root))
        spare_end = (tip_plane.origin
                     + tip_plane.xDir * (self.segments[end_segment].tip_airfoil.chord * spare_position_factor)
                     + tip_plane.zDir * (tip_camber + diff_tip))
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
                        tip_airfoil: Airfoil | None = None,
                        number_interpolation_points: PositiveInt | None = None
                        ) -> T:
        """
        Adds a tip segment to the wing configuration.

        Parameters:
            tip_type (TipType): The type of the tip ('flat', 'round').
            length (PositiveFloat): The length of the tip segment.
            sweep (NonNegativeFloat): The sweep of the tip segment.
            tip_airfoil (Airfoil | None): The airfoil at the tip of the segment.
            number_interpolation_points (PositiveInt | None): Number of points for airfoil interpolation.

        Returns:
            WingConfiguration: The updated WingConfiguration instance.

        Note:
            Tip segments are special segments that define the wing tip geometry and do not have spares or trailing edge devices.
        """
        tip_airfoil = tip_airfoil if tip_airfoil is not None else Airfoil()
        self._normalize_airfoil_dihedral_members(tip_airfoil)

        root_airfoil = Airfoil(airfoil=self.segments[-1].tip_airfoil.airfoil,
                               chord=self.segments[-1].tip_airfoil.chord,
                               dihedral_as_rotation_in_degrees=self.segments[
                                   -1].tip_airfoil.dihedral_as_rotation_in_degrees,
                               incidence=self.segments[-1].tip_airfoil.incidence)
        self._normalize_airfoil_dihedral_members(root_airfoil)

        tip_airfoil.airfoil = tip_airfoil.airfoil if tip_airfoil.airfoil is not None else root_airfoil.airfoil
        tip_airfoil.chord = tip_airfoil.chord if tip_airfoil.chord is not None else self.segments[-1].tip_airfoil.chord
        nip = number_interpolation_points if number_interpolation_points is not None else self.segments[
            0].number_interpolation_points

        segment = WingSegment(root_airfoil=root_airfoil, length=length, sweep=sweep, tip_airfoil=tip_airfoil,
                              number_interpolation_points=nip, tip_type=tip_type, wing_segment_type='tip')
        self.segments.append(segment)

        segment_number = len(self.segments) - 1

        self._wing_workplanes[(segment_number, False)] = self.get_wing_workplane(segment_number)
        self.segments[segment_number].tip_airfoil.set_airfoil_coordinate_system(
            (self._wing_workplanes[(segment_number, False)].plane))
        return self

    def add_segment(self: T,
                    length: PositiveFloat,
                    sweep: NonNegativeFloat = 0,
                    sweep_is_angle=False,
                    tip_airfoil: Airfoil | None = None,
                    number_interpolation_points: PositiveInt | None = None,
                    spare_list: list[Spare] | None = None,
                    trailing_edge_device: TrailingEdgeDevice | None = None
                    ) -> T:
        """
        Adds a new segment to the wing configuration.

        Parameters:
            length (PositiveFloat): The length of the segment.
            sweep (NonNegativeFloat): The sweep of the segment.
            sweep_is_angle (bool): If True, sweep is interpreted as an angle.
            tip_airfoil (Airfoil | None): The airfoil at the tip of the segment.
            number_interpolation_points (PositiveInt | None): Number of points for airfoil interpolation.
            spare_list (list[Spare] | None): List of spares for the segment.
            trailing_edge_device (TrailingEdgeDevice | None): Trailing edge device for the segment.

        Returns:
            WingConfiguration: The updated WingConfiguration instance.

        Note:
            Segments are added after the root segment and define the main structure of the wing.
        """
        if self.segments[-1].wing_segment_type == 'tip':
            raise ValueError(f"The previous wing segment cannot be a '{self.segments[-1].wing_segment_type}'")

        tip_airfoil = tip_airfoil if tip_airfoil is not None else Airfoil()
        self._normalize_airfoil_dihedral_members(tip_airfoil)

        root_airfoil = Airfoil(airfoil=self.segments[-1].tip_airfoil.airfoil,
                               chord=self.segments[-1].tip_airfoil.chord,
                               dihedral_as_rotation_in_degrees=self.segments[
                                   -1].tip_airfoil.dihedral_as_rotation_in_degrees,
                               incidence=self.segments[-1].tip_airfoil.incidence)
        self._normalize_airfoil_dihedral_members(root_airfoil)

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
        self.segments[segment_number].tip_airfoil.set_airfoil_coordinate_system(
            (self._wing_workplanes[(segment_number, False)].plane))

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

                    for seg_num in range(start_segment + 1, segment_number + 1):
                        follows_spare = self.segments[seg_num].spare_list[spare_idx]
                        self._set_follow_spare_origin_vector(seg_num, follows_spare, spare_idx)


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
                        spare.spare_origin = seg_plane.origin + seg_plane.xDir * (
                                    self.segments[segment_number].root_airfoil.chord * spare.spare_position_factor)
                    else:
                        spare.spare_origin = seg_plane.origin + spare.spare_origin
        return self

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

        Parameters:
            segment (NonNegativeInt): The index of the wing segment for which the workplane is created. Defaults to 0 (root segment).
            ignore_nose_point (bool): If True, the nose point is ignored when calculating the workplane's origin.

        Returns:
            Workplane: A cadquery.Workplane object representing the workplane for the specified segment.

        Note:
            The workplane is aligned with the segment's geometry and cached for performance.
        """

        if self.parameters == "aerosandbox":
            all_trans = self._get_absolute_segment_coordinate_system(segment, ignore_nose_point)
        elif self.parameters == "relative":
            all_trans = self._get_relative_segment_coordinate_system(segment, ignore_nose_point)
        else:
            raise ValueError(f"Unknown parameter type {self.parameters}, should be 'absolute' or 'relative'")

        normal = all_trans.transpose()[2]
        origin = all_trans.transpose()[3]
        xdir = all_trans.transpose()[0]

        plane = Plane(origin=origin.tolist()[:3], xDir=xdir.tolist()[:3], normal=normal.tolist()[:3])

        wp_plane = (Workplane(inPlane=plane, origin=origin))

        self._wing_workplanes[(segment, ignore_nose_point)] = wp_plane
        return wp_plane

    def _get_relative_segment_coordinate_system(self, segment, ignore_nose_point=True):
        """Decoupled frame computation: incidence does not propagate into positions.

        Position chain uses only dihedral (R_x) + translation.
        Twist (R_y) is accumulated separately and applied once at the end.
        This makes the frame exactly equal to ASB's R_x(gamma) . R_y(twist) convention.
        """
        # Accumulate dihedral and twist angles starting from root
        gamma_accum = self.segments[0].root_airfoil.dihedral_as_rotation_in_degrees
        theta_accum = self.segments[0].root_airfoil.incidence

        # Position: start at origin (nose_pnt applied at the end if needed)
        xyz_le = np.zeros(3)

        for seg in range(segment):
            airfoil_ref = self.segments[seg].tip_airfoil

            # Position: only dihedral rotates the translation vector
            r_x = np.array(self._create_homogeneous_rotation_matrix('x', gamma_accum))[:3, :3]
            offset = r_x @ np.array([
                self.segments[seg].sweep,
                self.segments[seg].length,
                0.0,  # z-offset is always 0; dihedral handled by rotation
            ])
            xyz_le += offset

            # Accumulate angles for next xsec
            gamma_accum += airfoil_ref.dihedral_as_rotation_in_degrees
            theta_accum += airfoil_ref.incidence

        # Build homogeneous matrix: R_x(gamma) . R_y(theta) + translation
        r_dihedral = np.array(self._create_homogeneous_rotation_matrix('x', gamma_accum))
        r_incidence = np.array(self._create_homogeneous_rotation_matrix('y', theta_accum))

        nose_point_trans = np.eye(4)
        if not ignore_nose_point:
            nose_point_trans[:3, 3] = self.nose_pnt

        # Position in homogeneous matrix
        t_pos = np.eye(4)
        t_pos[:3, 3] = xyz_le

        H = nose_point_trans @ t_pos @ r_dihedral @ r_incidence

        return H

    def _get_absolute_segment_coordinate_system(self, segment, ignore_nose_point=True):
        """Decoupled absolute frame computation.

        Same decoupling as relative mode: position from dihedral only,
        twist applied locally at the end.
        """
        if segment == 0:
            r_dihedral_deg = self.segments[0].root_airfoil.dihedral_as_rotation_in_degrees
            r_incidence_deg = self.segments[0].root_airfoil.incidence
            t_sweep = 0
            t_length = 0
        else:
            r_dihedral_deg = self.segments[segment - 1].tip_airfoil.dihedral_as_rotation_in_degrees
            r_incidence_deg = self.segments[segment - 1].tip_airfoil.incidence
            t_sweep = self.segments[segment - 1].sweep
            t_length = self.segments[segment - 1].length

        r_incidence = np.array(self._create_homogeneous_rotation_matrix('y', r_incidence_deg))
        r_dihedral = np.array(self._create_homogeneous_rotation_matrix('x', r_dihedral_deg))

        t_sweep_length = np.eye(4)
        t_sweep_length[0, 3] = t_sweep
        t_sweep_length[1, 3] = t_length

        nose_point_trans = np.eye(4)
        if not ignore_nose_point:
            nose_point_trans[:3, 3] = self.nose_pnt

        # Decoupled: position from sweep+length only,
        # then R_x(dihedral) . R_y(incidence)
        H = nose_point_trans @ t_sweep_length @ r_dihedral @ r_incidence

        return H

    def get_airfoil_points(self: T, segment: NonNegativeInt, isRoot: bool = False) -> list[tuple[float, float]]:
        """
        Returns the airfoil points for a given segment.

        Parameters:
            segment (NonNegativeInt): The index of the segment.
            isRoot (bool): If True, returns the root airfoil points; otherwise, returns the tip airfoil points.

        Returns:
            list[tuple[float, float]]: List of (x, y) points describing the airfoil shape, scaled by chord length.
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

    def get_camber_y_at_rel_chord(self: T, segment: NonNegativeInt, relative_chord: Factor,
                                  relative_length: float = 0.) -> tuple[float, float]:
        """
        Calculates the camber height and offset at a given relative chord position for a segment.

        Parameters:
            segment (NonNegativeInt): The index of the segment.
            relative_chord (Factor): Relative position along the chord (0 to 1).
            relative_length (float): Relative position along the segment length (0 to 1).

        Returns:
            tuple[float, float]: (camber height, offset from lower surface to chord).
        """
        upper, lower = self.get_points_on_surface(segment, relative_chord=relative_chord,
                                                  relative_length=relative_length)
        up_ar = np.asarray(upper.toTuple())
        low_ar = np.asarray(lower.toTuple())

        root_plane = self.get_wing_workplane(segment).plane
        tip_plane = self.get_wing_workplane(segment + 1).plane

        # calculate the offset from the lower surface to the chord
        root_point = root_plane.origin + root_plane.xDir * (self.segments[segment].root_airfoil.chord * relative_chord)
        tip_point = tip_plane.origin + tip_plane.xDir * (self.segments[segment].tip_airfoil.chord * relative_chord)
        chord_point = root_point + (tip_point - root_point) * relative_length

        chord_to_lower_surface = lower - chord_point
        chord_to_lower_height = np.linalg.norm(np.asarray(chord_to_lower_surface.toTuple())) * np.sign(
            chord_to_lower_surface.z)

        return np.linalg.norm(up_ar - low_ar) / 2, chord_to_lower_height

    def get_trailing_edge_device_planes(self: T, start_segment: NonNegativeInt, end_segment: NonNegativeInt) -> Tuple[
        Plane, Plane]:
        """
        Returns the planes for the trailing edge device between two segments.

        Parameters:
            start_segment (NonNegativeInt): Index of the starting segment.
            end_segment (NonNegativeInt): Index of the ending segment.

        Returns:
            tuple[Plane, Plane]: Planes at the root and tip for the trailing edge device.

        Note:
            Returns (None, None) if no trailing edge device is present.
        """
        start_seg = self.segments[start_segment]
        start_ted = start_seg.trailing_edge_device
        end_seg = self.segments[end_segment]

        if start_ted is None:
            logger.warning("No trailing edge device")
            return None, None
        else:
            wing_wp = self.get_wing_workplane(start_segment)
            wing_wp_tip = self.get_wing_workplane(end_segment + 1)

            origin_root = (wing_wp.plane.origin
                           + wing_wp.plane.xDir * start_seg.root_airfoil.chord * start_ted.rel_chord_root)
            origin_tip = (wing_wp_tip.plane.origin
                          + wing_wp_tip.plane.xDir * end_seg.tip_airfoil.chord * start_ted.rel_chord_tip)

            root_plane = Plane(origin=origin_root, xDir=wing_wp.plane.xDir, normal=wing_wp.plane.yDir)
            tip_plane = Plane(origin=origin_tip, xDir=wing_wp_tip.plane.xDir, normal=wing_wp_tip.plane.yDir)
            return root_plane, tip_plane

    @cache
    def asb_wing(self, scale: float = 1.0) -> asb.Wing:
        """
        Converts the WingConfiguration to an Aerosandbox Wing object.

        Parameters:
            scale (float): Scaling factor for the geometry.

        Returns:
            asb.Wing: The corresponding Aerosandbox Wing object.

        Note:
            Only compatible if all airfoil parameters and trailing edge device settings match Aerosandbox requirements.
        """
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

                # Note: no rc=0.25 guard. ``root_plane.origin`` is the
                # rotated LE position of the root airfoil in Wing's
                # frame regardless of rc — asb stores that as
                # ``xyz_le`` and uses the LE as its twist pivot
                # (rc_asb = 0). Any Wing rc value therefore converts
                # cleanly; see cad-modelling-service-121.

                if segment.trailing_edge_device is not None:
                    if segment.trailing_edge_device.rel_chord_root != segment.trailing_edge_device.rel_chord_tip:
                        logger.debug(
                            f"WingXSec: {i} --> trailing_edge_device rel_chord should be the same for root and tip")
                        raise ValueError(
                            f"WingXSec: {i} --> trailing_edge_device rel_chord should be the same for root and tip")

                control_surface = asb.ControlSurface(
                    name=segment.trailing_edge_device.name,
                    symmetric=segment.trailing_edge_device.symmetric,
                    deflection=0.0,
                    hinge_point=segment.trailing_edge_device.rel_chord_root,
                    trailing_edge=True,
                    analysis_specific_options=None) if segment.trailing_edge_device is not None else None

                incidence_angle += root_af.incidence
                root_origin = root_plane.origin
                root_section = asb.WingXSec(
                    chord=root_af.chord * scale,
                    airfoil=asb.Airfoil(name=os.path.abspath(root_af.airfoil)),
                    twist=incidence_angle,
                    control_surfaces=[control_surface] if control_surface is not None else None,
                    analysis_specific_options={
                        asb.AVL: {
                            "spanwise_resolution": 12,
                            "spanwise_spacing": "cosine",
                            "cl_alpha_factor": None,  # This is a float
                            "drag_polar": {
                                "CL1": 0,
                                "CD1": 0,
                                "CL2": 0,
                                "CD2": 0,
                                "CL3": 0,
                                "CD3": 0,
                            },
                        }},
                ).translate([root_origin.x * scale, root_origin.y * scale, root_origin.z * scale])
                sections.append(root_section)
                is_root = False

            tip_plane = self.get_wing_workplane(i + 1, ignore_nose_point=ignore_nose_point).plane
            tip_af = segment.tip_airfoil

            # Note: no rc=0.25 guard on the tip either — same reason
            # as the root above. See cad-modelling-service-121.

            control_surface = asb.ControlSurface(
                name=segment.trailing_edge_device.name,
                symmetric=segment.trailing_edge_device.symmetric,
                deflection=0.0,
                hinge_point=segment.trailing_edge_device.rel_chord_root,
                trailing_edge=True,
                analysis_specific_options=None) if segment.trailing_edge_device is not None else None

            incidence_angle += tip_af.incidence
            tip_origin = tip_plane.origin
            tip_section = asb.WingXSec(
                chord=tip_af.chord * scale,
                airfoil=asb.Airfoil(name=os.path.abspath(tip_af.airfoil)),
                twist=incidence_angle,
                control_surfaces=[control_surface] if control_surface is not None else None,
            ).translate([tip_origin.x * scale, tip_origin.y * scale, tip_origin.z * scale])

            sections.append(tip_section)

        # create the aerosandbox wing
        self._asb_wing = (asb.Wing(xsecs=sections,
                                   symmetric=self.symmetric,
                                   color=None,
                                   analysis_specific_options={
                                       asb.AVL: {
                                           "wing_level_spanwise_spacing": True,
                                           "spanwise_resolution": int(round(tip_origin.y * scale * 50)),
                                           "spanwise_spacing": "cosine",
                                           "chordwise_resolution": 12,
                                           "chordwise_spacing": "cosine",
                                           "component": None,  # This is an int
                                           "no_wake": False,
                                           "no_alpha_beta": False,
                                           "no_load": False,
                                           "drag_polar": {
                                               "CL1": 0,
                                               "CD1": 0,
                                               "CL2": 0,
                                               "CD2": 0,
                                               "CL3": 0,
                                               "CD3": 0,
                                           },
                                       }}
                                   )
                          # translate the wing to the nose point
                          .translate([x * scale for x in self.nose_pnt]))
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
                              ) -> tuple[Vector, Vector]:
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
        x, y = self._interpolate_y_at_x(root_points, x_root + x_offset)
        root_top = Vector(x, 0, y)
        x, y = self._interpolate_y_at_x(root_points, x_root + x_offset, reverse=True)
        root_bottom = Vector(x, 0, y)

        root_wp = self.get_wing_workplane(segment=segment)
        root_to_world = root_wp.plane.toWorldCoords(root_top.toTuple())
        root_bo_world = root_wp.plane.toWorldCoords(root_bottom.toTuple())

        x_tip = relative_chord * self.segments[segment].tip_airfoil.chord
        x, y = self._interpolate_y_at_x(tip_points, x_tip + x_offset)
        tip_top = Vector(x, 0, y)
        x, y = self._interpolate_y_at_x(tip_points, x_tip + x_offset, reverse=True)
        tip_bottom = Vector(x, 0, y)

        tip_wp = self.get_wing_workplane(segment=segment + 1)
        tip_to_world = tip_wp.plane.toWorldCoords(tip_top.toTuple())
        tip_bo_world = tip_wp.plane.toWorldCoords(tip_bottom.toTuple())

        # interpolate along the length
        interpolated_top = (
                    (tip_to_world - root_to_world) * (relative_length + z_offset / self.segments[segment].length)
                    + root_to_world)
        interpolated_bottom = (
                    (tip_bo_world - root_bo_world) * (relative_length + z_offset / self.segments[segment].length)
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
            tip_wp = self.get_wing_workplane(segment=segment + 1)
            it = tip_wp.plane.toLocalCoords(interpolated_top)
            ib = tip_wp.plane.toLocalCoords(interpolated_bottom)
            return Vector(it.x, it.z, it.y), Vector(ib.x, ib.z, ib.y)
        else:
            logger.critical(f"unknown coordinate system {coordinate_system}")
            raise ValueError(f"unknown coordinate system {coordinate_system}")

    def _interpolate_y_at_x(self, points, x, reverse=False) -> tuple[float, float]:
        # Extrahiere x- und y-Werte aus den Punkten
        if not reverse:
            x_values = [point[0] for point in points[:math.ceil(len(points) / 2)]]
            y_values = [point[1] for point in points[:math.ceil(len(points) / 2)]]
        else:
            x_values = [point[0] for point in points[math.floor(len(points) / 2):]]
            y_values = [point[1] for point in points[math.floor(len(points) / 2):]]

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
                if key == 'segments':
                    data[key] = [segment.__getstate__() for segment in value] if value else None
                else:
                    data[key] = value
        return data

    @staticmethod
    def from_json_dict(data: dict) -> 'WingConfiguration':
        """
        Create a WingConfiguration from a JSON dictionary.

        Args:
            data: Dictionary containing the WingConfiguration data.

        Returns:
            A new WingConfiguration instance.
        """
        from cad_designer.airplane.aircraft_topology.wing.Airfoil import Airfoil
        from cad_designer.airplane.aircraft_topology.wing.Spare import Spare
        from cad_designer.airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

        # Get airfoil data from the first segment if available
        first_segment = data.get('segments', [])[0] if data.get('segments') else {}
        root_airfoil_data = first_segment.get('root_airfoil', {}) if first_segment else data.get('root_airfoil', {})
        tip_airfoil_data = first_segment.get('tip_airfoil', {}) if first_segment else data.get('tip_airfoil', {})

        # Get spare list and trailing edge device from first segment if available
        spare_list_data = first_segment.get('spare_list', []) if first_segment else data.get('spare_list', [])
        trailing_edge_device_data = first_segment.get('trailing_edge_device', {}) if first_segment else data.get(
            'trailing_edge_device', {})

        # Get length and sweep from first segment if available
        length = first_segment.get('length', data.get('length', 0)) if first_segment else data.get('length', 0)
        sweep = first_segment.get('sweep', data.get('sweep', 0)) if first_segment else data.get('sweep', 0)

        # Create the base wing configuration
        wing = WingConfiguration(nose_pnt=tuple(data.get('nose_pnt', (0, 0, 0))), root_airfoil=Airfoil.from_json_dict(
            root_airfoil_data) if root_airfoil_data else Airfoil(), length=length, sweep=sweep,
                                 sweep_is_angle=data.get('sweep_is_angle', False), tip_airfoil=Airfoil.from_json_dict(
                tip_airfoil_data) if tip_airfoil_data else Airfoil(),
                                 number_interpolation_points=data.get('number_interpolation_points'),
                                 spare_list=[Spare.from_json_dict(spare) for spare in
                                             spare_list_data] if spare_list_data else None,
                                 trailing_edge_device=TrailingEdgeDevice.from_json_dict(
                                     trailing_edge_device_data) if trailing_edge_device_data else None,
                                 symmetric=data.get('symmetric', True))

        # Restore segments if they exist
        if 'segments' in data:
            from cad_designer.airplane.aircraft_topology.wing.WingSegment import WingSegment
            wing.segments = []
            for segment_data in data['segments']:
                segment = WingSegment.from_json_dict(segment_data)
                wing.segments.append(segment)

        return wing

    @staticmethod
    def from_json(file_path: str) -> 'WingConfiguration':
        """
        Load a WingConfiguration from a JSON file.

        Args:
            file_path: Path to the JSON file.

        Returns:
            A new WingConfiguration instance.
        """
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return WingConfiguration.from_json_dict(data)

    def save_to_json(self, file_path: str) -> None:
        """
        Saves the WingConfiguration to a JSON file.

        Parameters:
            file_path (str): Path to the JSON file.
        """
        import json
        with open(file_path, 'w') as f:
            json.dump(self.__getstate__(), f, indent=4)

    @staticmethod
    def from_asb(xsecs: list[asb.WingXSec], symmetric: bool = True) -> 'WingConfiguration':
        """Create a WingConfiguration from a list of Aerosandbox WingXSecs.

        Decoupled reconstruction: with rc=0 and the decoupled frame
        computation (incidence does not propagate into positions),
        the inverse is trivial arithmetic:

        - The position chain in _get_relative_segment_coordinate_system
          uses only R_x(cumulative_dihedral) to rotate [sweep, length, 0].
        - Therefore delta = R_x(cum_d) . [sweep, length, 0], giving:
          - sweep = delta.x  (R_x does not affect X)
          - length = sqrt(delta.y^2 + delta.z^2)
          - cum_d = atan2(delta.z, delta.y)
          - dihedral_delta = cum_d[k] - cum_d[k-1]
          - incidence_delta = twist[k+1] - twist[k]

        No M-matrix tracking needed. Dihedral is always extractable
        (no twist contamination in positions).

        Args:
            xsecs: List of WingXSec objects.
            symmetric: Whether the wing is symmetric.

        Returns:
            A new WingConfiguration in *relative* mode, with
            dihedral carried as dihedral_as_rotation_in_degrees on every airfoil.
        """
        asb_wing = asb.Wing(xsecs=xsecs, symmetric=symmetric)
        n = len(asb_wing.xsecs)
        if n < 2:
            raise ValueError(
                "WingConfiguration.from_asb requires at least 2 xsecs (one segment)."
            )

        # Per-segment deltas in global frame.
        deltas: list[ndarray] = []
        for i in range(n - 1):
            delta = (
                np.asarray(asb_wing.xsecs[i + 1].xyz_le, dtype=float)
                - np.asarray(asb_wing.xsecs[i].xyz_le, dtype=float)
            )
            deltas.append(delta)

        nose_pnt_arr = np.asarray(asb_wing.xsecs[0].xyz_le, dtype=float)
        nose_pnt = (
            float(nose_pnt_arr[0]),
            float(nose_pnt_arr[1]),
            float(nose_pnt_arr[2]),
        )

        # Per-xsec cumulative twist (absolute, as stored by asb).
        cum_twists: list[float] = [float(asb_wing.xsecs[k].twist) for k in range(n)]

        # Per-xsec cumulative dihedral angle, extracted from deltas.
        # With decoupled frame, delta = R_x(cum_d) . [sweep, length, 0],
        # so cum_d = atan2(delta.z, delta.y). Always extractable
        # because twist does not contaminate positions.
        cum_d: list[float] = [0.0] * n
        for k in range(n - 1):
            delta_y = float(deltas[k][1])
            delta_z = float(deltas[k][2])
            if abs(delta_y) + abs(delta_z) > 1e-12:
                cum_d[k] = math.degrees(math.atan2(delta_z, delta_y))
            else:
                # Zero-length segment: inherit previous dihedral
                cum_d[k] = cum_d[k - 1] if k > 0 else 0.0
        cum_d[n - 1] = cum_d[n - 2]

        # Root airfoil rotations: absolute cumulative at xsec 0.
        root_i = cum_twists[0]
        root_d = cum_d[0]

        def _airfoil_name(xsec: asb.WingXSec) -> str | None:
            af = xsec.airfoil
            return af.name if af is not None else None

        def _make_airfoil_at(
            k: int,
            incidence: float,
            d_rot: float,
        ) -> Airfoil:
            return Airfoil(
                airfoil=_airfoil_name(asb_wing.xsecs[k]),
                chord=float(asb_wing.xsecs[k].chord),
                dihedral_as_rotation_in_degrees=d_rot,
                incidence=incidence,
            )

        # Extract sweep and length from delta directly.
        # delta = R_x(cum_d) . [sweep, length, 0]
        # => sweep = delta.x, length = sqrt(delta.y^2 + delta.z^2)
        def _extract_sweep_length(delta: ndarray, seg_index: int) -> tuple[float, float]:
            sweep = float(delta[0])
            length = float(math.sqrt(delta[1] ** 2 + delta[2] ** 2))
            if length < 1e-9:
                raise ValueError(
                    f"WingConfiguration.from_asb: segment {seg_index} has near-zero "
                    f"span length ({length:.2e}). This produces degenerate geometry."
                )
            return sweep, length

        # Segment 0
        tip_d_0 = cum_d[1] - cum_d[0]
        tip_i_0 = cum_twists[1] - cum_twists[0]
        sweep_0, length_0 = _extract_sweep_length(deltas[0], 0)

        root_airfoil = _make_airfoil_at(k=0, incidence=root_i, d_rot=root_d)
        tip_airfoil = _make_airfoil_at(k=1, incidence=tip_i_0, d_rot=tip_d_0)

        wc = WingConfiguration(
            nose_pnt=nose_pnt,
            root_airfoil=root_airfoil,
            length=length_0,
            sweep=sweep_0,
            sweep_is_angle=False,
            tip_airfoil=tip_airfoil,
            symmetric=symmetric,
            parameters="relative",
            spare_list=None,
        )

        for j in range(1, n - 1):
            tip_d_j = cum_d[j + 1] - cum_d[j]
            tip_i_j = cum_twists[j + 1] - cum_twists[j]
            sweep_j, length_j = _extract_sweep_length(deltas[j], j)

            new_tip_airfoil = _make_airfoil_at(
                k=j + 1,
                incidence=tip_i_j,
                d_rot=tip_d_j,
            )

            wc.add_segment(
                length=length_j,
                sweep=sweep_j,
                sweep_is_angle=False,
                tip_airfoil=new_tip_airfoil,
                spare_list=None,
            )

        return wc
