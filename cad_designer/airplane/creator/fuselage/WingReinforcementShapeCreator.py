import logging

import cadquery as cq
import numpy
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import CreatorId, ShapeId


class WingReinforcementShapeCreator(AbstractShapeCreator):
    """Creates wing reinforcement ribs inside the fuselage.

    Attributes:
        fuselage_loft (str): Key of the fuselage loft shape to reinforce.
        full_wing_loft (str): Key of the full wing loft for overlap calculation.

    Returns:
        {id} (Workplane): Wing reinforcement ribs.
    """

    suggested_creator_id = "wing_reinforcement"

    def __init__(self,
                 creator_id: CreatorId,
                 fuselage_loft: ShapeId,
                 full_wing_loft: ShapeId,
                 loglevel=logging.INFO):
        self.full_wing_loft = full_wing_loft
        self.fuselage_loft = fuselage_loft
        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage_loft, self.full_wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating wing reinforcement --> '{self.identifier}'")

        rib_quantity = 7
        wing_rib_angle_roll = 0
        wing_rib_angle_yaw = 15
        rib_width = 1
        pipe_diameter = 6
        printer_resolution = 0.2
        chord_beam_position = 0.33
        tip_end_in_length_percent = 0.95
        beam_with_pipe = True

        wing = shapes_of_interest[self.full_wing_loft]
        big_wing = shapes_of_interest[self.fuselage_loft]

        wing_bbox = wing.findSolid().BoundingBox(tolerance=0.0001)
        wing_center = wing.findSolid().CenterOfBoundBox()

        root_section = wing.faces('<Y').display(name="root", severity=logging.NOTSET)
        tip_section = wing.faces('>Y').display(name="tip", severity=logging.NOTSET)

        ribs = self.construct_ribs(wing, rib_quantity, rib_width, wing_rib_angle_roll, wing_rib_angle_yaw)

        main_beam, main_pipe = self.construct_main_beam(wing, chord_beam_position, pipe_diameter, printer_resolution,
                                             root_section, tip_section, beam_with_pipe)

        second_beam, second_pipe = self.construct_main_beam(wing, 0.6, 3, printer_resolution, root_section,
                                               tip_section, beam_with_pipe)

        shapes = []
        rec_test = big_wing
        for i, rib in enumerate(ribs):
            rib = rib - main_pipe
            rib = rib - second_pipe
            shapes.append(rib.findSolid())
            rec_test = rec_test.cut(rib)
        reinforcement = cq.Workplane().newObject([main_beam.findSolid(), second_beam.findSolid(), *shapes ])
        rec_test = rec_test - main_beam
        rec_test = rec_test - second_beam
        rec_test = rec_test.combine(glue=True)
        rec_test.display(name=self.identifier, severity=logging.DEBUG)
        reinforcement.display(name=self.identifier, severity=logging.DEBUG)
        return {str(self.identifier): rec_test}

    def construct_ribs(self, wing, rib_quantity, rib_width, wing_rib_angle_roll, wing_rib_angle_yaw,
                       make_cross_rib=False, cut_offset_wing=False, skip_first=True):
        logging.debug("constructing ribs...")
        wing_bbox = wing.findSolid().BoundingBox(tolerance=1e-3)
        wing_center = wing.findSolid().CenterOfBoundBox()
        offset_wing = None
        if cut_offset_wing:
            offset_wing = cq.Workplane(obj=wing.findSolid().scale(0.8), origin=wing_center)
            trans = wing_center - offset_wing.findSolid().CenterOfBoundBox()
            offset_wing = offset_wing.translate(trans).display(name="offset", severity=logging.NOTSET)
        ribs: list[Workplane] = []
        origin = wing_center
        first = True
        for y_offset in numpy.linspace(wing_bbox.ymin, wing_bbox.ymax, num=rib_quantity):
            if skip_first & first:
                first=False
            else:
                origin.y = y_offset
                rib = self.create_diagonal_rib(cut_offset_wing, offset_wing, rib_width, wing, wing_bbox, wing_center,
                                               wing_rib_angle_roll, wing_rib_angle_yaw)
                ribs.append(rib)
                if make_cross_rib:
                    rib = self.create_diagonal_rib(cut_offset_wing, offset_wing, rib_width, wing, wing_bbox, wing_center,
                                                   180 - wing_rib_angle_roll, wing_rib_angle_yaw)
                    ribs.append(rib)
        return ribs

    def create_diagonal_rib(self, cut_offset_wing, offset_wing, rib_width, wing, wing_bbox, wing_center,
                            wing_rib_angle_roll, wing_rib_angle_yaw):
        section = cq.Workplane('XZ', origin=wing_center).transformed(
            rotate=(wing_rib_angle_roll, wing_rib_angle_yaw, 0)) \
            .add(wing).section()
        if cut_offset_wing:
            rib = cq.Workplane().copyWorkplane(section) \
                .cylinder(radius=max(wing_bbox.ylen * 1.1, wing_bbox.zlen * 1.2) / 2, height=rib_width).cut(offset_wing) \
                .intersect(wing).display(name="rib_A", severity=logging.NOTSET)
        else:
            rib = cq.Workplane().copyWorkplane(section) \
                .cylinder(radius=max(wing_bbox.ylen * 1.1, wing_bbox.zlen * 1.2) / 2, height=rib_width) \
                .intersect(wing).display(name="rib_A", severity=logging.NOTSET)
        return rib

    def construct_main_beam(self, intersect:Workplane, chord_beam_position: float, pipe_diameter: float, printer_resolution: float,
                            root_section: cq.Workplane,
                            tip_section: cq.Workplane, beam_with_pipe: bool = True) -> tuple[Workplane, Workplane]:
        logging.debug("constructing beam...")
        tip_bbox = tip_section.val().BoundingBox()
        root_bbox = root_section.val().BoundingBox()

        pipe = None
        if beam_with_pipe:
            pipe = cq.Workplane('XZ') \
                .copyWorkplane(root_section.workplane(invert=True, origin=root_bbox.center)) \
                .moveTo(root_bbox.xlen * (chord_beam_position - 1 / 2), 0) \
                .circle(pipe_diameter / 2) \
                .copyWorkplane(tip_section.workplane(invert=True, origin=tip_bbox.center)) \
                .moveTo(tip_bbox.xlen * (chord_beam_position - 1 / 2), 0) \
                .circle(pipe_diameter / 2) \
                .loft() \
                .display(name="pipe", severity=logging.NOTSET)

        beam = (cq.Workplane('XZ')
                     .copyWorkplane(root_section.workplane(invert=True, origin=root_bbox.center))
                     .moveTo(root_bbox.xlen * (chord_beam_position - 1 / 2) , 0)
                     .rect((2 * printer_resolution), root_bbox.zlen, True)
                     .copyWorkplane(tip_section.workplane(invert=True, origin=tip_bbox.center))
                     .moveTo(tip_bbox.xlen * (chord_beam_position - 1 / 2), 0)
                     .rect(2 * printer_resolution , tip_bbox.zlen, True)
                     .loft()).intersect(intersect)

        if beam_with_pipe:
            beam = (beam + pipe) \
                .display(name="beam", severity=logging.NOTSET)
        else:
            beam.display(name="beam", severity=logging.NOTSET)

        return beam, pipe

    @classmethod
    def overlap_calculator(cls, fullwing_loft: cq.Workplane, fuselage_loft: cq.Workplane) \
            -> tuple[cq.BoundBox, str, cq.Location]:
        fbbox = fuselage_loft.findSolid().BoundingBox()
        overlap = cq.Workplane('XZ').add(fullwing_loft).tag('middle').workplane(offset=fbbox.ymax).split(
            keepBottom=True) \
            .workplaneFromTagged('middle').workplane(offset=fbbox.ymin).split(keepTop=True)
        bbox = overlap.findSolid().BoundingBox()
        fus_bbox = fuselage_loft.findSolid().BoundingBox()
        wing_type = 'high'
        if (bbox.zmax - bbox.zmin) / 2 + bbox.zmin < (fus_bbox.zmax - fus_bbox.zmin) / 2 + fus_bbox.zmin:
            wing_type = 'low'
        return bbox, wing_type, overlap.findSolid().location()
