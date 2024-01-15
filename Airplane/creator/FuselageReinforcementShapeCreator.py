import logging

import cadquery as cq
import numpy
from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator


class FuselageReinforcementShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, rib_width: float, rib_spacing, ribcage_factor: float,
                 reinforcement_pipes_diameter: float, print_resolution: float, fuselage_loft: str, full_wing_loft,
                 loglevel=logging.INFO):
        """
        Creates a cage like structure with pipes for CFRP-rods in the four intersections.
        :param creator_id:
        :param rib_width: the width of the enforcement rib (wall to wall)
        :param rib_spacing: minimum spacing between wing and enforcement
        :param ribcage_factor: the width of the enforcement cage is 'fuselage_width * ribcage_factor'
        :param reinforcement_pipes_diameter: the radius of the CFRP-rods that go through the fuselage
        :param print_resolution: 3D printer resolution
        :param fuselage_loft: the loft the enforcement should be designed for
        :param full_wing_loft: needed to calculate the ribcage dimensions
        """
        self.print_resolution = print_resolution
        self.rib_spacing = rib_spacing
        self.full_wing_loft = full_wing_loft
        self.fuselage_loft = fuselage_loft
        self.rib_width = rib_width
        self.ribcage_factor = ribcage_factor
        self.circle_factor = 0.9
        self.reinforcement_pipes_diameter = reinforcement_pipes_diameter
        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage_loft, self.full_wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating fuselage reinforcement for {self.fuselage_loft} --> '{self.identifier}'")

        fuselage_loft = shapes_of_interest[self.fuselage_loft]
        fullwing_loft = shapes_of_interest[self.full_wing_loft]
        fus_bbox = fuselage_loft.findSolid().BoundingBox()

        overlap = cq.Workplane('XZ').add(fullwing_loft).tag('middle').workplane(offset=fus_bbox.ymax).split(keepBottom=True) \
            .workplaneFromTagged('middle').workplane(offset=fus_bbox.ymin).split(keepTop=True)
        wing_bbox = overlap.findSolid().BoundingBox()

        max_z_position = wing_bbox.zmin - self.rib_spacing  # for high wing aircraft
        min_z_position = fus_bbox.zmin
        if (wing_bbox.zmax-wing_bbox.zmin)/2 + wing_bbox.zmin < (fus_bbox.zmax-fus_bbox.zmin)/2 + fus_bbox.zmin:
            min_z_position = wing_bbox.zmax + self.rib_spacing  # for low wing aircraft
            max_z_position = fus_bbox.zmax

        box_height = abs(max_z_position - min_z_position) * self.ribcage_factor
        box_width = fus_bbox.ylen * self.ribcage_factor

        center_x = fus_bbox.xlen/2+fus_bbox.xmin
        center_y = fus_bbox.ylen/2+fus_bbox.ymin
        center_z = min_z_position + box_height / 2

        outer_pipe_radius = self.reinforcement_pipes_diameter / 2

        centered = (True, True, False)
        shape__fuselage_reinforcement = cq.Workplane('YZ').workplane(offset=fus_bbox.xmin).tag('nose')\
            .moveTo(center_y, center_z).rect(box_width, box_height, forConstruction=True).tag('rect')\
            .vertices().tag('v_rect').vertices('>Y and >Z').tag('c1').box(self.rib_width, fus_bbox.zlen * 2, fus_bbox.xlen, centered=centered)\
            .vertices(tag='c1').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .vertices(tag='rect').vertices('<Y and <Z').tag('c2').box(self.rib_width, fus_bbox.zlen * 2, fus_bbox.xlen, centered=centered)\
            .vertices(tag='c2').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .vertices(tag='rect') .vertices('>Y and <Z').tag('c3').box(fus_bbox.zlen * 2, self.rib_width, fus_bbox.xlen, centered=centered)\
            .vertices(tag='c3').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .vertices(tag='rect') .vertices('<Y and >Z').tag('c4').box(fus_bbox.zlen * 2, self.rib_width, fus_bbox.xlen, centered=centered)\
            .vertices(tag='c4').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)  # \

        rods = cq.Workplane('YZ')\
            .add(shape__fuselage_reinforcement.vertices(tag='c1')).vertices(tag='c1').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .add(shape__fuselage_reinforcement.vertices(tag='c2')).vertices(tag='c2').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .add(shape__fuselage_reinforcement.vertices(tag='c3')).vertices(tag='c3').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)\
            .add(shape__fuselage_reinforcement.vertices(tag='c4')).vertices(tag='c4').cylinder(radius=outer_pipe_radius, height=fus_bbox.xlen, centered=centered)

        # middle section cutouts
        start_v = cq.Vector(fus_bbox.xmin, center_y, center_z)
        shape__fuselage_reinforcement = self._do_cutout("XZ", box_height * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)
        shape__fuselage_reinforcement = self._do_cutout('XY', box_width * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)

        # side coutouts
        box_sides = abs(fus_bbox.ylen - box_width)/2
        start_v = cq.Vector(fus_bbox.xmin, box_sides/2 + box_width/2 + center_y, center_z)
        shape__fuselage_reinforcement = self._do_cutout('XY', box_sides * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)

        start_v = cq.Vector(fus_bbox.xmin, -box_sides/2 - box_width/2 + center_y, center_z)
        shape__fuselage_reinforcement = self._do_cutout('XY', box_sides * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)

        # top cutouts
        box_top = abs(fus_bbox.zmax - (center_z + box_height/2))
        start_v = cq.Vector(fus_bbox.xmin, center_y, center_z + box_height/2 + box_top/2)
        shape__fuselage_reinforcement = self._do_cutout('XZ', box_top * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)

        # bottom cutouts
        box_bottom = abs((center_z - box_height/2)-fus_bbox.zmin)
        start_v = cq.Vector(fus_bbox.xmin, center_y, center_z - box_height/2 - box_bottom/2)
        shape__fuselage_reinforcement = self._do_cutout('XZ', box_bottom * self.circle_factor, fus_bbox, outer_pipe_radius,
                                                        shape__fuselage_reinforcement, start_v)

        shape__fuselage_reinforcement.display(name=self.identifier, severity=logging.DEBUG)
        return {str(self.identifier): shape__fuselage_reinforcement, f"{self.identifier}.rods": rods}

    def _do_cutout(self, plane, box_height, fus_bbox, outer_pipe_radius, shape__fuselage_reinforcement, start_v):
        for offset in numpy.arange(0, fus_bbox.xlen * 1.3, box_height * 1.1):
            cutout = cq.Workplane(plane, origin=start_v).move(offset, 0) \
                .cylinder(height=fus_bbox.zlen * 1.2, radius=(box_height - outer_pipe_radius * 2.1) / 2,
                          direct=cq.Vector(0, 0, 1))
            shape__fuselage_reinforcement -= cutout
        return shape__fuselage_reinforcement
