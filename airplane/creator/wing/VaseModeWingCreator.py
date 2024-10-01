import logging

import math

import numpy as np

from typing import Union, Literal, Tuple, cast as tcast, Optional, Annotated
from pydantic import Field, NonNegativeInt

from math import cos, asin, degrees, radians

from cadquery import Workplane, Plane, Sketch
from cadquery.occ_impl.shapes import Edge
from cadquery.occ_impl.geom import Vector
from pydantic.v1 import NonNegativeFloat

from airplane.AbstractShapeCreator import AbstractShapeCreator
from airplane.aircraft_topology.components import ServoInformation
from airplane.aircraft_topology.printer3d import Printer3dSettings
from airplane.aircraft_topology.wing.WingConfiguration import WingConfiguration
from airplane.aircraft_topology.wing.WingSegment import WingSegment
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice
from airplane.creator.wing.ted_sketch_creators import ted_sketch_creators

from airplane.types import Factor, WingSides

import cq_plugins

MOUNT_PLATE_THICKNESS = 1.0

class VaseModeWingCreator(AbstractShapeCreator):
    """
    """

    def __init__(self,
                 creator_id: str,
                 wing_index: Union[str, NonNegativeInt],
                 leading_edge_offset_factor: Factor,
                 trailing_edge_offset_factor: Factor,
                 minimum_rib_angle: Annotated[float, Field(ge=45.0, default=45)] = 45,
                 wing_config: Optional[dict[NonNegativeInt, WingConfiguration]] = None,
                 printer_settings: Optional[Printer3dSettings] = None,
                 servo_information: Optional[dict[NonNegativeInt, ServoInformation]] = None,
                 wing_side: WingSides = "RIGHT",
                 loglevel: int = logging.INFO):
        """
        returns as shapes:
        creator_id -> the complete wing,
        creator_id.spare -> the spare,
        creator_id.cutout -> the ribs cutout,
        creator_id.slot -> the slot for vase mode,
        creator_id.teds -> the trailing edge devices dict as a dict of "trailing_edge_device.name::segment"

        parameters:
        printer_wall_thickness - printer settings wall thickness
        minimum_rib_angle -- important for printability (should be > 45°)
        """
        self.leading_edge_offset_factor: float = leading_edge_offset_factor
        self.trailing_edge_offset_factor: float = trailing_edge_offset_factor
        self.minimum_rib_angle: float = minimum_rib_angle
        self.wing_side: Literal["LEFT", "RIGHT", "BOTH"] = wing_side
        self.wing_index: Union[str, int] = wing_index
        self._wing_config: dict[int, WingConfiguration] = wing_config
        self._printer_settings: Printer3dSettings = printer_settings
        self._servo_information: dict[int, ServoInformation] = servo_information

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"construct vase mode wing from configuration --> '{self.identifier}'")
        wing_config: WingConfiguration = self._wing_config[self.wing_index]
        if self._printer_settings is not None:
            self.printer_wall_thickness = self._printer_settings.wall_thickness
            self.gap_rel_printer_wall_thickness = self._printer_settings.rel_gap_wall_thickness

        final_right_segments: list[Workplane|None] = [None for _ in wing_config.segments]
        segment = 0  # root segment
        # create root segment shapes for hull creation
        # those shapes are need to produce a hull and the base for the ribs
        # the shapes are offset by  1 and 2 * printer_wall_thickness
        logging.info(f"==> creating offset wing shapes for '{self.identifier}[{segment}]'")
        right_wing, right_wing_2xpwt_offset, right_wing_pwt_offset = self._create_basic_root_segment_shapes(wing_config)

        # create the hull
        # we need to take the last objects from the workplanes, those are the solids.
        logging.info(f"==> creating wing hull for '{self.identifier}[{segment}]'")
        right_wing_hull = Workplane(right_wing.vals()[-1].cut(right_wing_2xpwt_offset.vals()[-1]))

        current_pwt_offset: Workplane = right_wing_pwt_offset
        current_2xpwt_offset: Workplane = right_wing_2xpwt_offset
        current: Workplane = right_wing

        # create root segment spare
        logging.info(f"==> creating main spare shape for '{self.identifier}[{segment}]'")
        right_wing_spare, spare_plane = self._create_spare_shape(current=current_2xpwt_offset,
                                                                 segment=segment,
                                                                 wing_config=wing_config)

        # create additional spares
        for spare_idx in range(1, len(wing_config.segments[segment].spare_list)):
            logging.info(f"==> creating spare '{spare_idx}' shapes for '{self.identifier}[{segment}]'")
            spare_shape, _ = self._create_spare_shape(
                current=current_pwt_offset,
                segment=segment,
                wing_config=wing_config,
                spare_idx=spare_idx)
            pass
            right_wing_spare = right_wing_spare.add(spare_shape)

        # create root segment ribs
        logging.info(f"==> creating rib shapes for '{self.identifier}[{segment}]'")
        right_wing_cutout, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part = (
            self._create_ribs_shape(current=current_pwt_offset, segment=segment, wing_config=wing_config,
                                    leading_edge_start=None, trailing_edge_start=None, start_upper_part=False))

        # create root segment slot
        logging.info(f"==> creating rib slot for '{self.identifier}[{segment}]'")
        right_wing_slot = (Workplane(spare_plane)
                           .box(length=self.gap_rel_printer_wall_thickness * self.printer_wall_thickness,
                                width=100,
                                height=wing_config.segments[segment].length * 3,
                                centered=(False, False, True))
                           )

        # dictionary for trailing edge devices (teds)
        teds: dict[str, Workplane] = {}
        # cut out trailing edge device (ted) from segment
        ted_offset = 0.0
        if wing_config.segments[segment].trailing_edge_device is not None:
            logging.info(f"==> creating ted shapes for '{self.identifier}[{segment}]'")
            right_wing_hull, right_wing_cutout, ted_shape, ted_offset  = self._create_ted_shapes(current= current,
                                                                                                 current_hull= right_wing_hull,
                                                                                                 raw_ribs= right_wing_cutout,
                                                                                                 start_segment= segment,
                                                                                                 end_segment= segment,
                                                                                                 wing_config= wing_config)
            teds[f"{wing_config.segments[segment].trailing_edge_device.name}[{segment}]"] = ted_shape
            pass

        logging.info(f"==> combining shapes --> '{self.identifier}[{segment}]'")
        final_right_segments[segment] = (right_wing_hull
                                         .union(right_wing_spare)
                                         .union(right_wing_cutout)
                                         .cut(right_wing_slot)
                                         .combine())

        #############################
        # create the other segments #
        #############################
        glue_in_mounts: dict[str, Workplane] = {}
        glue_support_ted_offset = ted_offset + self.printer_wall_thickness*3
        for segment in range(1, len(wing_config.segments)):
            wing_segment = wing_config.segments[segment]
            # create all wing shapes that are need to produce a hull and the base for the ribs
            # the shapes are offsetted by  1 and 2 * printer_wall_thickness
            logging.info(f"==> creating offset wing shapes for '{self.identifier}[{segment}]'")
            current, current_2xpwt_offset, current_pwt_offset = self._create_basic_wing_shapes(current,
                                                                                               current_2xpwt_offset,
                                                                                               current_pwt_offset,
                                                                                               wing_config,
                                                                                               segment)
            # add a wing_tip
            if wing_segment.tip_type is not None:
                logging.info(f"==> creating tip '{wing_segment.tip_type}' shape for '{self.identifier}[{segment}]'")
                if wing_segment.tip_type == 'flat':
                    final_right_segments[segment] = current
                elif wing_segment.tip_type == 'round':
                    # TODO: implement a wing tip
                    # using a simple fillet does work in fusion360 but not with cadquery
                    current = current.faces("%PLANE and >Y").wires().toPending().fillet(wing_segment.length*0.95)
                    final_right_segments[segment] = current

                if raw_ribs is not None:
                    logging.info(f"==> adding glue support --> '{self.identifier}[{segment-1}]'")
                    tip_glue_tongue = (raw_ribs.solids(">X").faces("<Y").workplane(-3).split(keepTop=True)
                                .faces("<X").workplane(-self.printer_wall_thickness * 2).split(keepBottom=True)
                                .faces(">X").workplane(-glue_support_ted_offset).split(keepBottom=True))
                    final_right_segments[segment-1] = final_right_segments[segment-1].union(tip_glue_tongue)
                    raw_ribs=None
            else:
                # make a hull that is 2 * printer_wall_thickness thick
                logging.info(f"==> creating wing hull for '{self.identifier}[{segment}]'")
                current_hull = Workplane(current.vals()[-1].cut(current_2xpwt_offset.vals()[-1]))

                # create the base shape of the main spare and the spare's plane
                logging.info(f"==> creating main spare shape for '{self.identifier}[{segment}]'")
                raw_spare, spare_plane = self._create_spare_shape(current=current_2xpwt_offset, segment=segment,
                                                                  wing_config=wing_config, spare_idx=0)
                #right_wing_spare = right_wing_spare.add(raw_spare)

                # create the cut out for the ribs in an hour glass like shape
                # the cut out is created in a way that the main spare fits into it nicely
                logging.info(f"==> creating rib shapes for '{self.identifier}[{segment}]'")
                raw_ribs, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part = self._create_ribs_shape(
                    current_2xpwt_offset, segment, wing_config, leading_edge_start, trailing_edge_start, not lower_part)

                # create a shape for the slot that is needed to make the wing printable in vase mode
                # only spare with index 0 will get this slot
                logging.info(f"==> creating rib slot for '{self.identifier}[{segment}]'")
                right_wing_slot = (Workplane(spare_plane)
                                   .box(length=self.gap_rel_printer_wall_thickness * self.printer_wall_thickness,
                                        width=100,
                                        height=wing_segment.length * 10,
                                        centered=(False, False, True)))

                # create all other spares
                for spare_idx in range(1, len(wing_segment.spare_list)):
                    logging.info(f"==> creating spare '{spare_idx}' shapes for '{self.identifier}[{segment}]'")
                    raw_add_spar, _ = self._create_spare_shape(current=current_2xpwt_offset, segment=segment,
                                                               wing_config=wing_config, spare_idx=spare_idx)
                    raw_spare = raw_spare.add(raw_add_spar)

                try:
                    raw_spare.combine(glue=True)
                except ValueError:
                    pass

                # cut out trailing edge device (ted) from segment
                ted = wing_segment.trailing_edge_device
                if ted is not None:
                    # collect teds with the same name
                    same_teds_indx = [i
                                 for i, t in enumerate(wing_config.segments)
                                 if t.trailing_edge_device is not None
                                 and t.trailing_edge_device.name == ted.name]
                    last_ind = same_teds_indx[0]
                    for ind in same_teds_indx[1:]:
                        # fill missing parameters with values from the father ted
                        wing_config.segments[ind].trailing_edge_device.rel_chord_root = (
                            wing_config.segments[same_teds_indx[0]].trailing_edge_device.rel_chord_root)
                        wing_config.segments[ind].trailing_edge_device.rel_chord_tip = (
                            wing_config.segments[same_teds_indx[0]].trailing_edge_device.rel_chord_tip)
                        if ind != last_ind+1:
                            raise ValueError(f"same ted names should be in a sequence no segments in between")
                        last_ind = ind

                    if ted.servo(self._servo_information) is not None:
                        # if we have a servo defined for the ted than we create the mount and an access opening (cover)
                        # TODO: return the ted link plane( with origin and x-direction)
                        logging.info(f"==> create servo mount and cover shapes --> '{self.identifier}[{segment}]'")
                        current_hull, glue_in_mount = self._create_servo_mount_and_cover(current, current_hull, segment, wing_config,
                                                                          ted.servo_placement)
                        glue_in_mounts[f"{self.identifier}[{segment}].servo_mount"] = glue_in_mount
                    # create the shape of the ted including the hinge
                    # TODO: use the ted link origin and direction to construct a rudder horn with linkage for the ted
                    logging.info(f"==> creating ted shapes for '{self.identifier}[{segment}]'")
                    current_hull, raw_ribs, ted_shape, ted_offset = self._create_ted_shapes(current= current,
                                                                                            current_hull= current_hull,
                                                                                            raw_ribs= raw_ribs,
                                                                                            start_segment= same_teds_indx[0],
                                                                                            end_segment= same_teds_indx[-1],
                                                                                            wing_config= wing_config)
                    teds[f"{ted.name}[{segment}]"] = ted_shape

                    # set the glue_support_offset as we had a ted
                    new_glue_support_ted_offset = ted_offset + self.printer_wall_thickness * 3
                    glue_support_ted_offset = new_glue_support_ted_offset
                else:
                    previous_ted: TrailingEdgeDevice = wing_config.segments[segment-1].trailing_edge_device
                    if previous_ted is not None:
                        ted_offset = (1.0 - previous_ted.rel_chord_tip) * 0.5 * wing_segment.root_airfoil.chord
                        glue_support_ted_offset = glue_support_ted_offset + ted_offset
                    new_glue_support_ted_offset = self.printer_wall_thickness * 5

                # add some glue tongues for easier glueing the segments
                logging.info(f"==> adding glue support --> '{self.identifier}[{segment-1}]'")
                self.create_tip_glue_tongue(
                    final_right_segments=final_right_segments,
                    raw_ribs_part=raw_ribs.solids(">X"),
                    segment=segment,
                    num_glue_tongue_ribs=3,
                    glue_support_ted_offset=glue_support_ted_offset)
                glue_support_ted_offset = new_glue_support_ted_offset

                self.create_tip_glue_tongue(
                    final_right_segments=final_right_segments,
                    raw_ribs_part=raw_ribs.solids("<X"),
                    segment=segment,
                    num_glue_tongue_ribs=3,
                    glue_support_ted_offset=0.)

                # finally put everything together
                logging.info(f"==> combining shapes --> '{self.identifier}[{segment}]'")
                final_right_segments[segment] = (
                    current_hull
                    .union(raw_spare)
                    .union(raw_ribs)
                    .cut(right_wing_slot)
                    .combine())
                    #.fix_shape())

            right_wing_pwt_offset.add(current_pwt_offset)
            pass

        # we combine everything and try to fix the shape
        final_right_wing = Workplane()
        for wing_seg in final_right_segments:
            final_right_wing = final_right_wing.add(wing_seg)
        #final_right_wing = final_right_wing.fix_shape()

        # now we decide if we need the left, right or both wings for the wing
        # for the vertical stabilizer with the rudder we do only need one side
        if self.wing_side == "LEFT":
            final_right_wing = final_right_wing.mirror("XZ")
            for (k, v) in teds.items():
                teds[k] = v.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_right_wing = final_right_wing.mirror("XZ")
            final_right_wing = final_right_wing.union(left_right_wing, glue=True)

            _teds: dict[str, Workplane] = teds.copy()
            for (k, v) in teds.items():
                _teds[f"{k}*"] = v.mirror("XZ")
            teds = _teds

        final_right_wing = final_right_wing.combine()#.fix_shape().combine()

        # translate all shapes to the final place in the airplane
        # TODO: remove translations from creator... this should be translated, later or by assembly constraints
        final_right_wing = (final_right_wing.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}", severity=logging.DEBUG))

        for (k, v) in teds.items():
            teds[k] = (v.translate(wing_config.nose_pnt)
                       .display(name=f"{self.identifier}.ted[{k}]", severity=logging.DEBUG))

        # append main shapes
        final_dict: dict[str, Workplane] = {self.identifier: final_right_wing}

        # append all teds
        for (k, v) in teds.items():
            final_dict[f"{self.identifier}.{k}"] = v

        # append all single segments
        for i, wing_seg in enumerate(final_right_segments):
            final_dict[f"{self.identifier}[{i}]"] = wing_seg

        final_dict.update(glue_in_mounts)
        return final_dict

    def create_tip_glue_tongue(self,
                               final_right_segments: list[Workplane],
                               raw_ribs_part: Workplane,
                               segment: NonNegativeInt,
                               rel_tongue_length: NonNegativeFloat = 0.8,
                               glue_tongue_depth: NonNegativeFloat = 3.,
                               num_glue_tongue_ribs: NonNegativeInt = 2,
                               glue_tongue_ribs_rel_pos: NonNegativeFloat = 0.3,
                               glue_tongue_ribs_rel_length: NonNegativeFloat = 3.,
                               glue_tongue_ribs_minimum_distance: NonNegativeFloat = 5.0,
                               glue_support_ted_offset: NonNegativeFloat = 0.0):

        tip_glue_tongue = raw_ribs_part.faces("<Y").workplane(-glue_tongue_depth).split(keepTop=True)
        f_bb = tip_glue_tongue.faces("<Y").val().BoundingBox()

        if f_bb.xlen*rel_tongue_length < glue_tongue_depth*3:
            logging.warn(f"Cannot make a tongue for segment '{segment-1}' as the gap is too small. You can change the length of your segments")
            return # if the tongue's base is to small we cannot make a tongue
        
        # cutting of 55° to the right
        tip_glue_tongue = (tip_glue_tongue.copyWorkplane(
            Workplane("YZ", origin=f_bb.center + Vector(
                ((f_bb.xlen * 0.5 - glue_support_ted_offset) * rel_tongue_length , 0, 0)))
            .transformed((0, 90-55, 0))).split(keepBottom=True))

        # cutting of 55° to the left
        tip_glue_tongue = (
            tip_glue_tongue.copyWorkplane(
                Workplane("YZ", origin=f_bb.center - Vector((f_bb.xlen * rel_tongue_length * 0.5, 0, 0)))
                .transformed((0, 55-90, 0))).split(keepTop=True))
        final_right_segments[segment - 1] = final_right_segments[segment - 1].union(tip_glue_tongue)

        # cutting some ribs for more strength
        f_bb = tip_glue_tongue.faces("<Y").val().BoundingBox()
        gap = self.gap_rel_printer_wall_thickness * self.printer_wall_thickness

        # enforce a distance of at least glue_tongue_ribs_minimum_distance mm between the enforcement ribs
        while ((num_glue_tongue_ribs > 1) and
               (f_bb.xlen * glue_tongue_ribs_rel_pos * 2. / (num_glue_tongue_ribs-1) <= glue_tongue_ribs_minimum_distance)):
            num_glue_tongue_ribs = num_glue_tongue_ribs - 1
        if num_glue_tongue_ribs == 1:
            range = [0.0]
        else:
            range = np.arange(start=-f_bb.xlen * glue_tongue_ribs_rel_pos,
                              stop=f_bb.xlen * glue_tongue_ribs_rel_pos + 1.e-5,
                              step=f_bb.xlen * glue_tongue_ribs_rel_pos * 2. / (num_glue_tongue_ribs-1))
        for s in range:
            cut_top = (Workplane("YZ", origin=f_bb.center + Vector((s, 0, f_bb.zlen * 0.5)))
                       .box(glue_tongue_ribs_rel_length * glue_tongue_depth,
                            f_bb.zlen - self.printer_wall_thickness * 2.,
                            gap,
                            centered=(True, True, True)))
            cut_bottom = (Workplane("YZ", origin=f_bb.center + Vector((s, 0, -f_bb.zlen * 0.5)))
                          .box(glue_tongue_ribs_rel_length * glue_tongue_depth,
                               (f_bb.zlen - self.printer_wall_thickness * 2.),
                               gap,
                               centered=(True, True, True)))
            final_right_segments[segment - 1] = final_right_segments[segment - 1].cut(cut_top).cut(cut_bottom)

    def _create_servo_mount_and_cover(self, current: Workplane, current_hull: Workplane, segment: int,
                                      wing_config: WingConfiguration, placement: Literal['top', 'bottom'] = 'top',
                                      rim_size:float=2.5) -> tuple[Workplane, Workplane]:
        ted = wing_config.segments[segment].trailing_edge_device

        wing_plane = wing_config.get_wing_workplane(segment=segment).plane

        servo_mount = ted.servo(self._servo_information).create_laying_mount_for_wing()
        cover = ted.servo(self._servo_information).create_servo_cover_for_wing(self.printer_wall_thickness, rim_size, in_plane= None)
        cover_small = ted.servo(self._servo_information).create_servo_cover_for_wing(self.printer_wall_thickness, 0., in_plane= None)

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
                       .faces("%BSPLINE").faces(selector).chamfer(1.9 * self.printer_wall_thickness))
        cover = cover.union(toUnion=cover_small, clean=True, glue=False, tol=1.0e-3)
        updated_hull = updated_hull.union(toUnion=cover)

        #cover.display("cover", 500)
        #current_hull.display("hull", 500)
        #updated_hull.display("hull", 500)
        #servo_mount.display("servo_mount", 500)

        # box=Workplane().box(3,1,12, centered=False)
        # box = (Workplane(box.findSolid().mirror(mirrorPlane="YZ")
        #                   .rotate((0, 0, 0), (0, 1, 0), servo_orientation_deg).located(plane.location)))
        # trans = plane.xDir * so.x + plane.yDir * so.y + plane.zDir * (so.z - (so.z - sob.z) * 0.15)
        # box = box.translate(trans).display("box",24234)

        glue_in_mount = ted.servo(self._servo_information).create_laying_glue_in_mount(base_thickness=MOUNT_PLATE_THICKNESS, placement='bottom')
        glue_in_mount = mirror_and_rotate(glue_in_mount)
        glue_in_mount = glue_in_mount.translate(trans_mount)

        return updated_hull, glue_in_mount

    def calculate_lowest_point_for_mount(self,
                                         segment: NonNegativeInt,
                                         ted: TrailingEdgeDevice,
                                         wing_config: WingConfiguration,
                                         wing_plane: Plane):
        x_offset_interval = np.linspace(-(ted.servo(self._servo_information).leading_length + ted.servo(self._servo_information).latch_length),
                                        ted.servo(self._servo_information).trailing_length + ted.servo(self._servo_information).latch_length,
                                        10)
        y_offset_interval = np.linspace(-ted.servo(self._servo_information).height, 0.0, 3)

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


    def _create_ted_shapes(self,
                           current: Workplane,
                           current_hull: Workplane,
                           raw_ribs: Workplane,
                           start_segment: NonNegativeInt,
                           end_segment: NonNegativeInt,
                           wing_config: WingConfiguration
                           ) -> Tuple[Workplane, Workplane, Workplane, float]:

        wcs: WingSegment = wing_config.segments[start_segment]
        ted: TrailingEdgeDevice = wing_config.segments[start_segment].trailing_edge_device
        ted_root_plane, ted_tip_plane = wing_config.get_trailing_edge_device_planes(start_segment, end_segment)

        # make the intersect and cut shape and create the ted
        ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip, ted_distance = (
            ted_sketch_creators[ted.hinge_type](ted=ted,
                                                wing_config=wing_config,
                                                segment=start_segment,
                                                end_segment=end_segment,
                                                printer_settings=self._printer_settings))

        # intersect it with the wing
        ted_intersect = (Workplane()
                         .placeSketch(ted_sketch.moved(ted_root_plane.location),
                                      ted_sketch_tip.moved(ted_tip_plane.location)).loft())
        ted_shape = current.intersect(ted_intersect)

        length = (ted_tip_plane.origin - ted_root_plane.origin)
        if ted.side_spacing_root > 0:
            #TODO: better to use a split
            ted_shape = ted_shape.cut(
                Workplane(inPlane=ted_root_plane).box(wcs.root_airfoil.chord * 4,
                                                      wcs.root_airfoil.chord * 4,
                                                      ted.side_spacing_root,
                                                      centered=(True, True, False)))
            length = (ted_tip_plane.origin - ted_root_plane.origin)

        if ted.side_spacing_tip > 0:
            #TODO: better to use a split
            ted_shape = ted_shape.cut(
                Workplane(inPlane=ted_root_plane).workplane(offset=length.y - ted.side_spacing_tip)
                .box(wcs.root_airfoil.chord * 4,
                     wcs.root_airfoil.chord * 4,
                     wcs.root_airfoil.chord * 4,
                     centered=(True, True, False)))

        # cut it from the wing
        wing_cutout = (Workplane()
                       .placeSketch(wing_sketch.moved(ted_root_plane.location),
                                    wing_sketch_tip.moved(ted_tip_plane.location)).loft())

        current_hull = current_hull.cut(wing_cutout)
        raw_ribs = raw_ribs.cut(wing_cutout)

        return current_hull, raw_ribs, ted_shape, ted_distance

    def _create_basic_root_segment_shapes(self, wing_config: WingConfiguration):
        segment: int = 0
        root_plane = wing_config.get_wing_workplane(segment).plane.rotated((90,0,0))
        tip_plane = wing_config.get_wing_workplane(segment+1).plane.rotated((90,0,0))

        wing_root_segment_lambda = lambda offset : (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[segment].root_airfoil.airfoil,
                root_chord=wing_config.segments[segment].root_airfoil.chord,
                root_dihedral=wing_config.segments[segment].root_airfoil.dihedral,
                root_incidence=wing_config.segments[segment].root_airfoil.incidence,
                length=wing_config.segments[segment].length,
                sweep=wing_config.segments[segment].sweep,
                tip_chord=wing_config.segments[segment].tip_airfoil.chord,
                tip_dihedral=wing_config.segments[segment].tip_airfoil.dihedral,
                tip_incidence=wing_config.segments[segment].tip_airfoil.incidence,
                tip_airfoil=wing_config.segments[segment].tip_airfoil.airfoil,
                offset=offset,
                number_interpolation_points=wing_config.segments[0].number_interpolation_points,
                root_plane=root_plane,
                tip_plane=tip_plane
            ))

        right_wing_pwt_offset: Workplane = wing_root_segment_lambda(self.printer_wall_thickness)
        right_wing_2xpwt_offset: Workplane = wing_root_segment_lambda(2.0 * self.printer_wall_thickness)
        right_wing: Workplane = wing_root_segment_lambda(0.0)

        return right_wing, right_wing_2xpwt_offset, right_wing_pwt_offset

    def _create_basic_wing_shapes(self, _current: Workplane,
                                  _current_2xpwt_offset: Workplane,
                                  _current_pwt_offset: Workplane,
                                  wing_config:WingConfiguration,
                                  segment: int):
        segment_config = wing_config.segments[segment]
        root_plane = wing_config.get_wing_workplane(segment).plane.rotated((90,0,0))
        tip_plane = wing_config.get_wing_workplane(segment+1).plane.rotated((90,0,0))

        wing_segment_lambda = lambda actual, offset : actual.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_airfoil.chord,
            tip_dihedral=segment_config.tip_airfoil.dihedral,
            tip_incidence=segment_config.tip_airfoil.incidence,
            tip_airfoil=segment_config.tip_airfoil.airfoil,
            offset=offset,
            number_interpolation_points=segment_config.number_interpolation_points,
            root_plane=root_plane,
            tip_plane=tip_plane
        )

        current_pwt_offset = wing_segment_lambda(_current_pwt_offset, self.printer_wall_thickness)
        current_2xpwt_offset = wing_segment_lambda(_current_2xpwt_offset, 2.0 * self.printer_wall_thickness)
        current = wing_segment_lambda(_current,0.0)
        return current, current_2xpwt_offset, current_pwt_offset

    def _create_spare_shape(self, current: Workplane, segment: int, wing_config: WingConfiguration,
                            spare_idx: int = 0) -> Tuple[Workplane, Plane]:
        spare = wing_config.segments[segment].spare_list[spare_idx]

        # create spare sketch
        spare_sketch = self._construct_spare_sketch(printer_wall_thickness=self.printer_wall_thickness,
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
        root_chord = wing_config.segments[segment].root_airfoil.chord
        teof = 0.0
        if ted is not None:
            teof = (max((root_chord * (1 - ted.rel_chord_root)),
                        ((wing_config.segments[segment].tip_airfoil.chord + wing_config.segments[segment].sweep) *
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
            trailing_edge_start = wing_config.segments[segment].root_airfoil.chord - trailing_edge_offset

        # calculating the leading edge guides from root to tip
        root_nose = np.asarray((.0, .0, .0))
        root_nose_offset = root_nose + np.asarray((leading_edge_offset, .0, .0))
        tip_nose = np.asarray((wing_config.segments[segment].sweep, wing_config.segments[segment].length, 0.))
        tip_nose_offset = tip_nose + np.asarray((leading_edge_offset, .0, .0))

        # calculating the trailing edge guides from root to tip
        root_tail = np.asarray((wing_config.segments[segment].root_airfoil.chord, .0, .0))
        root_tail_offset = root_tail - np.asarray((trailing_edge_offset, .0, .0))
        tip_tail = tip_nose + np.asarray((wing_config.segments[segment].tip_airfoil.chord, .0, .0))
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

    def _construct_spare_sketch(self, printer_wall_thickness: float, spare_support_dimension_width: float,
                                spare_support_dimension_height: float) -> Sketch:
        """
        Construct a sketch that is extruded to form a spare.

        For the vase mode it is important to leave gaps as the top part of the spare is connected to the
        upper hull of the wing and the bottom part to the bottom hull.
        """
        gap_height = self.gap_rel_printer_wall_thickness * printer_wall_thickness

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
