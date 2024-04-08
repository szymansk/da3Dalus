import logging

from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator


class SimpleOffsetShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 offset: float,
                 shape: str = None,
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
