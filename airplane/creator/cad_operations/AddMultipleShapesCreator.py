import logging

from cadquery import Workplane

from airplane.AbstractShapeCreator import AbstractShapeCreator

class AddMultipleShapesCreator(AbstractShapeCreator):
    """
    Add shape B to shape A. This is not a fuse operation.
    """

    def __init__(self, creator_id: str, shapes: list[str], loglevel=logging.INFO):
        self.shapes = shapes
        super().__init__(creator_id, shapes_of_interest_keys=shapes, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"adding shapes '{' + '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")

        shape = shape_list[0]
        for shp in shape_list[1:]:
            shape.add(shp)
        _shape = shape.combine()
        _shape = shape.combine() # I am not sure, why this only works after the second call...

        _shape.display(self.identifier, logging.DEBUG)
        return {self.identifier: _shape}

