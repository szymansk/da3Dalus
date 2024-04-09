import logging

import math

import numpy as np

from typing import Union, Literal, Tuple, cast as tcast

from math import cos, asin, degrees, radians

from cadquery import Workplane, Plane, Sketch
from cadquery.occ_impl.shapes import Edge
from cadquery.occ_impl.geom import Vector

from airplane.AbstractShapeCreator import AbstractShapeCreator
from airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration
from airplane.aircraft_topology.wing.WingSegment import WingSegment
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from airplane.creator.wing.ted_sketch_creators import ted_sketch_creators

import cq_plugins

MOUNT_PLATE_THICKNESS = 1.0


class VaseModeWingCreator(AbstractShapeCreator):
    """
    """

    def __init__(self, creator_id: str, wing_index: Union[str, int], printer_wall_thickness: float,
                 leading_edge_offset_factor: float, trailing_edge_offset_factor: float,
                 minimum_rib_angle: float = 45, spare_perpendicular: bool = False,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT", "RIGHT", "BOTH"] = "RIGHT", loglevel: int = logging.INFO):
        """
        returns as shapes:
        creator_id -> the complete wing,
        creator_id.spare -> the spare,
        creator_id.cutout -> the ribs cutout,
        creator_id.slot -> the slot for vase mode,
        creator_id.teds -> the trailing edge devices dict as a dict of "trailing_edge_device.name::segment"

        parameters:
        printer_wall_thickness - printer settings wall thickness
        spare_support_geometry_is_round -- default true
        spare_support_dimension_x -- diameter if round is true
        spare_support_dimension_z -- ignored if round
        leading_edge_offset --
        trailing_edge_offset --
        minimum_rib_angle -- important for printability (should be > 45°)
        """
        self.printer_wall_thickness: float = printer_wall_thickness
        self.spare_perpendicular: bool = spare_perpendicular
        self.leading_edge_offset_factor: float = leading_edge_offset_factor
        self.trailing_edge_offset_factor: float = trailing_edge_offset_factor
        self.minimum_rib_angle: float = minimum_rib_angle
        self.wing_side: Literal["LEFT", "RIGHT", "BOTH"] = wing_side
        self.wing_index: Union[str, int] = wing_index
        self._wing_config: dict[int, WingConfiguration] = wing_config

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"construct vase mode wing from configuration --> '{self.identifier}'")
        wing_config: WingConfiguration = self._wing_config[self.wing_index]

        segment = 0  # root segment
        # create root segment shapes for hull creation
        # those shapes are need to produce a hull and the base for the ribs
        # the shapes are offset by  1 and 2 * printer_wall_thickness
        right_wing, right_wing_2xpwt_offset, right_wing_pwt_offset = self._create_basic_root_segment_shapes(wing_config)

        # create the hull
        # we need to take the last objects from the workplanes, those are the solids.
        right_wing_hull = Workplane(right_wing.vals()[-1].cut(right_wing_2xpwt_offset.vals()[-1]))

        current_pwt_offset: Workplane = right_wing_pwt_offset
        current_2xpwt_offset: Workplane = right_wing_2xpwt_offset
        current: Workplane = right_wing

        # create root segment spare
        right_wing_spare, spare_plane = self._create_spare_shape(current=current_pwt_offset,
                                                                 segment=segment,
                                                                 wing_config=wing_config)

        # create root segment ribs
        right_wing_cutout, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part = (
            self._create_ribs_shape(current=current_pwt_offset, segment=segment, wing_config=wing_config,
                                    leading_edge_start=None, trailing_edge_start=None, start_upper_part=False))

        # create root segment slot
        right_wing_slot = (Workplane(spare_plane)
                           .box(length=0.05 * self.printer_wall_thickness,
                                width=100,
                                height=wing_config.segments[segment].length * 3,
                                centered=(False, False, True))
                           )

        # dictionary for trailing edge devices (teds)
        teds: dict[str, Workplane] = {}
        # cut out trailing edge device (ted) from segment
        if wing_config.segments[segment].trailing_edge_device is not None:
            right_wing_hull, right_wing_cutout, ted_shape = self._create_ted_shapes(current, right_wing_hull,
                                                                                    right_wing_cutout,
                                                                                    segment, wing_config)
            teds[f"{wing_config.segments[segment].trailing_edge_device.name}[{segment}]"] = ted_shape
            pass

        final_right_wing = right_wing_hull.add(right_wing_spare).add(right_wing_cutout).cut(right_wing_slot)

        # create additional spares
        for spare_idx in range(1, len(wing_config.segments[segment].spare_list)):
            spare_shape, _ = self._create_spare_shape(
                current=current_pwt_offset,
                segment=segment,
                wing_config=wing_config,
                spare_idx=spare_idx)
            pass
            final_right_wing = final_right_wing.add(spare_shape)

        # create the other segments
        for segment in range(1, len(wing_config.segments)):
            wing_segment = wing_config.segments[segment]
            # create all wing shapes that are need to produce a hull and the base for the ribs
            # the shapes are offsetted by  1 and 2 * printer_wall_thickness
            current, current_2xpwt_offset, current_pwt_offset = self._create_basic_wing_shapes(current,
                                                                                               current_2xpwt_offset,
                                                                                               current_pwt_offset,
                                                                                               wing_config,
                                                                                               segment)
            # add a wing_tip
            if wing_segment.tip_type is not None and segment == len(wing_config.segments)-1:
                # only do this if it is the last segment in the list
                if wing_segment.tip_type is 'flat':
                    final_right_wing = final_right_wing.add(current)
                elif wing_segment.tip_type is 'round':
                    # TODO: implent a wing tip
                    # using a simple fillet does work in fusion360 but not with cadquery
                    current = current.faces("%PLANE and >Y").wires().toPending().fillet(wing_segment.length*0.95)
                    final_right_wing = final_right_wing.add(current)
            else:
                # make a hull that is 2 * printer_wall_thickness thick
                current_hull = Workplane(current.vals()[-1].cut(current_2xpwt_offset.vals()[-1]))

                # create the base shape of the main spare and the spare's plane
                raw_spare, spare_plane = self._create_spare_shape(current=current_pwt_offset, segment=segment,
                                                                  wing_config=wing_config, spare_idx=0)
                right_wing_spare = right_wing_spare.add(raw_spare)

                # create the cut out for the ribs in an hour glass like shape
                # the cut out is created in a way that the main spare fits into it nicely
                raw_ribs, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part = self._create_ribs_shape(
                    current_pwt_offset, segment, wing_config, leading_edge_start, trailing_edge_start, not lower_part)
                right_wing_cutout.add(raw_ribs)

                # create a shape for the slot that is needed to make the wing printable in vase mode
                # only spare with index 0 will get this slot
                right_wing_slot = (Workplane(spare_plane)
                                   .box(length=0.05 * self.printer_wall_thickness,
                                        width=100,
                                        height=wing_segment.length * 10,
                                        centered=(False, False, True)))

                # create all other spares
                for spare_idx in range(1, len(wing_segment.spare_list)):
                    raw_add_spar, _ = self._create_spare_shape(current=current_pwt_offset, segment=segment,
                                                               wing_config=wing_config, spare_idx=spare_idx)

                # cut out trailing edge device (ted) from segment
                ted = wing_segment.trailing_edge_device
                if ted is not None:
                    if ted.servo is not None:
                        # if we have a servo defined for the ted than we create the mount and an access opening (cover)
                        # TODO: return the ted link plane( with origin and x-direction)
                        current_hull, glue_in_mount = self._create_servo_mount_and_cover(current, current_hull, segment, wing_config,
                                                                          ted.servo_placement)
                    # create the shape of the ted including the hinge
                    # TODO: use the ted link origin and direction to construct a rudder horn with linkage for the ted
                    current_hull, raw_ribs, ted_shape = self._create_ted_shapes(current, current_hull, raw_ribs,
                                                                                segment, wing_config)
                    teds[f"{ted.name}[{segment}]"] = ted_shape
                    pass

                # finally put everything together (however due to the complexity a 'union' does not work
                final_right_wing = final_right_wing.add(
                    current_hull
                    .add(raw_spare)
                    .add(raw_ribs)
                    .cut(right_wing_slot)
                    .combine())

            right_wing_pwt_offset.add(current_pwt_offset)
            pass

        # we combine everything and try to fix the shape
        final_right_wing = final_right_wing.fix_shape().combine()
        right_wing_cutout = right_wing_cutout.combine(glue=True)

        # now we decide if we need the left, right or both wings for the wing
        # for the vertical stabilizer with the rudder we do only need one side
        if self.wing_side == "LEFT":
            right_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_cutout = right_wing_cutout.mirror("XZ")
            final_right_wing = final_right_wing.mirror("XZ")
            for (k, v) in teds.items():
                teds[k] = v.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_spare = right_wing_spare.add(left_wing_spare)

            left_wing_cutout = right_wing_cutout.mirror("XZ")
            right_wing_cutout = right_wing_cutout.union(left_wing_cutout)

            left_right_wing = final_right_wing.mirror("XZ")
            final_right_wing = final_right_wing.add(left_right_wing)

            _teds: dict[str, Workplane] = teds.copy()
            for (k, v) in teds.items():
                _teds[f"{k}*"] = v.mirror("XZ")
            teds = _teds

        right_wing_spare = right_wing_spare.fix_shape()
        right_wing_cutout = right_wing_cutout.fix_shape()
        final_right_wing = final_right_wing.fix_shape().combine()

        # translate all shapes to the final place in the airplane
        # TODO: remove translations from creator... this should be translated, later or by assembly constraints
        right_wing_spare = (right_wing_spare.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}.spare", severity=logging.DEBUG))

        right_wing_cutout = right_wing_cutout.translate(wing_config.nose_pnt).display(name=f"{self.identifier}.cutout",
                                                                                      severity=logging.DEBUG)

        final_right_wing = (final_right_wing.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}", severity=logging.DEBUG))

        for (k, v) in teds.items():
            teds[k] = (v.translate(wing_config.nose_pnt)
                       .display(name=f"{self.identifier}.ted[{k}]", severity=logging.DEBUG))

        final_dict: dict = {self.identifier: final_right_wing,
                            f"{self.identifier}.spare": right_wing_spare,
                            f"{self.identifier}.cutout": right_wing_cutout,
                            f"{self.identifier}.slot": right_wing_slot}

        for (k, v) in teds.items():
            final_dict[f"{self.identifier}.{k}"] = v

        return final_dict

    def _create_servo_mount_and_cover(self, current: Workplane, current_hull: Workplane, segment: int,
                                      wing_config: WingConfiguration, placement: Literal['top', 'bottom'] = 'top',
                                      rim_size:float=2.5) -> tuple[Workplane, Workplane]:
        ted = wing_config.segments[segment].trailing_edge_device
        servo = ted.servo

        wing_plane = wing_config.get_wing_workplane(segment=segment).plane

        servo_mount = servo.create_laying_mount_for_wing()
        cover = servo.create_servo_cover_for_wing(self.printer_wall_thickness, rim_size, in_plane= None)
        cover_small = servo.create_servo_cover_for_wing(self.printer_wall_thickness, 0., in_plane= None)

        servo_origin_top, servo_origin_bottom = wing_config.get_points_on_surface(segment=segment,
                                                                                  relative_chord=ted.rel_chord_servo_position,
                                                                                  relative_length=ted.rel_length_servo_position)

        bottom_max, top_min = self.calculate_lowest_point_for_mount(segment, ted, wing_config, wing_plane)

        if placement == 'bottom':
            servo_orientation_deg = 0
            sob = wing_plane.toLocalCoords(servo_origin_top)
            so = wing_plane.toLocalCoords(servo_origin_bottom)
            direction = -1.
            selector = "<Z"
            correction = bottom_max + 2*MOUNT_PLATE_THICKNESS
        else:
            servo_orientation_deg = 180  # 0 - lays on the bottom / 180 - hangs from the top
            so = wing_plane.toLocalCoords(servo_origin_top)
            sob = wing_plane.toLocalCoords(servo_origin_bottom)
            direction = 1.
            selector = ">Z"
            correction = top_min - 2*MOUNT_PLATE_THICKNESS # we need to compensate a not so good rotation

        trans_mount = wing_plane.xDir * so.x + wing_plane.yDir * so.y + wing_plane.zDir * correction
        trans_cover = wing_plane.xDir * (sob.x + rim_size) + wing_plane.yDir * sob.y + wing_plane.zDir * sob.z

        mirror_and_rotate = lambda wp: (Workplane(wp.findSolid().mirror(mirrorPlane="YZ")
                                     .rotate((0, 0, 0), (0, 1, 0), servo_orientation_deg)
                                     .rotate((0, 0, 0), (0, 0, 1), 180 - servo_orientation_deg)
                                     .located(wing_plane.location)))

        servo_mount = mirror_and_rotate(servo_mount)
        cover = mirror_and_rotate(cover)
        cover_small = mirror_and_rotate(cover_small)

        servo_mount = servo_mount.translate(trans_mount)
        servo_mount = servo_mount.intersect(current)
        updated_hull = current_hull.union(servo_mount)

        cover = cover.translate(trans_cover)
        cover = cover.intersect(current_hull)

        cover_small = cover_small.translate(trans_cover)
        cover_small = cover_small.intersect(current_hull)

        cover_top = cover.translate(wing_plane.zDir * 1.9 * self.printer_wall_thickness)
        cover_bottom = cover.translate(wing_plane.zDir * (-1.9 * self.printer_wall_thickness))

        cover = cover.union(toUnion=cover_top, clean=True, glue=True).union(toUnion=cover_bottom, clean=True, glue=True)
        cover = cover.faces("%BSPLINE").chamfer(2 * self.printer_wall_thickness)

        cover_small = (cover_small.translate(wing_plane.zDir * (direction * 3.5 * self.printer_wall_thickness))
                       .faces("%BSPLINE").faces(selector).chamfer(1.99 * self.printer_wall_thickness))
        cover = cover.union(toUnion=cover_small, clean=True, glue=True)
        updated_hull = updated_hull.union(toUnion=cover, clean=True, glue=True)

        #cover.display("cover", 500)
        #current_hull.display("hull", 500)
        #updated_hull.display("hull", 500)
        #servo_mount.display("servo_mount", 500)

        # box=Workplane().box(3,1,12, centered=False)
        # box = (Workplane(box.findSolid().mirror(mirrorPlane="YZ")
        #                   .rotate((0, 0, 0), (0, 1, 0), servo_orientation_deg).located(plane.location)))
        # trans = plane.xDir * so.x + plane.yDir * so.y + plane.zDir * (so.z - (so.z - sob.z) * 0.15)
        # box = box.translate(trans).display("box",24234)

        return updated_hull, servo.create_laying_glue_in_mount(base_thickness=MOUNT_PLATE_THICKNESS)

    def calculate_lowest_point_for_mount(self, segment, ted, wing_config, wing_plane):
        x_offset_interval = np.linspace(-(ted.servo.leading_length + ted.servo.latch_length),
                                        ted.servo.trailing_length + ted.servo.latch_length,
                                        10)
        y_offset_interval = np.linspace(-ted.servo.height, 0.0, 3)

        top_min = math.inf
        bottom_max = -math.inf
        for y_off in y_offset_interval:
            for x_off in x_offset_interval:
                top_wc, bottom_wc = wing_config.get_points_on_surface(segment=segment,
                                                                      relative_chord=ted.rel_chord_servo_position,
                                                                      relative_length=ted.rel_length_servo_position,
                                                                      x_offset=x_off,
                                                                      z_offset=y_off,
                                                                      coordinate_system='world')
                top_lc = wing_plane.toLocalCoords(top_wc)
                bottom_lc = wing_plane.toLocalCoords(bottom_wc)
                if top_min > top_lc.z:
                    top_min = top_lc.z
                if bottom_max < bottom_lc.z:
                    bottom_max = bottom_lc.z
                pass

        return bottom_max, top_min

    def _create_ted_shapes(self, current: Workplane, current_hull: Workplane, raw_ribs: Workplane,
                           segment: int, wing_config: WingConfiguration) -> Tuple[Workplane, Workplane, Workplane]:
        wcs: WingSegment = wing_config.segments[segment]
        ted: TrailingEdgeDevice = wing_config.segments[segment].trailing_edge_device
        ted_root_plane, ted_tip_plane = wing_config.get_trailing_edge_device_planes(segment)

        # make the intersect and cut shape and create the ted
        ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip = (
            ted_sketch_creators[ted.suspension_type](ted=ted, wing_config=wing_config, segment=segment))

        # intersect it with the wing
        ted_intersect = (Workplane()
                         .placeSketch(ted_sketch.moved(ted_root_plane.location),
                                      ted_sketch_tip.moved(ted_tip_plane.location)).loft())
        ted_shape = current.intersect(ted_intersect)

        if ted.side_spacing > 0:
            ted_shape = ted_shape.cut(
                Workplane(inPlane=ted_root_plane).box(wcs.root_chord * 4, wcs.root_chord * 4, ted.side_spacing,
                                                      centered=(True, True, False)))
            length = (ted_tip_plane.origin - ted_root_plane.origin)

            ted_shape = ted_shape.cut(
                Workplane(inPlane=ted_root_plane).workplane(offset=length.y - ted.side_spacing).box(wcs.root_chord * 4,
                                                                                                    wcs.root_chord * 4,
                                                                                                    wcs.root_chord * 4,
                                                                                                    centered=(
                                                                                                    True, True,
                                                                                                    False)))

        # cut it from the wing
        wing_cutout = (Workplane()
                       .placeSketch(wing_sketch.moved(ted_root_plane.location),
                                    wing_sketch_tip.moved(ted_tip_plane.location)).loft())


        #current_hull.display("current_hull", 500)

        current_hull = current_hull.cut(wing_cutout)
        raw_ribs = raw_ribs.cut(wing_cutout)

        #ted_intersect.display("ted_intersect", 500)
        #wing_cutout.display("cutout", 500)
        #ted_shape.display("ted_shape", 500)
        #raw_ribs.display("raw_ribs", 500)

        return current_hull, raw_ribs, ted_shape

    def _create_basic_root_segment_shapes(self, wing_config: WingConfiguration):
        segment: int = 0
        root_plane = wing_config.get_wing_workplane(segment).plane.rotated((90,0,0))
        tip_plane = wing_config.get_wing_workplane(segment+1).plane.rotated((90,0,0))
        right_wing_pwt_offset: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[segment].root_airfoil,
                root_chord=wing_config.segments[segment].root_chord,
                root_dihedral=wing_config.segments[segment].root_dihedral,
                root_incidence=wing_config.segments[segment].root_incidence,
                length=wing_config.segments[segment].length,
                sweep=wing_config.segments[segment].sweep,
                tip_chord=wing_config.segments[segment].tip_chord,
                tip_dihedral=wing_config.segments[segment].tip_dihedral,
                tip_incidence=wing_config.segments[segment].tip_incidence,
                tip_airfoil=wing_config.segments[segment].tip_airfoil,
                offset=self.printer_wall_thickness,
                number_interpolation_points=wing_config.segments[0].number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane
            ))

        right_wing_2xpwt_offset: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[segment].root_airfoil,
                root_chord=wing_config.segments[segment].root_chord,
                root_dihedral=wing_config.segments[segment].root_dihedral,
                root_incidence=wing_config.segments[segment].root_incidence,
                length=wing_config.segments[segment].length,
                sweep=wing_config.segments[segment].sweep,
                tip_chord=wing_config.segments[segment].tip_chord,
                tip_dihedral=wing_config.segments[segment].tip_dihedral,
                tip_incidence=wing_config.segments[segment].tip_incidence,
                tip_airfoil=wing_config.segments[segment].tip_airfoil,
                offset=2.0 * self.printer_wall_thickness,
                number_interpolation_points=wing_config.segments[0].number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane
            ))
        right_wing: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[segment].root_airfoil,
                root_chord=wing_config.segments[segment].root_chord,
                root_dihedral=wing_config.segments[segment].root_dihedral,
                root_incidence=wing_config.segments[segment].root_incidence,
                length=wing_config.segments[segment].length,
                sweep=wing_config.segments[segment].sweep,
                tip_chord=wing_config.segments[segment].tip_chord,
                tip_dihedral=wing_config.segments[segment].tip_dihedral,
                tip_incidence=wing_config.segments[segment].tip_incidence,
                tip_airfoil=wing_config.segments[segment].tip_airfoil,
                offset=0.0,
                number_interpolation_points=wing_config.segments[0].number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane
            ))
        return right_wing, right_wing_2xpwt_offset, right_wing_pwt_offset

    def _create_basic_wing_shapes(self, _current: Workplane,
                                  _current_2xpwt_offset: Workplane,
                                  _current_pwt_offset: Workplane,
                                  wing_config:WingConfiguration,
                                  segment: int):
        segment_config = wing_config.segments[segment]
        root_plane = wing_config.get_wing_workplane(segment).plane.rotated((90,0,0))
        tip_plane = wing_config.get_wing_workplane(segment+1).plane.rotated((90,0,0))

        current_pwt_offset = _current_pwt_offset.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=self.printer_wall_thickness,
            number_interpolation_points=segment_config.number_interpolation_points,
            root_plane=root_plane,
            tip_plane=tip_plane
        )
        current_2xpwt_offset = _current_2xpwt_offset.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=2.0 * self.printer_wall_thickness,
            number_interpolation_points=segment_config.number_interpolation_points,
            root_plane=root_plane,
            tip_plane=tip_plane)
        current = _current.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=0.0,
            number_interpolation_points=segment_config.number_interpolation_points,
            root_plane=root_plane,
            tip_plane=tip_plane)
        return current, current_2xpwt_offset, current_pwt_offset

    def _create_spare_shape(self, current: Workplane, segment: int, wing_config: WingConfiguration,
                            spare_idx: int = 0) -> Tuple[Workplane, Plane]:
        spare = wing_config.segments[segment].spare_list[spare_idx]

        # create spare sketch
        spare_sketch = VaseModeWingCreator._construct_spare_sketch(printer_wall_thickness=self.printer_wall_thickness,
                                                                   spare_support_dimension_width=spare.spare_support_dimension_width,
                                                                   spare_support_dimension_height=spare.spare_support_dimension_height)

        # the spare vector defines a vector the spare should follow (normal of the spare_plane)
        # the spare vector can be changed for segments or can be the same
        wing_wp = wing_config.get_wing_workplane(segment)
        spare_plane = Plane(origin=spare.spare_origin,
                            xDir=wing_wp.plane.xDir,
                            normal=spare.spare_vector.normalized())

        extrude_length = wing_config.segments[segment].length * 10 if spare.spare_length is None else spare.spare_length
        # extrude and intersect
        both_directions: bool = False if spare.spare_start != 0. else True
        raw_spare = (Workplane(inPlane=spare_plane)
                     .workplane(offset=spare.spare_start)
                     .placeSketch(spare_sketch)
                     .extrude(extrude_length, both=both_directions)
                     .intersect(toIntersect=current))
        return raw_spare, spare_plane

    def _create_ribs_shape(self, current, segment, wing_config, leading_edge_start, trailing_edge_start,
                           start_upper_part, spare_idx: int = 0):
        ted = wing_config.segments[segment].trailing_edge_device
        spare_position_factor = wing_config.segments[segment].spare_list[0].spare_position_factor
        root_chord = wing_config.segments[segment].root_chord
        teof = 0.0
        if ted is not None:
            teof = (max((root_chord * (1 - ted.rel_chord_root)),
                        ((wing_config.segments[segment].tip_chord + wing_config.segments[segment].sweep) *
                         (1 - ted.rel_chord_tip)))
                    * ted.trailing_edge_offset_factor)

        trailing_edge_offset = self.trailing_edge_offset_factor * root_chord \
            if teof < self.trailing_edge_offset_factor * root_chord else teof

        cutout_face, leading_edge_start, trailing_edge_start, lower_part, spare_vector_origin = (
            VaseModeWingCreator._rib_cutout(segment=segment, wing_config=wing_config,
                                            printer_wall_thickness=self.printer_wall_thickness,
                                            leading_edge_offset=self.leading_edge_offset_factor * root_chord,
                                            trailing_edge_offset=trailing_edge_offset,
                                            leading_edge_start=leading_edge_start,
                                            trailing_edge_start=trailing_edge_start, start_upper_part=start_upper_part,
                                            minimum_rib_angle=self.minimum_rib_angle, spare_idx=spare_idx))
        cutout_face.assemble()
        try:
            raw_ribs = (
                wing_config.get_wing_workplane(segment=segment)
                .placeSketch(cutout_face)
                .add(current)
                .cutThruAll()
            )
        except:
            logging.warning(f"could not create segment: {segment}!")
        pass
        return raw_ribs, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part

    @staticmethod
    def _rib_cutout(segment: int, wing_config: WingConfiguration, printer_wall_thickness: float,
                    leading_edge_offset: float, trailing_edge_offset: float, leading_edge_start: float = None,
                    trailing_edge_start: float = None, start_upper_part: bool = False, minimum_rib_angle: float = 45,
                    spare_idx: int = 0) -> Tuple[Sketch, float, float, bool, Vector]:
        """
        Constructs a set of hourglass like structures in between the nose and the tail part of the wing.

        TODO: Implement a zigzag pattern for the rib segments, to improve stability.
        """

        (root_nose_offset, root_nose_start, root_tail_offset, root_tail_start, spare_nose_root,
         spare_nose_tip, spare_tail_root, spare_tail_tip, tip_nose, tip_nose_offset, tip_tail_offset,
         spare_vector_origin) = (
            VaseModeWingCreator._calculate_wing_construction_points(segment, printer_wall_thickness,
                                                                    leading_edge_offset, leading_edge_start,
                                                                    trailing_edge_offset, trailing_edge_start,
                                                                    wing_config, spare_idx=spare_idx)
        )

        # Drawing the offset outlines in the sketch.
        const_lines: Sketch = (
            Sketch()
            .segment(Vector(tuple(root_nose_offset)),
                     Vector(tuple(tip_nose_offset)), 'nose_os', forConstruction=True)
            .segment(Vector(tuple(root_tail_offset)),
                     Vector(tuple(tip_tail_offset)), 'tail_os', forConstruction=True)
            .segment(Vector(tuple(spare_tail_root)),
                     Vector(tuple(spare_tail_tip)), 'spare_tail', forConstruction=True)
            .segment(Vector(tuple(spare_nose_root)),
                     Vector(tuple(spare_nose_tip)), 'spare_nose', forConstruction=True)
        )

        # Constructing the first row of ribs...
        if not start_upper_part:
            const_lines = (
                const_lines
                .segmentToEdge(Vector(tuple(root_tail_start)),
                               180. - minimum_rib_angle, 'spare_tail', 'rib_tl')  # rib: tail left  \
                .segmentToEdge(minimum_rib_angle, 'tail_os', 'rib_tr')  # rib: tail right /
                .segmentToEdge(180., 'nose_os', 'help_top', forConstruction=False)
                .segmentToEdge('rib_tl', 180., 'spare_nose', 'help_middle', forConstruction=False)
                .segment(Vector(tuple(root_nose_start)), 'rib_nl')  # rib: nose left  /
                .segmentToEdge('help_middle', 1, 'help_top', 1., 'rib_nr')  # rib: nose right \
                .segment(Vector(tuple(root_tail_start)), Vector(tuple(root_tail_start))
                         - Vector((0, wing_config.segments[segment].length * 0.1, 0)), 'nose_ext')
                .segment(Vector(tuple(root_nose_start)), Vector(tuple(root_nose_start))
                         - Vector((0, wing_config.segments[segment].length * 0.1, 0)), 'tail_ext')
                .segmentToEdge('nose_ext', 1., 'tail_ext', 1., 'root')
            )
        else:
            const_lines = (
                const_lines
                .segmentToEdge(Vector(tuple(root_tail_start)), minimum_rib_angle, 'tail_os',
                               'rib_tr')  # rib: tail right (upper) /
                .segmentToEdge(180., 'nose_os', 'help_top', forConstruction=False)
                .segmentToEdge('help_top', 1., Vector(tuple(root_nose_start)), 'rib_nr')  # rib: nose right (upper) \
                .segment(Vector(tuple(root_tail_start)), Vector(tuple(root_tail_start))
                         - Vector((0, wing_config.segments[segment].length * 0.1, 0)), 'nose_ext')
                .segment(Vector(tuple(root_nose_start)), Vector(tuple(root_nose_start))
                         - Vector((0, wing_config.segments[segment].length * 0.1, 0)), 'tail_ext')
                .segmentToEdge('nose_ext', 1., 'tail_ext', 1., 'root')
            )

        # health check
        # 'rib_nr' should not end left of 'rib_tr'
        if (tcast(Edge, const_lines._tags['rib_nr'][0]).endPoint().x >
                tcast(Edge, const_lines._tags['rib_tr'][0]).endPoint().x):
            start_p = tcast(Edge, const_lines._tags['rib_nr'][0]).startPoint()
            const_lines = (
                const_lines
                .select('rib_nr').delete()
                .segmentToEdge(start_p, 180 - minimum_rib_angle, 'nose_os', 'rib_nr')  # rib: nose right (upper) \
                .select('help_top').delete()
                .segmentToEdge('rib_tr', 1., 'rib_nr', 1., 'help_top')  # rib: nose right (upper) \
            )

        # Constructing as many ribs as do fit in the wing.
        id_s = ''
        while (tcast(Edge, const_lines._tags['help_top' + id_s][0]).startPoint().y
               < wing_config.segments[segment].length):
            const_lines = (
                const_lines
                .segmentToEdge('rib_tr' + id_s, 180 - minimum_rib_angle, 'spare_tail', 'rib_tl_' + id_s)
                .segmentToEdge(minimum_rib_angle, 'tail_os', 'rib_tr_' + id_s)
                .segmentToEdge(180, 'nose_os', 'help_top_' + id_s, forConstruction=False)
                .segmentToEdge('rib_tl_' + id_s, 180, 'spare_nose', 'help_middle_' + id_s, forConstruction=False)
                .segmentToEdge('help_top' + id_s, 1, 'help_middle_' + id_s, 1, 'rib_nl_' + id_s)
                .segmentToEdge('help_middle_' + id_s, 1, 'help_top_' + id_s, 1., 'rib_nr_' + id_s)
                .select('help_top' + id_s).delete()
            )
            try:
                # if not start_upper_part:
                const_lines.select('help_middle' + id_s).delete()
            except Exception:
                pass

            # health check
            # 'rib_nr' should not end left of 'rib_tr'
            if (tcast(Edge, const_lines._tags['rib_nr_' + id_s][0]).endPoint().x >
                    tcast(Edge, const_lines._tags['rib_tr_' + id_s][0]).endPoint().x):
                start_p = tcast(Edge, const_lines._tags['rib_nr' + id_s][0]).startPoint()
                const_lines = (
                    const_lines
                    .select('rib_nr_' + id_s).delete()
                    .segmentToEdge(start_p, 180 - minimum_rib_angle, 'nose_os',
                                   'rib_nr_' + id_s)  # rib: nose right (upper) \
                    .select('help_top').delete()
                    .segmentToEdge('rib_tr', 1., 'rib_nr', 1., 'help_top')  # rib: nose right (upper) \
                )
            id_s = id_s + '_'

        # Removing all constrution lines...
        # if not start_upper_part:
        try:
            const_lines.select('help_middle' + id_s).delete()
        except Exception:
            pass

        leading_edge_start, trailing_edge_start, lower_part = (
            VaseModeWingCreator._calc_edge_start(const_lines, id_s, spare_nose_tip, tip_nose))

        const_lines.select('nose_os').delete()
        const_lines.select('spare_nose').delete()
        const_lines.select('spare_tail').delete()
        const_lines.select('tail_os').delete()

        return const_lines, leading_edge_start, trailing_edge_start, lower_part, spare_vector_origin

    @staticmethod
    def _calc_edge_start(sketch: Sketch, id_s: str, spare_nose_tip, tip_nose) -> Tuple[float, float, bool]:
        """
        Constructs the start points leading_edge_start, trailing_edge_start for the next segment, and if it
        starts in the lower or upper part of the hour glas shape.
        """
        try:
            # The construction uses the spare_nose_tip and tip_nose points and draws a horizontal line to intersect with
            # the rib_nl (nose left) and rib_tl (tip left) lines.
            p_le = sketch.segmentToEdge('spare_nose', 180, 'rib_nl' + id_s, 'helper')._tags['helper'][0].endPoint()
            sketch.select('helper').delete()
            p_te = sketch.segmentToEdge('spare_tail', 180, 'rib_tl' + id_s, 'helper')._tags['helper'][0].endPoint()
            sketch.select('helper').delete()
            lower_part = True
            if ((spare_nose_tip[0] - p_le.x) > 0 and abs(p_le.y - tip_nose[1]) < tip_nose[1] * 0.1):
                pass
            else:
                p_le = sketch.segmentToEdge('spare_nose', 180, 'rib_nr' + id_s, 'helper')._tags['helper'][0].endPoint()
                sketch.select('helper').delete()
                p_te = sketch.segmentToEdge('spare_tail', 180, 'rib_tr' + id_s, 'helper')._tags['helper'][0].endPoint()
                sketch.select('helper').delete()
                lower_part = False
        except:
            p_le = sketch.segmentToEdge('spare_nose', 180, 'rib_nr' + id_s, 'helper')._tags['helper'][0].endPoint()
            sketch.select('helper').delete()
            p_te = sketch.segmentToEdge('spare_tail', 180, 'rib_tr' + id_s, 'helper')._tags['helper'][0].endPoint()
            sketch.select('helper').delete()
            lower_part = False

        leading_edge_start = p_le.x - tip_nose[0]
        trailing_edge_start = p_te.x - tip_nose[0]
        return (leading_edge_start, trailing_edge_start, lower_part)

    @staticmethod
    def _calculate_wing_construction_points(segment: int, printer_wall_thickness: float, leading_edge_offset: float,
                                            leading_edge_start: float, trailing_edge_offset: float,
                                            trailing_edge_start: float, wing_config: WingConfiguration,
                                            spare_idx: int = 0):
        spare_vector = wing_config.segments[segment].spare_list[spare_idx].spare_vector
        spare_vector_origin = wing_config.segments[segment].spare_list[spare_idx].spare_origin
        spare_position_factor = wing_config.segments[segment].spare_list[spare_idx].spare_position_factor
        spare_support_dimension_width = wing_config.segments[segment].spare_list[
            spare_idx].spare_support_dimension_width

        spare_vector_origin.y = 0

        if leading_edge_start is None:
            leading_edge_start = leading_edge_offset
        if trailing_edge_start is None:
            trailing_edge_start = wing_config.segments[segment].root_chord - trailing_edge_offset

        # calculating the leading edge guides from root to tip
        root_nose = np.asarray((.0, .0, .0))
        root_nose_offset = root_nose + np.asarray((leading_edge_offset, .0, .0))
        tip_nose = np.asarray((wing_config.segments[segment].sweep, wing_config.segments[segment].length, 0.))
        tip_nose_offset = tip_nose + np.asarray((leading_edge_offset, .0, .0))

        # calculating the trailing edge guides from root to tip
        root_tail = np.asarray((wing_config.segments[segment].root_chord, .0, .0))
        root_tail_offset = root_tail - np.asarray((trailing_edge_offset, .0, .0))
        tip_tail = tip_nose + np.asarray((wing_config.segments[segment].tip_chord, .0, .0))
        tip_tail_offset = tip_tail - np.asarray((trailing_edge_offset, .0, .0))

        # calculating the rib start points
        root_nose_start = np.asarray((leading_edge_start, .0, .0))
        root_tail_start = np.asarray((trailing_edge_start, .0, .0))

        spare_support_width = 0.5 * spare_support_dimension_width + 2 * printer_wall_thickness

        # Calculating the spare nose and tail positions from root to tip
        spare_nose_root = (np.asarray(spare_vector_origin.toTuple())
                           - np.asarray((spare_support_width, 0., 0.)))
        spare_tail_root = (np.asarray(spare_vector_origin.toTuple())
                           + np.asarray((spare_support_width, 0., 0.)))
        if segment > 0:
            # origin is in global coordinates, but the sketch starts with the nose point as (0,0,0)
            # so we need to shift along x by the sweep
            sweep_sum = sum([ws.sweep for ws in wing_config.segments[0:segment]])
            spare_nose_root = spare_nose_root - np.asarray((sweep_sum, 0., 0.))
            spare_tail_root = spare_tail_root - np.asarray((sweep_sum, 0., 0.))

        # we have to remove the z part, because we would loose some length to the z part,
        # which leads to an ugly offset in the segments
        vec = np.asarray((spare_vector.x, spare_vector.y, 0.0))
        norm_vec = vec / np.linalg.norm(vec)
        spare_nose_tip = spare_nose_root + norm_vec * wing_config.segments[segment].length
        spare_tail_tip = spare_tail_root + norm_vec * wing_config.segments[segment].length
        _spare_vector_origin = (spare_vector_origin
                                + Vector(tuple(norm_vec * wing_config.segments[segment].length))
                                - Vector((wing_config.segments[segment].sweep, 0., 0.))
                                )
        _spare_vector_origin.y = 0

        return (root_nose_offset, root_nose_start,
                root_tail_offset, root_tail_start,
                spare_nose_root, spare_nose_tip,
                spare_tail_root, spare_tail_tip,
                tip_nose, tip_nose_offset,
                tip_tail_offset, _spare_vector_origin)

    @staticmethod
    def _construct_spare_sketch(printer_wall_thickness: float, spare_support_dimension_width: float,
                                spare_support_dimension_height: float) -> Sketch:
        """
        Construct a sketch that is extruded to form a spare.

        For the vase mode it is important to leave gaps as the top part of the spare is connected to the
        upper hull of the wing and the bottom part to the bottom hull.
        """
        gap_height = 0.05 * printer_wall_thickness

        beta = degrees(asin((gap_height / 2.0) / (0.5 * spare_support_dimension_width)))
        x = cos(radians(beta)) * (0.5 * spare_support_dimension_width)

        # the width of the spare next to the support beam
        spare_support_width = 0.5 * spare_support_dimension_width + 2 * printer_wall_thickness

        hight = 100
        if spare_support_dimension_height == spare_support_dimension_width:
            const_lines = (
                Sketch()
                .segment((-spare_support_width, gap_height / 2.0),
                         (-spare_support_width, hight), 'left_t')
                .segment((spare_support_width, gap_height / 2.0),
                         (spare_support_width, hight), 'right_t')
                .segment((-spare_support_width, hight),
                         (spare_support_width, hight), 'top')
                .segment((x, gap_height / 2.0),
                         (spare_support_width, gap_height / 2.0))
                .segment((-x, gap_height / 2.0),
                         (-(spare_support_width), gap_height / 2.0))
                .arc((0.0, 0.0), 0.5 * spare_support_dimension_width, beta, 180. - (2. * beta), 'spare_t')
                .assemble()
                .segment((-spare_support_width, -gap_height / 2.0),
                         (-spare_support_width, -hight), 'left_b')
                .segment((spare_support_width, -gap_height / 2.0),
                         (spare_support_width, -hight), 'right_b')
                .segment((-spare_support_width, -hight),
                         (spare_support_width, -hight), 'bottom')
                .segment((x, -gap_height / 2.0),
                         (spare_support_width, -gap_height / 2.0))
                .segment((-x, -gap_height / 2.0),
                         (-(spare_support_width), -gap_height / 2.0))
                .arc((0.0, 0.0), 0.5 * spare_support_dimension_width, -beta, -(180. - (2. * beta)), 'spare_b')
                .assemble()
            )
        else:
            const_lines = (
                Sketch()
                .segment((-spare_support_width, gap_height / 2.0),
                         (-spare_support_width, hight), 'left_t')
                .segment((spare_support_width, gap_height / 2.0),
                         (spare_support_width, hight), 'right_t')
                .segment((-spare_support_width, hight),
                         (spare_support_width, hight), 'top')
                .segment((x, gap_height / 2.0),
                         (spare_support_width, gap_height / 2.0))

                .segment((x, gap_height / 2.0),
                         (x, spare_support_dimension_height / 2.0 - (gap_height / 2.0)))
                .segment((x, spare_support_dimension_height / 2.0 - (gap_height / 2.0)),
                         (-x, spare_support_dimension_height / 2.0 - (gap_height / 2.0)))
                .segment((-x, spare_support_dimension_height / 2.0 - (gap_height / 2.0)),
                         (-x, gap_height / 2.0))

                .segment((-x, gap_height / 2.0),
                         (-(spare_support_width), gap_height / 2.0))
                .assemble()
                .segment((-spare_support_width, -gap_height / 2.0),
                         (-spare_support_width, -hight), 'left_b')
                .segment((spare_support_width, -gap_height / 2.0),
                         (spare_support_width, -hight), 'right_b')
                .segment((-spare_support_width, -hight),
                         (spare_support_width, -hight), 'bottom')
                .segment((x, -gap_height / 2.0),
                         (spare_support_width, -gap_height / 2.0))

                .segment((x, - gap_height / 2.0),
                         (x, -(spare_support_dimension_height / 2.0 - (gap_height / 2.0))))
                .segment((x, -(spare_support_dimension_height / 2.0 - (gap_height / 2.0))),
                         (-x, -(spare_support_dimension_height / 2.0 - (gap_height / 2.0))))
                .segment((-x, -(spare_support_dimension_height / 2.0 - (gap_height / 2.0))),
                         (-x, -(gap_height / 2.0)))

                .segment((-x, -gap_height / 2.0),
                         (-(spare_support_width), -gap_height / 2.0))
                .assemble()
            )

        return const_lines
