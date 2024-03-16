import logging

import numpy as np

from typing import Union, Literal, Tuple, cast as tcast

from math import cos, asin, degrees, radians, atan2

from cadquery import Workplane, Plane, Sketch
from cadquery.occ_impl.shapes import Edge
from cadquery.occ_impl.geom import Vector, Location

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration, TrailingEdgeDevice, WingSegment

from cq_plugins.wing.wing_segment import wing_segment
from cq_plugins.wing.wing_root_segment import wing_root_segment
from cq_plugins.fix_shape.fix_shape import fix_shape
from cq_plugins.segmentToEdge import segmentToEdge


class VaseModeWingCreator(AbstractShapeCreator):
    """
    """

    def __init__(self, creator_id: str, wing_index: Union[str, int], printer_wall_thickness: float,
                 leading_edge_offset_factor: float, trailing_edge_offset_factor: float, spare_position_factor: float = 1. / 3.,
                 minimum_rib_angle: float = 45, spare_perpendicular: bool = False,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT", "RIGHT", "BOTH"] = "RIGHT", loglevel: int = logging.INFO):
        """
        TODO: leading_edge_offset and trailing_edge_offset should be a factor in terms of the chord

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
        self.spare_position_factor: float = spare_position_factor
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
        logging.info(f"wing spare from configuration --> '{self.identifier}'")
        wing_config: WingConfiguration = self._wing_config[self.wing_index]

        segment = 0  # root segment
        # create root segment shapes for hull creation
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
                           .box(length=0.5*self.printer_wall_thickness,
                                width=100,
                                height=wing_config.segments[segment].length * 3,
                                centered=(False, False, True))
                           )

        final_right_wing = right_wing_hull.add(right_wing_spare).add(right_wing_cutout).cut(right_wing_slot)
        # final_right_wing.display(f"fin | {segment}", 500)

        # create additional spares
        for spare_idx in range(1, len(wing_config.segments[segment].spare_list)):
            spare_shape, _ = self._create_spare_shape(
                current=current_pwt_offset,
                segment=segment,
                wing_config=wing_config,
                spare_idx=spare_idx)
            pass
            final_right_wing = final_right_wing.add(spare_shape)

        # dictionary for trailing edge devices (teds)
        teds: dict[str, Workplane] = {}

        # create the other segments
        for segment_config in wing_config.segments[1:]:
            segment = segment + 1
            current, current_2xpwt_offset, current_pwt_offset = self._create_basic_wing_shapes(current,
                                                                                               current_2xpwt_offset,
                                                                                               current_pwt_offset,
                                                                                               segment_config)

            current_hull = Workplane(current.vals()[-1].cut(current_2xpwt_offset.vals()[-1]))

            raw_spare, spare_plane = self._create_spare_shape(current=current_pwt_offset, segment=segment,
                                                              wing_config=wing_config, spare_idx=0)
            right_wing_spare = right_wing_spare.add(raw_spare)

            raw_ribs, leading_edge_start, trailing_edge_start, spare_vector_origin, lower_part = self._create_ribs_shape(
                current_pwt_offset, segment, wing_config, leading_edge_start, trailing_edge_start, not lower_part)
            right_wing_cutout.add(raw_ribs)

            right_wing_slot = (Workplane(spare_plane)
                               .box(length=0.5*self.printer_wall_thickness,
                                    width=100,
                                    height=wing_config.segments[segment].length * 10,
                                    centered=(False, False, True))
                               )

            for spare_idx in range(1, len(wing_config.segments[segment].spare_list)):
                raw_add_spar, _ = self._create_spare_shape(current=current_pwt_offset, segment=segment,
                                                           wing_config=wing_config, spare_idx=spare_idx)

            # cut out trailing edge device (ted) from segment
            if wing_config.segments[segment].trailing_edge_device is not None:
                current_hull, raw_ribs, ted_shape = self._create_ted_shapes(current, current_hull, raw_ribs,
                                                                            segment, wing_config)
                teds[f"{wing_config.segments[segment].trailing_edge_device.name}[{segment}]"] = ted_shape
                pass

            final_right_wing = final_right_wing.add(
                current_hull
                .add(raw_spare)
                .add(raw_ribs)
                .cut(right_wing_slot)
                .combine())

            right_wing_pwt_offset.add(current_pwt_offset)
            pass

        final_right_wing = final_right_wing.fix_shape().combine()
        right_wing_cutout = right_wing_cutout.combine(glue=True)

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

    def _create_ted_shapes(self, current: Workplane, current_hull: Workplane, raw_ribs: Workplane,
                           segment: int, wing_config: WingConfiguration) -> Tuple[Workplane, Workplane, Workplane]:
        wcs: WingSegment = wing_config.segments[segment]
        ted: TrailingEdgeDevice = wing_config.segments[segment].trailing_edge_device
        ted_root_plane, ted_tip_plane = wing_config.get_trailing_edge_device_planes(segment)

        # make the cut and create the ted
        ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip = self._ted_sketch_by_suspension_type(ted, wing_config,
                                                                                                       segment)

        ted_intersect = (Workplane(inPlane=ted_root_plane)
                         .placeSketch(ted_sketch, ted_sketch_tip).loft())
        ted_shape = current.intersect(ted_intersect)

        # TODO: Cut the side_spacing from the ted_shape
        ted_shape = ted_shape.cut(
            Workplane(inPlane=ted_root_plane).box(wcs.root_chord * 4, wcs.root_chord * 4, ted.side_spacing,
                                                  centered=(True, True, False)))
        length = (ted_tip_plane.origin - ted_root_plane.origin)

        ted_shape = ted_shape.cut(
            Workplane(inPlane=ted_root_plane).workplane(offset=length.y - ted.side_spacing).box(wcs.root_chord * 4,
                                                                                              wcs.root_chord * 4,
                                                                                              wcs.root_chord * 4,
                                                                                              centered=(True, True,
                                                                                                        False)))

        # cut it from the wing
        wing_cutout = (Workplane(inPlane=ted_root_plane)
                       .placeSketch(wing_sketch, wing_sketch_tip).loft())

        # current_hull.display("current_hull", 500)

        current_hull = current_hull.cut(wing_cutout)
        raw_ribs = raw_ribs.cut(wing_cutout)

        # ted_intersect.display("ted_intersect", 500)
        # wing_cutout.display("cutout", 500)
        # ted_shape.display("ted_shape", 500)
        # raw_ribs.display("raw_ribs", 500)

        return current_hull, raw_ribs, ted_shape

    def _ted_sketch_by_suspension_type(self, ted, wing_config: WingConfiguration, segment: int) \
            -> Tuple[Sketch, Sketch, Sketch, Sketch]:
        """
        The wing_shape is always used as a cut shape and the ted_shape is an intersect shape.
        """
        wcs: WingSegment = wing_config.segments[segment]

        ted_root_plane, ted_tip_plane = wing_config.get_trailing_edge_device_planes(segment)
        loft_direction_vector = ted_root_plane.toLocalCoords(ted_tip_plane.origin)
        loft_direction_vector_length = np.linalg.norm(np.array(list(loft_direction_vector.toTuple())))

        max_chord = max(wcs.root_chord * ted.rel_chord_root,
                        wcs.tip_chord * ted.rel_chord_tip + wcs.sweep)

        if ted.suspension_type == "middle":
            ted_sketch: Sketch = (Sketch()
                                  .segment((ted.hinge_spacing, 0), (max_chord, max_chord))
                                  .segment((max_chord, max_chord), (max_chord, -max_chord))
                                  .close()
                                  .assemble()
                                  )
            wing_sketch: Sketch = (Sketch()
                                   .segment((0, -max_chord), (0, max_chord))
                                   .segment((0, max_chord), (max_chord, max_chord))
                                   .segment((max_chord, max_chord), (max_chord, -max_chord))
                                   .close()
                                   .assemble()
                                   )

            ted_sketch_tip = ted_sketch.moved(
                Location(loft_direction_vector.normalized().multiply(loft_direction_vector_length - ted.side_spacing)))
            ted_sketch = ted_sketch.moved(
                Location(loft_direction_vector.normalized().multiply(ted.side_spacing)))
            wing_sketch_tip = wing_sketch.moved(Location(loft_direction_vector * 2))
        elif ted.suspension_type == "top_simple":
            top, bottom = wing_config.get_points_on_surface(segment, ted.rel_chord_root, 0, "root_airfoil")
            top_t, bottom_t = wing_config.get_points_on_surface(segment, ted.rel_chord_tip, 1.0, "root_airfoil")

            top_offset = top_t - top

            ted_sketch: Sketch = (Sketch()
                                  .segment((ted.hinge_spacing, -top.y), (max_chord, -top.y))
                                  .segment((max_chord, -top.y), (max_chord, max_chord))
                                  .close()
                                  .assemble()
                                  )
            wing_sketch: Sketch = (Sketch()
                                   .segment((0, -max_chord), (0, max_chord))
                                   .segment((0, max_chord), (max_chord, max_chord))
                                   .segment((max_chord, max_chord), (max_chord, -max_chord))
                                   .close()
                                   .assemble()
                                   )

            _ted_sketch_tip: Sketch = (Sketch()
                                       .segment((top_offset.x + ted.hinge_spacing, -top_t.y), (max_chord, -top_t.y))
                                       .segment((max_chord, -top_t.y), (max_chord, max_chord))
                                       .close()
                                       .assemble()
                                       )
            _wing_sketch_tip: Sketch = (Sketch()
                                        .segment((top_offset.x, -max_chord), (top_offset.x, max_chord))
                                        .segment((top_offset.x, max_chord), (max_chord, max_chord))
                                        .segment((max_chord, max_chord), (max_chord, -max_chord))
                                        .close()
                                        .assemble()
                                        )

            length = np.linalg.norm(np.array(list(top_offset.toTuple())))

            ted_sketch_tip = _ted_sketch_tip.moved(Location(Vector(0, 0, length)))
            wing_sketch_tip = _wing_sketch_tip.moved(Location(Vector(0, 0, length)))
            pass
        elif ted.suspension_type == "top":
            top, bottom = wing_config.get_points_on_surface(segment, ted.rel_chord_root, 0, "root_airfoil")
            top_t, bottom_t = wing_config.get_points_on_surface(segment, ted.rel_chord_tip, 1.0, "root_airfoil")

            top_offset = top_t - top
            root_radius = abs((bottom - top).y)
            tip_radius = abs((bottom_t - top_t).y)

            ted_sketch: Sketch = (Sketch()
                                  .segment((max_chord, -top.y), (max_chord, -3 * max_chord), 'help')
                                  .arc((0, -top.y), root_radius, 180 - ted.negative_deflection_deg,
                                       -(90 - ted.negative_deflection_deg), tag="arc")
                                  .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                                  .segment((0, -top.y), (0, -top.y + 2 * ted.hinge_spacing), 'edge')
                                  .segmentToEdge('arc', 0.0, 'edge', 1.0)
                                  # .segmentToEdge('arc', 0.0, (0, -top.y))
                                  .segment((0, -top.y), (max_chord, -top.y), 'top')
                                  .segmentToEdge('diag', 1.0, 'top', 1.0)
                                  .select('help').delete()
                                  .assemble()
                                  )
            _ted_sketch_tip: Sketch = (Sketch()
                                       .segment((max_chord, -top_t.y), (max_chord, -3 * max_chord), 'help')
                                       .arc((top_offset.x, -top_t.y), tip_radius, 180 - ted.negative_deflection_deg,
                                            -(90 - ted.negative_deflection_deg), "arc")
                                       .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                                       .segment((top_offset.x, -top_t.y),
                                                (top_offset.x, -top_t.y + 2 * ted.hinge_spacing), 'edge')
                                       .segmentToEdge('arc', 0.0, 'edge', 1.0)
                                       # .segmentToEdge('arc', 0.0, (top_offset.x, -top_t.y))
                                       .segment((top_offset.x, -top_t.y), (max_chord, -top_t.y), 'top')
                                       .segmentToEdge('diag', 1.0, 'top', 1.0)
                                       .select('help').delete()
                                       .assemble()
                                       )

            wing_sketch: Sketch = (Sketch()
                                   .segment((max_chord, -top.y), (max_chord, top.y), 'help')
                                   .arc((0., -top.y), root_radius + ted.hinge_spacing, 180,
                                        -(90 - ted.negative_deflection_deg), 'arc')
                                   .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                                   .select('help').delete()
                                   .segmentToEdge('arc', 0.0, (-ted.hinge_spacing, -top.y), 'diag2')
                                   .segment((-ted.hinge_spacing, -top.y), (-ted.hinge_spacing, -max_chord))
                                   .segment((-ted.hinge_spacing, -max_chord), (max_chord, -max_chord))
                                   .segmentToEdge(90., 'diag')
                                   .assemble()
                                   )
            _wing_sketch_tip: Sketch = (Sketch()
                                        .segment((max_chord, -top_t.y), (max_chord, top.y), 'help')
                                        .arc((top_offset.x, -top_t.y), tip_radius + ted.hinge_spacing, 180,
                                             -(90 - ted.negative_deflection_deg), 'arc')
                                        .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                                        .select('help').delete()
                                        .segmentToEdge('arc', 0.0, (-ted.hinge_spacing + top_offset.x, -top_t.y),
                                                       'diag2')
                                        .segment((-ted.hinge_spacing + top_offset.x, -top_t.y),
                                                 (-ted.hinge_spacing + top_offset.x, -max_chord))
                                        .segment((-ted.hinge_spacing + top_offset.x, -max_chord),
                                                 (max_chord, -max_chord))
                                        .segmentToEdge(90., 'diag')
                                        .assemble()
                                        )
            length = np.linalg.norm(np.array(list(top_offset.toTuple())))

            ted_sketch_tip = _ted_sketch_tip.moved(Location(Vector(0, 0, length)))
            wing_sketch_tip = _wing_sketch_tip.moved(Location(Vector(0, 0, length)))
            pass
        else:
            pass
        return ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip

    def _create_basic_root_segment_shapes(self, wing_config: WingConfiguration, segment: int = 0):
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
                offset=self.printer_wall_thickness))
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
                offset=2.0 * self.printer_wall_thickness))
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
                offset=0.0))
        return right_wing, right_wing_2xpwt_offset, right_wing_pwt_offset

    def _create_basic_wing_shapes(self, _current, _current_2xpwt_offset, _current_pwt_offset, segment_config):
        current_pwt_offset = _current_pwt_offset.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=self.printer_wall_thickness)
        current_2xpwt_offset = _current_2xpwt_offset.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=2.0 * self.printer_wall_thickness)
        current = _current.wing_segment(
            length=segment_config.length,
            sweep=segment_config.sweep,
            tip_chord=segment_config.tip_chord,
            tip_dihedral=segment_config.tip_dihedral,
            tip_incidence=segment_config.tip_incidence,
            tip_airfoil=segment_config.tip_airfoil,
            offset=0.0)
        return current, current_2xpwt_offset, current_pwt_offset

    def _create_spare_shape(self, current: Workplane, segment: int, wing_config: WingConfiguration,
                            spare_idx: int = 0) -> Tuple[Workplane, Plane]:
        spare_vector = wing_config.segments[segment].spare_list[spare_idx].spare_vector
        spare_vector_origin = wing_config.segments[segment].spare_list[spare_idx].spare_origin
        spare_support_dimension_width = wing_config.segments[segment].spare_list[
            spare_idx].spare_support_dimension_width
        spare_support_dimension_height = wing_config.segments[segment].spare_list[
            spare_idx].spare_support_dimension_height
        spare_length = wing_config.segments[segment].spare_list[spare_idx].spare_length

        # create spare sketch
        spare_sketch = VaseModeWingCreator._construct_spare_sketch(printer_wall_thickness=self.printer_wall_thickness,
                                               spare_support_dimension_width=spare_support_dimension_width,
                                               spare_support_dimension_height=spare_support_dimension_height)
        # calc extrude direction
        if spare_vector is None:
            wing_wp = wing_config.get_wing_workplane(segment)
            diff = 0.0
            if segment > 0:
                diff = ((wing_config.segments[segment - 1].tip_chord - wing_config.segments[segment].tip_chord)
                        * self.spare_position_factor)
            rotation = degrees(atan2(wing_config.segments[segment].sweep - diff, wing_config.segments[segment].length))
            origin = wing_wp.plane.origin + Vector(
                (wing_config.segments[segment].root_chord * self.spare_position_factor, 0, 0))
            xDir = wing_wp.plane.xDir
            normal = wing_wp.plane.yDir
            spare_plane = (Plane(origin=origin, xDir=xDir, normal=normal)
                           .rotated((0.0, rotation, 0.0)))
        else:
            # the spare vector defines a vector the spare should follow (normal of the spare_plane)
            # the spare vector can be changed for segments or can be the same
            wing_wp = wing_config.get_wing_workplane(segment)
            xDir = wing_wp.plane.xDir
            normal = spare_vector.normalized()
            spare_plane = Plane(origin=spare_vector_origin, xDir=xDir, normal=normal)
            pass

        extrude_length = wing_config.segments[segment].length * 10 if spare_length is None else spare_length
        # extrude and intersect
        raw_spare = (Workplane(spare_plane)
                     .placeSketch(spare_sketch)
                     .extrude(extrude_length, both=True)
                     .intersect(toIntersect=current))
        return raw_spare, spare_plane

    def _create_ribs_shape(self, current, segment, wing_config, leading_edge_start, trailing_edge_start,
                           start_upper_part, spare_idx: int = 0):
        ted = wing_config.segments[segment].trailing_edge_device
        root_chord = wing_config.segments[segment].root_chord
        teof = 0.0
        if ted is not None:
            teof = (max((root_chord * (1 - ted.rel_chord_root)),
                       ((wing_config.segments[segment].tip_chord+ wing_config.segments[segment].sweep) *
                        (1 - ted.rel_chord_tip)))
                    * ted.trailing_edge_offset_factor)

        trailing_edge_offset = self.trailing_edge_offset_factor * root_chord \
            if teof < self.trailing_edge_offset_factor * root_chord else teof

        cutout_face, leading_edge_start, trailing_edge_start, lower_part, spare_vector_origin = (
            VaseModeWingCreator._rib_cutout(
                segment=segment, wing_config=wing_config, printer_wall_thickness=self.printer_wall_thickness,
                leading_edge_offset=self.leading_edge_offset_factor*root_chord, trailing_edge_offset=trailing_edge_offset,
                leading_edge_start=leading_edge_start, trailing_edge_start=trailing_edge_start,
                start_upper_part=start_upper_part, minimum_rib_angle=self.minimum_rib_angle,
                spare_perpendicular=self.spare_perpendicular, spare_position_factor=self.spare_position_factor,
                spare_idx=spare_idx))
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
    def _rib_cutout(segment: int, wing_config: WingConfiguration, printer_wall_thickness: float, leading_edge_offset: float,
                    trailing_edge_offset: float, leading_edge_start: float = None, trailing_edge_start: float = None,
                    start_upper_part: bool = False, minimum_rib_angle: float = 45, spare_perpendicular: bool = False,
                    spare_position_factor: float = 1. / 3., spare_idx: int = 0) -> Tuple[Sketch, float, float, bool, Vector]:
        """
        Constructs a set of hourglass like structures in between the nose and the tail part of the wing.

        TODO: Implement a zigzag pattern for the rib segments, to improve stability.
        """

        (root_nose_offset, root_nose_start, root_tail_offset, root_tail_start, spare_nose_root,
         spare_nose_tip, spare_tail_root, spare_tail_tip, tip_nose, tip_nose_offset, tip_tail_offset,
         spare_vector_origin) = (
            VaseModeWingCreator._calculate_wing_construction_points(segment, printer_wall_thickness, leading_edge_offset, leading_edge_start,
                                                trailing_edge_offset, trailing_edge_start, spare_position_factor,
                                                wing_config, spare_perpendicular, spare_idx=spare_idx)
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
            #if not start_upper_part:
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
                                            trailing_edge_start: float, spare_position_factor: float,
                                            wing_config: WingConfiguration, spare_perpendicular: bool = False,
                                            spare_idx: int = 0):
        spare_vector = wing_config.segments[segment].spare_list[spare_idx].spare_vector
        spare_vector_origin = wing_config.segments[segment].spare_list[spare_idx].spare_origin
        spare_support_dimension_width = wing_config.segments[segment].spare_list[spare_idx].spare_support_dimension_width

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
        if spare_vector is None:
            spare_nose_root = (np.asarray((wing_config.segments[segment].root_chord, 0., 0.))
                               * spare_position_factor
                               - np.asarray((spare_support_width, 0., 0.)))
            spare_tail_root = (np.asarray((wing_config.segments[segment].root_chord, 0., 0.))
                               * spare_position_factor
                               + np.asarray((spare_support_width, 0., 0.)))
        else:
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

            pass

        _spare_vector_origin = None
        if not spare_perpendicular and spare_vector is None:
            spare_nose_tip = (tip_nose + np.asarray((1., 0., 0.)) * wing_config.segments[segment].tip_chord
                              * spare_position_factor
                              - np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                              - np.asarray((1., 0., 0.)) * printer_wall_thickness)
            spare_tail_tip = (tip_nose + np.asarray((1., 0., 0.)) * wing_config.segments[segment].tip_chord
                              * spare_position_factor
                              + np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                              + np.asarray((1., 0., 0.)) * printer_wall_thickness)
        elif not spare_perpendicular and spare_vector is not None:  # a spare vector is given
            vec = np.asarray((spare_vector.x, spare_vector.y, spare_vector.z))
            norm_vec = vec / np.linalg.norm(vec)
            spare_nose_tip = spare_nose_root + norm_vec * wing_config.segments[segment].length
            spare_tail_tip = spare_tail_root + norm_vec * wing_config.segments[segment].length
            _spare_vector_origin = (spare_vector_origin
                                    + Vector(tuple(norm_vec * wing_config.segments[segment].length))
                                    - Vector((wing_config.segments[segment].sweep, 0., 0.))
                                    )
            _spare_vector_origin.y = 0
        else:  # spare is perpendicular to x-axis (roll axis of the plane)
            spare_nose_tip = (spare_nose_root
                              + np.asarray((0., 1., 0.)) * wing_config.segments[segment].length)
            spare_tail_tip = (spare_tail_root
                              + np.asarray((0., 1., 0.)) * wing_config.segments[segment].length)

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
        gap_height = 0.5 * printer_wall_thickness

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

                .segment(( x, gap_height / 2.0),
                         ( x, spare_support_dimension_height/2.0 - (gap_height / 2.0)))
                .segment(( x, spare_support_dimension_height/2.0 - (gap_height / 2.0)),
                         (-x, spare_support_dimension_height/2.0 - (gap_height / 2.0)))
                .segment((-x, spare_support_dimension_height/2.0 - (gap_height / 2.0)),
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
