import logging

import cadquery as cq
from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class Fuse2ShapesCreator(AbstractShapeCreator):
    """Fuses two shapes into a single solid using boolean union.

    Attributes:
        shape_a (str): Key of the first shape (base).
        shape_b (str): Key of the second shape to fuse into shape_a.

    Returns:
        {id} (Workplane): Boolean union of shape_a and shape_b.
    """

    suggested_creator_id = "fuse.{shape_a}.{shape_b}"

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None, loglevel=logging.INFO):
        self.shape_a = shape_a
        self.shape_b = shape_b
        super().__init__(creator_id, shapes_of_interest_keys=[self.shape_a, self.shape_b], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"fusing shapes '{list(shapes_of_interest.keys())[0]}' + '{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")
        shape_list = [sh if isinstance(sh, cq.Workplane) else cq.Workplane(obj=sh) for sh in shape_list]

        fused_shape = shape_list[0].union(toUnion=shape_list[1])

        fused_shape.display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: fused_shape}
