import logging

import numpy as np
from scipy.spatial.transform import Rotation as R

from typing import Union, Literal, Tuple, cast as tcast

from cadquery import Workplane, Plane, Sketch
from cadquery.occ_impl.shapes import Edge, Solid
from cadquery.occ_impl.geom import Vector

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.aircraft_topology.WingConfiguration import WingConfiguration

from cq_plugins.wing.wing_segment import wing_segment
from cq_plugins.wing.wing_root_segment import wing_root_segment
from cq_plugins.fix_shape.fix_shape import fix_shape
from cq_plugins.segmentToEdge import segmentToEdge

def _calc_edge_start(sketch: Sketch, id_s: str, spare_nose_tip, tip_nose) -> Tuple[float, float, bool]:
    try:
        p_le = sketch.segmentToEdge('spare_nose', 180, 'rib_nl' + id_s, 'helper')._tags['helper'][0].endPoint()
        sketch.select('helper').delete()
        p_te = sketch.segmentToEdge('spare_tail', 180, 'rib_tl' + id_s, 'helper')._tags['helper'][0].endPoint()
        sketch.select('helper').delete()
        lower_part = True
        if ((spare_nose_tip[0] - p_le.x) > 0 and abs(p_le.y - tip_nose[1]) < 1e-5):
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


def _rib_cutout(
        segment: int,
        wing_config: WingConfiguration,
        printer_wall_thickness: float,
        spare_support_dimension_width: float,
        spare_support_dimension_height: float,
        leading_edge_offset: float,
        trailing_edge_offset: float,
        leading_edge_start: float = None,
        trailing_edge_start: float = None,
        start_upper_part: bool = False,  # construction starts with the upper part of the hourglas structure
        minimum_rib_angle: float = 45,
        spare_perpendicular: bool = False,
        spare_position_factor: float = 1. / 3.,
) -> Tuple[Sketch, float, float, bool]:
    """
    Constructs a set of hourglass like structures in between the nose and the tail part of the wing.

    """

    (root_nose_offset, root_nose_start, root_tail_offset, root_tail_start, spare_nose_root,
     spare_nose_tip, spare_tail_root, spare_tail_tip, tip_nose, tip_nose_offset, tip_tail_offset) = (
        _calculate_wing_construction_points(
        leading_edge_offset, leading_edge_start, printer_wall_thickness, segment, spare_perpendicular,
        spare_position_factor, spare_support_dimension_width, trailing_edge_offset, trailing_edge_start, wing_config)
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
                        180.-minimum_rib_angle, 'spare_tail', 'rib_tl') # rib: tail left  \
            .segmentToEdge(minimum_rib_angle, 'tail_os', 'rib_tr')     # rib: tail right /
            .segmentToEdge(180.,'nose_os', 'help_top', forConstruction=False)
            .segmentToEdge('rib_tl', 180.,'spare_nose', 'help_middle', forConstruction=False)
            .segment(Vector(tuple(root_nose_start)),'rib_nl')          # rib: nose left  /
            .segmentToEdge('help_middle', 1, 'help_top', 1., 'rib_nr')        # rib: nose right \
            .segment(Vector(tuple(root_tail_start)),Vector(tuple(root_tail_start))
                     -Vector((0,wing_config.segments[segment].length*0.1,0)),'nose_ext')
            .segment(Vector(tuple(root_nose_start)),Vector(tuple(root_nose_start))
                    -Vector((0,wing_config.segments[segment].length*0.1,0)),'tail_ext')
            .segmentToEdge('nose_ext',1.,'tail_ext',1.,'root')
            )
    else:
        const_lines = (
            const_lines
            .segmentToEdge(Vector(tuple(root_tail_start)), minimum_rib_angle, 'tail_os', 'rib_tr')     # rib: tail right (upper) /
            .segmentToEdge(180.,'nose_os', 'help_top', forConstruction=False)
            .segmentToEdge('help_top', 1., Vector(tuple(root_nose_start)), 'rib_nr') # rib: nose right (upper) \
            .segment(Vector(tuple(root_tail_start)),Vector(tuple(root_tail_start))
                     -Vector((0,wing_config.segments[segment].length*0.1,0)),'nose_ext')
            .segment(Vector(tuple(root_nose_start)),Vector(tuple(root_nose_start))
                    -Vector((0,wing_config.segments[segment].length*0.1,0)),'tail_ext')
            .segmentToEdge('nose_ext',1.,'tail_ext',1.,'root')
            )    #show(const_lines)

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
        if not start_upper_part:
            const_lines.select('help_middle' + id_s).delete()

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
    if not start_upper_part:
        const_lines.select('help_middle' + id_s).delete()
    const_lines.select('nose_os').delete()
    const_lines.select('spare_nose').delete()
    const_lines.select('spare_tail').delete()
    const_lines.select('tail_os').delete()

    return const_lines, *_calc_edge_start(const_lines, id_s, spare_nose_tip, tip_nose)


def _calculate_wing_construction_points(leading_edge_offset, leading_edge_start, printer_wall_thickness, segment,
                                        spare_perpendicular, spare_position_factor, spare_support_dimension_width,
                                        trailing_edge_offset, trailing_edge_start, wing_config):
    if leading_edge_start is None:
        leading_edge_start = leading_edge_offset
    if trailing_edge_start is None:
        trailing_edge_start = wing_config.segments[segment].root_chord - trailing_edge_offset
    root_nose = np.asarray((.0, .0, .0))
    root_nose_offset = root_nose + np.asarray((leading_edge_offset, .0, .0))
    root_nose_start = np.asarray((leading_edge_start, .0, .0))
    root_tail = np.asarray((1., .0, .0)) * wing_config.segments[segment].root_chord
    root_tail_offset = root_tail - np.asarray((trailing_edge_offset, .0, .0))
    root_tail_start = np.asarray((trailing_edge_start, .0, .0))
    tip_nose = np.asarray((wing_config.segments[segment].sweep, wing_config.segments[segment].length, 0.))
    tip_nose_offset = tip_nose + np.asarray((1.0, .0, .0)) * leading_edge_offset
    tip_tail = tip_nose + np.asarray((1., .0, .0)) * wing_config.segments[segment].tip_chord
    tip_tail_offset = tip_tail - np.asarray((1., .0, .0)) * trailing_edge_offset
    # Calculating the spare nose and tail positions
    spare_nose_root = (np.asarray((1., 0., 0.)) * wing_config.segments[segment].root_chord
                       * spare_position_factor
                       - np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                       - np.asarray((1., 0., 0.)) * printer_wall_thickness)
    spare_tail_root = (np.asarray((1., 0., 0.)) * wing_config.segments[segment].root_chord
                       * spare_position_factor
                       + np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                       + np.asarray((1., 0., 0.)) * printer_wall_thickness)
    if not spare_perpendicular:
        spare_nose_tip = (tip_nose + np.asarray((1., 0., 0.)) * wing_config.segments[segment].tip_chord
                          * spare_position_factor
                          - np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                          - np.asarray((1., 0., 0.)) * printer_wall_thickness)
        spare_tail_tip = (tip_nose + np.asarray((1., 0., 0.)) * wing_config.segments[segment].tip_chord
                          * spare_position_factor
                          + np.asarray((1., 0., 0.)) * spare_support_dimension_width / 2
                          + np.asarray((1., 0., 0.)) * printer_wall_thickness)
    else:
        spare_nose_tip = (spare_nose_root
                          + np.asarray((0., 1., 0.)) * wing_config.segments[segment].length)
        spare_tail_tip = (spare_tail_root
                          + np.asarray((0., 1., 0.)) * wing_config.segments[segment].length)
    return root_nose_offset, root_nose_start, root_tail_offset, root_tail_start, spare_nose_root, spare_nose_tip, spare_tail_root, spare_tail_tip, tip_nose, tip_nose_offset, tip_tail_offset


class VaseModeRibCutoutCreator(AbstractShapeCreator):
    """
    Create a cutout shape that should be intersected with the hull shape.
    The shape :
               | \  ||     / | trailing
    leading    |  \ ||   /   | edge
    edge       |   \||/      |
               |   /||\      |
               |  / ||   \   |
               | /  ||     \ |
               offset        offset
    """

    def __init__(self, creator_id: str,
                 wing_index: Union[str, int],
                 printer_wall_thickness: float,
                 spare_support_geometry_is_round: bool,
                 spare_support_dimension_width: float,
                 spare_support_dimension_height: float,
                 leading_edge_offset: float,
                 trailing_edge_offset: float,
                 offset: float,
                 spare_position_factor: float = 1. / 3.,
                 minimum_rib_angle: float = 45,
                 spare_perpendicular: bool = False,
                 invert_cutout: bool = False,
                 taper_cutout: float = 0.,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT", "RIGHT", "BOTH"] = "RIGHT",
                 loglevel: int =logging.INFO):
        """
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
        self.spare_support_geometry_is_round: bool = spare_support_geometry_is_round
        self.spare_support_dimension_width: float = spare_support_dimension_width
        self.spare_support_dimension_height: float = spare_support_dimension_height
        self.spare_perpendicular: bool = spare_perpendicular
        self.spare_position_factor: float = spare_position_factor
        self.leading_edge_offset: float = leading_edge_offset
        self.trailing_edge_offset: float = trailing_edge_offset
        self.offset: float = offset
        self.minimum_rib_angle: float = minimum_rib_angle
        self.invert_cutout: bool = invert_cutout
        self.taper_cutout: float = taper_cutout
        self.wing_side: Literal["LEFT", "RIGHT", "BOTH"] = wing_side
        self.wing_index: Union[str, int] = wing_index
        self._wing_config: dict[int, WingConfiguration] = wing_config

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing rib cutout from configuration --> '{self.identifier}'")

        wing_config: WingConfiguration = self._wing_config[self.wing_index]
        right_wing: Workplane = (
            Workplane('XZ')
            .wing_root_segment(
                root_airfoil=wing_config.segments[0].root_airfoil,
                root_chord=wing_config.segments[0].root_chord,
                root_dihedral=wing_config.segments[0].root_dihedral,
                root_incidence=wing_config.segments[0].root_incidence,
                length=wing_config.segments[0].length,
                sweep=wing_config.segments[0].sweep,
                tip_chord=wing_config.segments[0].tip_chord,
                tip_dihedral=wing_config.segments[0].tip_dihedral,
                tip_incidence=wing_config.segments[0].tip_incidence,
                tip_airfoil=wing_config.segments[0].tip_airfoil,
                offset=self.offset))

        segment = 0
        current: Workplane = right_wing
        right_wing_cutout, leading_edge_start, trailing_edge_start = (
            self._create_ribs_shape(current, segment,wing_config, None, None))

        for segment_config in wing_config.segments[1:]:
            segment = segment + 1
            current = current.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=self.offset)
            right_wing.add(current)

            raw_ribs, leading_edge_start, trailing_edge_start = self._create_ribs_shape(current, segment, wing_config,
                                                                                        leading_edge_start,
                                                                                        trailing_edge_start)
            right_wing_cutout.add(raw_ribs)

        right_wing_cutout = right_wing_cutout.combine(glue=True)

        if self.wing_side == "LEFT":
            right_wing = right_wing.mirror("XZ")
            right_wing_cutout = right_wing_cutout.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing = right_wing.mirror("XZ")
            right_wing = right_wing.union(left_wing)
            left_wing_cutout = right_wing_cutout.mirror("XZ")
            right_wing_cutout = right_wing_cutout.union(left_wing_cutout)

        right_wing = right_wing.fix_shape()
        right_wing = right_wing.translate(wing_config.nose_pnt).display(name=f"{self.identifier}",
                                                                        severity=logging.DEBUG)
        right_wing_cutout = right_wing_cutout.fix_shape()
        right_wing_cutout = right_wing_cutout.translate(wing_config.nose_pnt).display(name=f"{self.identifier}.cutout",
                                                                                      severity=logging.DEBUG)

        return {self.identifier: right_wing, f"{self.identifier}.cutout": right_wing_cutout}

    def _create_ribs_shape(self, current, segment, wing_config, leading_edge_start, trailing_edge_start):
        cutout_face, leading_edge_start, trailing_edge_start, lower_part = _rib_cutout(
            segment=segment,
            wing_config=wing_config,
            printer_wall_thickness=self.printer_wall_thickness,
            spare_support_dimension_width=self.spare_support_dimension_width,
            spare_support_dimension_height=self.spare_support_dimension_height,
            leading_edge_offset=self.leading_edge_offset,
            trailing_edge_offset=self.trailing_edge_offset,
            leading_edge_start=leading_edge_start,
            trailing_edge_start=trailing_edge_start,
            minimum_rib_angle=self.minimum_rib_angle,
            spare_perpendicular=self.spare_perpendicular,
            spare_position_factor=self.spare_position_factor)
        cutout_face.assemble()
        try:
            if self.invert_cutout:
                raw_ribs = (
                    wing_config.get_wing_workplane(segment=segment)
                    .placeSketch(cutout_face)
                    .extrude(until=100, taper=self.taper_cutout, both=True)
                    .intersect(current)
                )
            else:
                raw_ribs = (
                    wing_config.get_wing_workplane(segment=segment)
                    .placeSketch(cutout_face)
                    .add(current)
                    .cutThruAll(taper=self.taper_cutout)
                )
            pass
        except:
            logging.warning(f"could not create segment: {segment}!")
        pass
        return raw_ribs, leading_edge_start, trailing_edge_start


from math import cos, asin, degrees, radians, atan2


def _construct_spare_sketch(printer_wall_thickness: float, spare_support_dimension_width: float,
                            spare_support_dimension_height: float) -> Sketch:

    beta = degrees(asin((0.5 * printer_wall_thickness) / (0.5 * spare_support_dimension_width)))
    x = cos(radians(beta)) * (0.5 * spare_support_dimension_width)

    hight = 100
    spf = 0.5
    const_lines = (
        Sketch()
        .segment((-spf * spare_support_dimension_width - printer_wall_thickness, printer_wall_thickness * spf),
                 (-spf * spare_support_dimension_width - printer_wall_thickness, hight), 'left_t')
        .segment((spf * spare_support_dimension_width + printer_wall_thickness, printer_wall_thickness * spf),
                 (spf * spare_support_dimension_width + printer_wall_thickness, hight), 'right_t')
        .segment((-spf * spare_support_dimension_width - printer_wall_thickness, hight),
                 (spf * spare_support_dimension_width + printer_wall_thickness, hight), 'top')
        .segment((x, printer_wall_thickness * spf),
                 (spf * spare_support_dimension_width + printer_wall_thickness, printer_wall_thickness * spf))
        .segment((-x, printer_wall_thickness * spf),
                 (-(spf * spare_support_dimension_width + printer_wall_thickness), printer_wall_thickness * spf))
        .arc((0.0, 0.0), spf * spare_support_dimension_width, beta, 180. - (2. * beta), 'spare_t')
        # .assemble()
        .segment((-spf * spare_support_dimension_width - printer_wall_thickness, -printer_wall_thickness * spf),
                 (-spf * spare_support_dimension_width - printer_wall_thickness, -hight), 'left_b')
        .segment((spf * spare_support_dimension_width + printer_wall_thickness, -printer_wall_thickness * spf),
                 (spf * spare_support_dimension_width + printer_wall_thickness, -hight), 'right_b')
        .segment((-spf * spare_support_dimension_width - printer_wall_thickness, -hight),
                 (spf * spare_support_dimension_width + printer_wall_thickness, -hight), 'bottom')
        .segment((x, -printer_wall_thickness * spf),
                 (spf * spare_support_dimension_width + printer_wall_thickness, -printer_wall_thickness * spf))
        .segment((-x, -printer_wall_thickness * spf),
                 (-(spf * spare_support_dimension_width + printer_wall_thickness), -printer_wall_thickness * spf))
        .arc((0.0, 0.0), spf * spare_support_dimension_width, -beta, -(180. - (2. * beta)), 'spare_b')
        .assemble()
    )
    return const_lines

class VaseModeSpareCreator(AbstractShapeCreator):
    """
    """

    def __init__(self, creator_id: str,
                 wing_index: Union[str, int],
                 printer_wall_thickness: float,
                 spare_support_geometry_is_round: bool,
                 spare_support_dimension_width: float,
                 spare_support_dimension_height: float,
                 leading_edge_offset: float,
                 trailing_edge_offset: float,
                 offset: float,
                 spare_position_factor: float = 1. / 3.,
                 minimum_rib_angle: float = 45,
                 spare_perpendicular: bool = False,
                 invert_cutout: bool = False,
                 taper_cutout: float = 0.,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT", "RIGHT", "BOTH"] = "RIGHT",
                 loglevel: int =logging.INFO):
        """
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
        self.spare_support_geometry_is_round: bool = spare_support_geometry_is_round
        self.spare_support_dimension_width: float = spare_support_dimension_width
        self.spare_support_dimension_height: float = spare_support_dimension_height
        self.spare_perpendicular: bool = spare_perpendicular
        self.spare_position_factor: float = spare_position_factor
        self.leading_edge_offset: float = leading_edge_offset
        self.trailing_edge_offset: float = trailing_edge_offset
        self.offset: float = offset
        self.minimum_rib_angle: float = minimum_rib_angle
        self.invert_cutout: bool = invert_cutout
        self.taper_cutout: float = taper_cutout
        self.wing_side: Literal["LEFT", "RIGHT", "BOTH"] = wing_side
        self.wing_index: Union[str, int] = wing_index
        self._wing_config: dict[int, WingConfiguration] = wing_config

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing spare from configuration --> '{self.identifier}'")

        wing_config: WingConfiguration = self._wing_config[self.wing_index]
        segment = 0

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
                offset=self.offset))
        current: Workplane = right_wing

        right_wing_spare, spare_plane = self._create_spare_shape(current, segment, wing_config)

        #right_wing_spare.display("wing_w_spare", severity=logging.DEBUG)

        right_wing_slot = (Workplane(spare_plane)
                    .box(length=self.printer_wall_thickness,
                         width=100,
                         height=wing_config.segments[segment].length*2,
                         centered=False)
                    )
        right_wing = current

        for segment_config in wing_config.segments[1:]:
            segment = segment + 1
            current = current.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=self.offset)

            raw_spare, spare_plane = self._create_spare_shape(current, segment, wing_config)

            right_wing_spare = right_wing_spare.add(raw_spare)

            right_wing_slot = right_wing_slot.add(Workplane(spare_plane)
                        .box(length=self.printer_wall_thickness,
                             width=100,
                             height=wing_config.segments[segment].length,
                             centered=False)
                        )

            right_wing.add(current) #.add(right_wing_spare).cut(right_wing_slot))
            pass

        right_wing = right_wing.fix_shape()
        #right_wing_spare.display("wing_w_spare", severity=logging.DEBUG)
        #right_wing_spare = right_wing_spare.combine()

        if self.wing_side == "LEFT":
            right_wing = right_wing.mirror("XZ")
            right_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_slot = right_wing_slot.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing = right_wing.mirror("XZ")
            right_wing = right_wing.union(left_wing)
            left_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_spare = right_wing_spare.add(left_wing_spare)
            left_wing_slot = right_wing_slot.mirror("XZ")
            right_wing_slot = right_wing_slot.add(left_wing_slot)

        right_wing = right_wing.fix_shape()
        right_wing = right_wing.translate(wing_config.nose_pnt).display(name=f"{self.identifier}",
                                                                        severity=logging.DEBUG)
        right_wing_spare = right_wing_spare.fix_shape()
        right_wing_spare = (right_wing_spare.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}.spare", severity=logging.DEBUG))

        right_wing_slot = right_wing_slot.fix_shape()
        right_wing_slot = (right_wing_slot.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}.slot", severity=logging.DEBUG))

        return {self.identifier: right_wing,
                f"{self.identifier}.spare": right_wing_spare,
                f"{self.identifier}.slot": right_wing_slot}

    def _create_spare_shape(self, current, segment, wing_config):
        # create spare sketch
        spare_sketch = _construct_spare_sketch(printer_wall_thickness=self.printer_wall_thickness,
                                               spare_support_dimension_width=self.spare_support_dimension_width,
                                               spare_support_dimension_height=self.spare_support_dimension_height)
        # calc extrude direction
        wing_wp = wing_config.get_wing_workplane(segment)
        diff = 0.0
        if segment > 0:
            diff = (wing_config.segments[segment - 1].tip_chord - wing_config.segments[
                segment].tip_chord) * self.spare_position_factor
        rotation = degrees(atan2(wing_config.segments[segment].sweep - diff, wing_config.segments[segment].length))
        origin = wing_wp.plane.origin + Vector(
            (wing_config.segments[segment].root_chord * self.spare_position_factor, 0, 0))
        spare_plane = (Plane(origin=origin, xDir=wing_wp.plane.xDir, normal=wing_wp.plane.yDir)
                       .rotated((0.0, rotation, 0.0))
                       )
        # extrude and intersect
        raw_spare = (Workplane(spare_plane)
                     .placeSketch(spare_sketch)
                     .extrude(wing_config.segments[segment].length * 10, both=True)
                     .intersect(toIntersect=current))
        return raw_spare, spare_plane

class VaseModeWingCreator(AbstractShapeCreator):
    """
    """

    def __init__(self, creator_id: str,
                 wing_index: Union[str, int],
                 printer_wall_thickness: float,
                 spare_support_geometry_is_round: bool,
                 spare_support_dimension_width: float,
                 spare_support_dimension_height: float,
                 leading_edge_offset: float,
                 trailing_edge_offset: float,
                 offset: float,
                 spare_position_factor: float = 1. / 3.,
                 minimum_rib_angle: float = 45,
                 spare_perpendicular: bool = False,
                 invert_cutout: bool = False,
                 taper_cutout: float = 0.,
                 wing_config: dict[int, WingConfiguration] = None,
                 wing_side: Literal["LEFT", "RIGHT", "BOTH"] = "RIGHT",
                 loglevel: int =logging.INFO):
        """
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
        self.spare_support_geometry_is_round: bool = spare_support_geometry_is_round
        self.spare_support_dimension_width: float = spare_support_dimension_width
        self.spare_support_dimension_height: float = spare_support_dimension_height
        self.spare_perpendicular: bool = spare_perpendicular
        self.spare_position_factor: float = spare_position_factor
        self.leading_edge_offset: float = leading_edge_offset
        self.trailing_edge_offset: float = trailing_edge_offset
        self.offset: float = offset
        self.minimum_rib_angle: float = minimum_rib_angle
        self.invert_cutout: bool = invert_cutout
        self.taper_cutout: float = taper_cutout
        self.wing_side: Literal["LEFT", "RIGHT", "BOTH"] = wing_side
        self.wing_index: Union[str, int] = wing_index
        self._wing_config: dict[int, WingConfiguration] = wing_config

        super().__init__(creator_id, shapes_of_interest_keys=[], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"wing spare from configuration --> '{self.identifier}'")

        wing_config: WingConfiguration = self._wing_config[self.wing_index]

        segment = 0
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
                offset=2.0*self.printer_wall_thickness))

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

        right_wing_hull = Workplane( right_wing.vals()[-1].cut(right_wing_2xpwt_offset.vals()[-1]))

        current_pwt_offset: Workplane = right_wing_pwt_offset
        current_2xpwt_offset: Workplane = right_wing_2xpwt_offset
        current: Workplane = right_wing

        right_wing_spare, spare_plane = self._create_spare_shape(current_pwt_offset, segment, wing_config)
        right_wing_cutout, leading_edge_start, trailing_edge_start = (
            self._create_ribs_shape(current_pwt_offset, segment,wing_config, None, None))

        right_wing_slot = (Workplane(spare_plane)
                    .box(length=self.printer_wall_thickness,
                         width=100,
                         height=wing_config.segments[segment].length*3,
                         centered=(False,False,True))
                    )
        final_right_wing = right_wing_hull.add(right_wing_spare).add(right_wing_cutout).cut(right_wing_slot)

        for segment_config in wing_config.segments[1:]:
            segment = segment + 1
            current_pwt_offset = current_pwt_offset.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=self.printer_wall_thickness)

            current_2xpwt_offset = current_2xpwt_offset.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=2.0*self.printer_wall_thickness)

            current = current.wing_segment(
                length=segment_config.length,
                sweep=segment_config.sweep,
                tip_chord=segment_config.tip_chord,
                tip_dihedral=segment_config.tip_dihedral,
                tip_incidence=segment_config.tip_incidence,
                tip_airfoil=segment_config.tip_airfoil,
                offset=0.0)

            current_hull = Workplane(current.vals()[-1].cut(current_2xpwt_offset.vals()[-1]))

            raw_spare, spare_plane = self._create_spare_shape(current_pwt_offset, segment, wing_config)
            right_wing_spare = right_wing_spare.add(raw_spare)

            raw_ribs, leading_edge_start, trailing_edge_start = self._create_ribs_shape(current_pwt_offset, segment, wing_config,
                                                                                        leading_edge_start,
                                                                                        trailing_edge_start)
            right_wing_cutout.add(raw_ribs)

            right_wing_slot = (Workplane(spare_plane)
                               .box(length=self.printer_wall_thickness,
                                    width=100,
                                    height=wing_config.segments[segment].length * 10,
                                    centered=(False, False, True))
                               )
            final_right_wing = final_right_wing.add(
                current_hull
                .add(raw_spare)
                .add(raw_ribs)
                .cut(right_wing_slot)
                .combine())

            right_wing_pwt_offset.add(current_pwt_offset) #.add(right_wing_spare).cut(right_wing_slot))
            pass

        final_right_wing = final_right_wing.fix_shape().combine()
        right_wing_cutout = right_wing_cutout.combine(glue=True)

        if self.wing_side == "LEFT":
            right_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_slot = right_wing_slot.mirror("XZ")
            right_wing_cutout = right_wing_cutout.mirror("XZ")
            final_right_wing = final_right_wing.mirror("XZ")
        elif self.wing_side == "BOTH":
            left_wing_spare = right_wing_spare.mirror("XZ")
            right_wing_spare = right_wing_spare.add(left_wing_spare)

            left_wing_cutout = right_wing_cutout.mirror("XZ")
            right_wing_cutout = right_wing_cutout.union(left_wing_cutout)

            left_wing_slot = right_wing_slot.mirror("XZ")
            right_wing_slot = right_wing_slot.add(left_wing_slot)

            left_right_wing = final_right_wing.mirror("XZ")
            final_right_wing = final_right_wing.add(left_right_wing)


        right_wing_spare = right_wing_spare.fix_shape()
        right_wing_spare = (right_wing_spare.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}.spare", severity=logging.DEBUG))

        right_wing_cutout = right_wing_cutout.fix_shape()
        right_wing_cutout = right_wing_cutout.translate(wing_config.nose_pnt).display(name=f"{self.identifier}.cutout",
                                                                                      severity=logging.DEBUG)

        right_wing_slot = right_wing_slot.fix_shape()
        right_wing_slot = (right_wing_slot.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}.slot", severity=logging.DEBUG))

        final_right_wing = final_right_wing.fix_shape().combine()
        final_right_wing = (final_right_wing.translate(wing_config.nose_pnt)
                            .display(name=f"{self.identifier}", severity=logging.DEBUG))

        return {self.identifier: final_right_wing,
                f"{self.identifier}.spare": right_wing_spare,
                f"{self.identifier}.cutout": right_wing_cutout,
                f"{self.identifier}.slot": right_wing_slot}

    def _create_spare_shape(self, current, segment, wing_config):
        # create spare sketch
        spare_sketch = _construct_spare_sketch(printer_wall_thickness=self.printer_wall_thickness,
                                               spare_support_dimension_width=self.spare_support_dimension_width,
                                               spare_support_dimension_height=self.spare_support_dimension_height)
        # calc extrude direction
        wing_wp = wing_config.get_wing_workplane(segment)
        diff = 0.0
        if segment > 0:
            diff = (wing_config.segments[segment - 1].tip_chord - wing_config.segments[
                segment].tip_chord) * self.spare_position_factor
        rotation = degrees(atan2(wing_config.segments[segment].sweep - diff, wing_config.segments[segment].length))
        origin = wing_wp.plane.origin + Vector(
            (wing_config.segments[segment].root_chord * self.spare_position_factor, 0, 0))
        spare_plane = (Plane(origin=origin, xDir=wing_wp.plane.xDir, normal=wing_wp.plane.yDir)
                       .rotated((0.0, rotation, 0.0))
                       )
        # extrude and intersect
        raw_spare = (Workplane(spare_plane)
                     .placeSketch(spare_sketch)
                     .extrude(wing_config.segments[segment].length * 10, both=True)
                     .intersect(toIntersect=current))
        return raw_spare, spare_plane

    def _create_ribs_shape(self, current, segment, wing_config, leading_edge_start, trailing_edge_start):
        cutout_face, leading_edge_start, trailing_edge_start, lower_part = _rib_cutout(
            segment=segment,
            wing_config=wing_config,
            printer_wall_thickness=self.printer_wall_thickness,
            spare_support_dimension_width=self.spare_support_dimension_width,
            spare_support_dimension_height=self.spare_support_dimension_height,
            leading_edge_offset=self.leading_edge_offset,
            trailing_edge_offset=self.trailing_edge_offset,
            leading_edge_start=leading_edge_start,
            trailing_edge_start=trailing_edge_start,
            minimum_rib_angle=self.minimum_rib_angle,
            spare_perpendicular=self.spare_perpendicular,
            spare_position_factor=self.spare_position_factor)
        cutout_face.assemble()
        try:
            if self.invert_cutout:
                raw_ribs = (
                    wing_config.get_wing_workplane(segment=segment)
                    .placeSketch(cutout_face)
                    .extrude(until=100, taper=self.taper_cutout, both=True)
                    .intersect(current)
                )
            else:
                raw_ribs = (
                    wing_config.get_wing_workplane(segment=segment)
                    .placeSketch(cutout_face)
                    .add(current)
                    .cutThruAll(taper=self.taper_cutout)
                )
            pass
        except:
            logging.warning(f"could not create segment: {segment}!")
        pass
        return raw_ribs, leading_edge_start, trailing_edge_start
