import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class Intersect2ShapesCreator(AbstractShapeCreator):
    """Computes the boolean intersection of two shapes, keeping only overlapping volume.

    Attributes:
        shape_a (str): Key of the first shape.
        shape_b (str): Key of the second shape to intersect with.

    Returns:
        {id} (Workplane): Boolean intersection of shape_a and shape_b.
    """

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None, loglevel=logging.INFO):
        self.shape_a = shape_a
        self.shape_b = shape_b
        super().__init__(creator_id, shapes_of_interest_keys=[self.shape_a, self.shape_b], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"intersecting shapes '{list(shapes_of_interest.keys())[0]}' / '{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")

        shape__a = shape_list[0]
        shape__b = shape_list[1]
        new_shape = shape__a.intersect(shape__b).combine(glue=True).display(name=self.identifier, severity=logging.DEBUG)

        return {self.identifier: new_shape}
