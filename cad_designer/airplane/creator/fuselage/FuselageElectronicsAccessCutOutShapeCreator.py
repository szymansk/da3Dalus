import logging

from cadquery import Workplane
import cadquery as cq

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator

class FuselageElectronicsAccessCutOutShapeCreator(AbstractShapeCreator):
    """Creates a cutout in the fuselage for electronics access.

    Attributes:
        ribcage_factor (float): Ribcage width as a factor of fuselage width.
        length_factor (float): Cutout length as a factor of root chord.
        fuselage_loft (str): Key of the fuselage loft shape.
        full_wing_loft (str): Key of the full wing loft for dimension calculation.
        wing_position (str): Wing position on fuselage: top, middle, or bottom.
    """

    def __init__(self, creator_id: str, ribcage_factor: float, length_factor, fuselage_loft, full_wing_loft,
                 wing_position: str = None, loglevel=logging.INFO):
        """
        Creates a cutout shape for creating the access to the electronics depending on the wing position ('top',
        'middle', 'bottom').
            - width is '0.8 * ribcage_factor * fuselage_width'
            - length 'root_chord * length_factor'
        :param creator_id:
        :param ribcage_factor: the width of the enforcement cage is 'fuselage_width * ribcage_factor'
        :param length_factor: defines the length of the cutout 'root_chord * length_factor'
        :param fuselage_loft: the loft the enforcement should be designed for
        :param full_wing_loft: needed to re calculate the ribcage dimensions
        :param wing_position: ('top', 'middle', 'bottom')
        """
        self.length_factor = length_factor
        self.full_wing_loft = full_wing_loft
        self.fuselage_loft = fuselage_loft
        self.ribcage_factor = ribcage_factor
        self.wing_position = wing_position
        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage_loft, self.full_wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"creating fuselage electronics cutout for {self.fuselage_loft} --> '{self.identifier}'")

        fuselage_loft = shapes_of_interest[self.fuselage_loft]
        full_wing_loft = shapes_of_interest[self.full_wing_loft]
        wing_bbox, wing_type, center = FuselageElectronicsAccessCutOutShapeCreator.overlap_calculator(full_wing_loft, fuselage_loft)
        fus_bbox = fuselage_loft.findSolid().BoundingBox()

        if wing_type=='high':
            max_z_position = wing_bbox.zmin  # for high wing aircraft
            min_z_position = fus_bbox.zmin
        else:
            min_z_position = wing_bbox.zmax  # for low wing aircraft
            max_z_position = fus_bbox.zmax

        box_height = abs(max_z_position - min_z_position) * self.ribcage_factor
        box_width = fus_bbox.ylen * self.ribcage_factor * 0.8

        center_x = wing_bbox.center.x
        center_y = fus_bbox.ylen/2+fus_bbox.ymin
        center_z = min_z_position + box_height / 2
        start_v = cq.Vector(center_x, center_y, center_z)

        shape__hardware_cutout = cq.Workplane('XY', origin=start_v).workplane(invert=wing_type=='low')\
            .box(width=box_width, height=fus_bbox.zlen, length=wing_bbox.xlen*self.length_factor-box_width, centered=(True, True, False))\
            .faces('<X or >X').cylinder(radius=box_width/2, height=fus_bbox.zlen)\
            .display(name=self.identifier, severity=logging.DEBUG)

        return {str(self.identifier): shape__hardware_cutout}

    @classmethod
    def overlap_calculator(cls, fullwing_loft: cq.Workplane, fuselage_loft: cq.Workplane) \
            -> tuple[cq.BoundBox, str, cq.Location]:
        fbbox = fuselage_loft.findSolid().BoundingBox()
        overlap = cq.Workplane('XZ').add(fullwing_loft).tag('middle').workplane(offset=fbbox.ymax).split(keepBottom=True) \
            .workplaneFromTagged('middle').workplane(offset=fbbox.ymin).split(keepTop=True)
        bbox = overlap.findSolid().BoundingBox()
        fus_bbox = fuselage_loft.findSolid().BoundingBox()
        wing_type = 'high'
        if (bbox.zmax - bbox.zmin) / 2 + bbox.zmin < (fus_bbox.zmax - fus_bbox.zmin) / 2 + fus_bbox.zmin:
            wing_type = 'low'
        return bbox, wing_type, overlap.findSolid().location()