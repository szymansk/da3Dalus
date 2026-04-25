import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator
from cad_designer.airplane.types import CreatorId, ShapeId

class SimpleOffsetShapeCreator(AbstractShapeCreator):
    """Creates a uniformly offset version of a shape, enlarging or shrinking it.

    Attributes:
        offset (float): Offset distance in mm (positive = enlarge, negative = shrink).
        shape (str): Key of the shape to offset.

    Returns:
        {id} (Workplane): Shape offset by the specified distance.
    """

    suggested_creator_id = "offset.{shape}"

    def __init__(self, creator_id: CreatorId,
                 offset: float,
                 shape: ShapeId = None,
                 loglevel=logging.INFO):
        self.offset = offset
        self.shape = shape

        super().__init__(creator_id, shapes_of_interest_keys=[shape], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"offset shape '{list(shapes_of_interest.keys())[0]}' by {self.offset}mm --> '{self.identifier}'")

        shape: Workplane = shape_list[0].offset3D(self.offset, perform_simple=True).display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: shape}
