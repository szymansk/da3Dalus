import logging

import numpy
from cadquery import Workplane
import cadquery as cq

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator

class FuselageWingSupportShapeCreator(AbstractShapeCreator):
    """Creates wing support using vertical cube-shaped ribs inside the fuselage.

    Attributes:
        rib_quantity (int): Number of support ribs to create.
        rib_width (float): Width of each support rib in mm.
        rib_height_factor (float): Factor of overlap height used for rib height.
        rib_z_offset (float): Vertical offset of the rib center in mm.
        fuselage_loft (str): Key of the fuselage loft shape.
        full_wing_loft (str): Key of the full wing loft for overlap calculation.

    Returns:
        {id} (Workplane): Wing support ribs inside the fuselage.
    """

    suggested_creator_id = "wing_support"
    def __init__(self, creator_id: str, rib_quantity: int, rib_width: float, rib_height_factor: float, rib_z_offset,
                 fuselage_loft: str, full_wing_loft, loglevel=logging.INFO):
        self.rib_z_offset = rib_z_offset
        self.full_wing_loft = full_wing_loft
        self.fuselage_loft = fuselage_loft
        self.rib_quantity: int = rib_quantity
        self.rib_width: float = rib_width
        self.rib_height_factor: float = rib_height_factor
        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage_loft, self.full_wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(
            f"creating wing support reinforcement for '{self.full_wing_loft}' with '{self.fuselage_loft}' --> '{self.identifier}'")
        fuselage_loft = shapes_of_interest[self.fuselage_loft]
        full_wing_loft = shapes_of_interest[self.full_wing_loft]
        overlap, wing_type = FuselageWingSupportShapeCreator.overlap_calculator(full_wing_loft, fuselage_loft)

        step = overlap.ylen/(self.rib_quantity-1)
        ass = cq.Assembly()
        origin = overlap.center
        height = overlap.zlen*self.rib_height_factor

        if wing_type == 'low':
            origin.z = overlap.zmin + height/2 + self.rib_z_offset
            for y_offset in numpy.linspace(overlap.ymin, overlap.ymax, num=self.rib_quantity):
                rib = cq.Workplane('XZ', origin=origin).workplane(offset=y_offset-self.rib_width/2)\
                    .sketch().trapezoid(overlap.xlen + 2*height, height, 45).finalize().extrude(self.rib_width)
                ass.add(rib)
        else:
            origin.z = overlap.zmax - height/2 + self.rib_z_offset
            for y_offset in numpy.linspace(overlap.ymin, overlap.ymax, num=self.rib_quantity):
                rib = cq.Workplane('XZ', origin=origin).workplane(offset=y_offset-self.rib_width/2)\
                    .sketch().trapezoid(overlap.xlen + 2*height, height, 45, angle=180).finalize().extrude(self.rib_width)
                ass.add(rib)

        shape__wing_support = cq.Workplane(ass.toCompound()) \
            .display(name=self.identifier, severity=logging.DEBUG)

        return {str(self.identifier): shape__wing_support}

    @classmethod
    def overlap_calculator(cls, fullwing_loft: cq.Workplane, fuselage_loft: cq.Workplane) \
            -> tuple[cq.BoundBox, str]:
        fus_bbox = fuselage_loft.findSolid().BoundingBox(0)
        overlap = cq.Workplane('XZ', origin=cq.Vector(0, 0, 0)).add(fullwing_loft).tag('middle')\
            .workplane(offset=fus_bbox.ymax, origin=cq.Vector(0, 0, 0)).split(keepBottom=True) \
            .workplaneFromTagged('middle').workplane(offset=fus_bbox.ymin, origin=cq.Vector(0, 0, 0))\
            .split(keepTop=True)
        wing_bbox = overlap.findSolid().BoundingBox()

        # cadquery behaves wired so I cut it off
        cut_off = cq.Workplane('YZ').workplane(offset=wing_bbox.xmax)\
            .box(fus_bbox.zlen*2, fus_bbox.ylen * 2, fus_bbox.xlen, centered=(True, True, False))
        fuselage_loft = fuselage_loft.cut(cut_off)
        cut_off = cq.Workplane('YZ').workplane(offset=-wing_bbox.xmin, invert=True)\
            .box(fus_bbox.zlen*2, fus_bbox.ylen * 2, fus_bbox.xlen, centered=(True, True, False))
        fuselage_loft = fuselage_loft.cut(cut_off)

        fus_bbox = fuselage_loft.findSolid().BoundingBox()

        overlap = cq.Workplane('XZ', origin=cq.Vector(0, 0, 0)).add(fullwing_loft).tag('middle_1')\
            .workplane(offset=fus_bbox.ymax, origin=cq.Vector(0, 0, 0)).split(keepBottom=True) \
            .workplaneFromTagged('middle_1').workplane(offset=fus_bbox.ymin, origin=cq.Vector(0,0,0))\
            .split(keepTop=True)
        bbox = overlap.findSolid().BoundingBox()

        overlap.display(name="overlap")

        wing_type = 'high'
        if (bbox.zmax - bbox.zmin) / 2 + bbox.zmin < (fus_bbox.zmax - fus_bbox.zmin) / 2 + fus_bbox.zmin:
            wing_type = 'low'

        return bbox, wing_type