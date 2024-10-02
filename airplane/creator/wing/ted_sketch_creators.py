from typing import Tuple

import numpy as np
import math

from cadquery import Sketch, Location
from pydantic.v1 import NonNegativeInt

from airplane.aircraft_topology.printer3d import Printer3dSettings
from airplane.aircraft_topology.wing import WingConfiguration
from airplane.aircraft_topology.wing.WingSegment import WingSegment
from airplane.aircraft_topology.wing.TrailingEdgeDevice import TrailingEdgeDevice

"""
This file contains trailing edge device (ted) sketch creators, which create sketches for 
cutting the ted from the wings hull. The sketches are lofted and the loft ist used for the ted 
to INTERSECT with the wings hull to get the ted and the wing ted loft is used to CUT the ted from
the wings hull.

New ted sketch creators should have the signature:

def create_XYZ_ted_sketch(segment: int, ted: TrailingEdgeDevice, wing_config: WingConfiguration) 
    -> Tuple[Sketch, Sketch, Sketch, Sketch, float]:
    ...
    return ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip
    
It returns four sketches:
ted_sketch, ted_sketch_tip the sketches to be lofted and intersected with the wings hull 
wing_sketch, wing_sketch_tip the sketches to be lofted and cut from the wings hull.
"""

def create_MIDDLE_ted_sketch(segment: NonNegativeInt,
                             end_segment: NonNegativeInt,
                             ted: TrailingEdgeDevice,
                             wing_config: WingConfiguration,
                             printer_settings: Printer3dSettings)\
        -> Tuple[Sketch, Sketch, Sketch, Sketch, float]:
    wcs: WingSegment = wing_config.segments[segment]
    ted_root_plane, ted_tip_plane = wing_config.get_trailing_edge_device_planes(segment, segment)
    loft_direction_vector = ted_root_plane.toLocalCoords(ted_tip_plane.origin)
    loft_direction_vector_length = np.linalg.norm(np.array(list(loft_direction_vector.toTuple())))
    max_chord = max(wcs.root_airfoil.chord * ted.rel_chord_root,
                    wcs.tip_airfoil.chord * ted.rel_chord_tip + wcs.sweep)

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
        Location(loft_direction_vector.normalized().multiply(loft_direction_vector_length - ted.side_spacing_root)))
    if ted.side_spacing_root > 0:
        ted_sketch = ted_sketch.moved(
            Location(loft_direction_vector.normalized().multiply(ted.side_spacing_root)))
    wing_sketch_tip = wing_sketch.moved(Location(loft_direction_vector * 2))
    # TODO: ted_offset should be where the ted reaches into the wing
    ted_offset = 1.0
    return ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip, ted_offset


def create_SIMPLE_TOP_ted_sketch(segment: NonNegativeInt, end_segment: NonNegativeInt, ted: TrailingEdgeDevice, wing_config: WingConfiguration, printer_settings: Printer3dSettings)\
        -> Tuple[Sketch, Sketch, Sketch, Sketch, float]:
    wcs: WingSegment = wing_config.segments[segment]
    max_chord = max(wcs.root_airfoil.chord * ted.rel_chord_root,
                    wcs.tip_airfoil.chord * ted.rel_chord_tip + wcs.sweep)

    top, bottom = wing_config.get_points_on_surface(segment, ted.rel_chord_root, 0, "root_airfoil")
    top_t, bottom_t = wing_config.get_points_on_surface(segment, ted.rel_chord_tip, 1.0, "root_airfoil")
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
    ted_sketch_tip: Sketch = (Sketch()
                               .segment((ted.hinge_spacing, -top_t.y), (max_chord, -top_t.y))
                               .segment((max_chord, -top_t.y), (max_chord, max_chord))
                               .close()
                               .assemble()
                               )
    wing_sketch_tip: Sketch = (Sketch()
                                .segment((0.0, -max_chord), (0.0, max_chord))
                                .segment((0.0, max_chord), (max_chord, max_chord))
                                .segment((max_chord, max_chord), (max_chord, -max_chord))
                                .close()
                                .assemble()
                                )
    # TODO: ted_offset should be where the ted reaches into the wing
    ted_offset = 1.0
    return ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip, ted_offset


def create_TOP_ted_sketch(segment: NonNegativeInt, end_segment: NonNegativeInt, ted: TrailingEdgeDevice, wing_config: WingConfiguration, printer_settings: Printer3dSettings)\
        -> Tuple[Sketch, Sketch, Sketch, Sketch, float]:
    wcs: WingSegment = wing_config.segments[segment]
    wcs_end: WingSegment = wing_config.segments[end_segment]
    sweep = sum([wing_config.segments[i].sweep for i in range(segment, end_segment + 1)])

    max_chord = max(wcs.root_airfoil.chord * ted.rel_chord_root,
                    wcs_end.tip_airfoil.chord * ted.rel_chord_tip + sweep)

    top, bottom = wing_config.get_points_on_surface(segment, ted.rel_chord_root, 0, "root_airfoil")
    top_t, bottom_t = wing_config.get_points_on_surface(end_segment, ted.rel_chord_tip, 1.0, "root_airfoil")
    top_t_ta, bottom_t_ta = wing_config.get_points_on_surface(end_segment, ted.rel_chord_tip, 1.0, "tip_airfoil")

    root_radius = abs((bottom - top).y)
    tip_radius = abs((bottom_t - top_t).y)

    offset = printer_settings.wall_thickness*1.5
    theta_rad = math.asin(offset / (root_radius + ted.hinge_spacing))
    theta_deg = math.degrees(theta_rad)

    ted_sketch: Sketch = (Sketch()
                          .segment((max_chord, -top.y), (max_chord, -3 * max_chord), 'help')
                          .arc((0, -top.y), root_radius, 180 - ted.negative_deflection_deg,
                               -(90 - ted.negative_deflection_deg), tag="arc")
                          .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                          .segment((0, -top.y), (0, -top.y + 2 * offset), 'edge')
                          .segmentToEdge('arc', 0.0, 'edge', 1.0)
                          # .segmentToEdge('arc', 0.0, (0, -top.y))
                          .segment((0, -top.y), (max_chord, -top.y), 'top')
                          .segmentToEdge('diag', 1.0, 'top', 1.0)
                          .select('help').delete()
                          .assemble()
                          )
    ted_sketch_tip: Sketch = (Sketch()
                               .segment((max_chord, -top_t_ta.y), (max_chord, -3 * max_chord), 'help')
                               .arc((0.0, -top_t_ta.y), tip_radius, 180 - ted.negative_deflection_deg,
                                    -(90 - ted.negative_deflection_deg), "arc")
                               .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                               .segment((0.0, -top_t_ta.y),
                                        (0.0, -top_t_ta.y + 2 * ted.hinge_spacing), 'edge')
                               .segmentToEdge('arc', 0.0, 'edge', 1.0)
                               # .segmentToEdge('arc', 0.0, (0.0, -top_t.y))
                               .segment((0.0, -top_t_ta.y), (max_chord, -top_t_ta.y), 'top')
                               .segmentToEdge('diag', 1.0, 'top', 1.0)
                               .select('help').delete()
                               .assemble()
                               )

    wing_sketch: Sketch = (Sketch()
                           .segment((max_chord, -top.y+offset), (max_chord, top.y), 'help')
                           .arc((0., -top.y), root_radius + ted.hinge_spacing, 180-theta_deg,
                                -(90 - ted.negative_deflection_deg), 'arc')
                           .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                           .select('help').delete()
                           .segmentToEdge('arc', 0.0, (-ted.hinge_spacing, -top.y+offset), 'diag2')
                           .segment((-ted.hinge_spacing, -top.y+offset), (-ted.hinge_spacing, -max_chord))
                           .segment((-ted.hinge_spacing, -max_chord), (max_chord, -max_chord))
                           .segmentToEdge(90., 'diag')
                           .assemble()
                           )
    wing_sketch_tip: Sketch = (Sketch()
                                .segment((max_chord, -top_t_ta.y+offset), (max_chord, top_t_ta.y), 'help')
                                .arc((0, -top_t_ta.y), tip_radius + ted.hinge_spacing, 180-theta_deg,
                                     -(90 - ted.negative_deflection_deg), 'arc')
                                .segmentToEdge(-(270 - ted.negative_deflection_deg + 90), 'help', 'diag')
                                .select('help').delete()
                                .segmentToEdge('arc', 0.0, (-ted.hinge_spacing, -top_t_ta.y+offset),
                                               'diag2')
                                .segment((-ted.hinge_spacing, -top_t_ta.y+offset),
                                         (-ted.hinge_spacing, -max_chord))
                                .segment((-ted.hinge_spacing, -max_chord),
                                         (max_chord, -max_chord))
                                .segmentToEdge(90., 'diag')
                                .assemble()
                                )

    return ted_sketch, ted_sketch_tip, wing_sketch, wing_sketch_tip, root_radius


ted_sketch_creators = {
    "middle" : create_MIDDLE_ted_sketch,
    "top" : create_TOP_ted_sketch,
    "top_simple" : create_SIMPLE_TOP_ted_sketch,
}
