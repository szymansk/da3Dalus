import logging

import cadquery as cq
from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator


class FuselageShellShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 thickness: float,
                 fuselage: str = None,
                 loglevel=logging.INFO):
        self.thickness = thickness
        self.fuselage = fuselage

        super().__init__(creator_id, shapes_of_interest_keys=[self.fuselage], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"shell shape '{list(shapes_of_interest.keys())[0]}' by {self.thickness}mm --> '{self.identifier}'")

        fuselage = shape_list[0].findSolid()
        offset_shape = cq.Workplane("ZY").newObject([fuselage]).offset3D(self.thickness)
        shape = cq.Workplane("ZY").newObject([fuselage]).cut(toCut=offset_shape)\
            .display(name=f"{self.identifier}", severity=logging.DEBUG).findSolid()

        return {self.identifier: shape}
