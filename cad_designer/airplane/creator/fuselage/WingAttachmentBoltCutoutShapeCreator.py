import logging

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import ShapeId


class WingAttachmentBoltCutoutShapeCreator(AbstractShapeCreator):
    """Creates bolt cutouts along the roll-axis for wing attachment rubber bands.

    Attributes:
        fuselage_loft (str): Key of the fuselage loft shape.
        full_wing_loft (str): Key of the full wing loft for overlap calculation.
        bolt_diameter (float): Diameter of the attachment bolts in mm.

    Returns:
        {id} (Workplane): Cylindrical bolt cutouts for wing attachment.
    """

    suggested_creator_id = "bolt_cutout"

    def __init__(self, creator_id: str, fuselage_loft: ShapeId, full_wing_loft: ShapeId, bolt_diameter: float, loglevel=logging.INFO):
        self.bolt_diameter = bolt_diameter
        self.full_wing_loft = full_wing_loft
        self.fuselage_loft = fuselage_loft
        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage_loft, self.full_wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating wing attachment bolts --> '{self.identifier}'")
        fuselage_loft = shapes_of_interest[self.fuselage_loft]
        fullwing_loft = shapes_of_interest[self.full_wing_loft]

        bbox, wing_type, _ = self.overlap_calculator(fullwing_loft, fuselage_loft)

        bolt_z_position = bbox.zmin  if wing_type == 'high' else bbox.zmax

        bolt_front = cq.Workplane('XZ').moveTo(bbox.xmin, bolt_z_position)\
            .cylinder(height=bbox.ylen*1.1, radius=self.bolt_diameter/2, direct=cq.Vector(0, 0, 1))
        bolt_back = cq.Workplane('XZ').moveTo(bbox.xmax, bolt_z_position)\
            .cylinder(height=bbox.ylen*1.1, radius=self.bolt_diameter/2, direct=cq.Vector(0, 0, 1)).add(bolt_front)\
            .display(name=self.identifier, severity=logging.DEBUG)

        return {str(self.identifier): bolt_back}

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
