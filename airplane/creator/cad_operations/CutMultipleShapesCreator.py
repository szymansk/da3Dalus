import logging

from cadquery import Workplane

from airplane.AbstractShapeCreator import AbstractShapeCreator


class CutMultipleShapesCreator(AbstractShapeCreator):
    """
    Fusing shape B with shape A.
    """

    def __init__(self, creator_id: str, subtrahends: list[str], minuend: str = None, loglevel=logging.INFO):
        self.subtrahends = subtrahends
        self.minuend = minuend
        soik = [self.minuend] + self.subtrahends
        super().__init__(creator_id, shapes_of_interest_keys=soik, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        logging.info(f"cutting shapes '{' - '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        subtrahends_shapes = [shapes_of_interest[key] for key in self.subtrahends]

        shape = list(shapes_of_interest.values())[0]
        for subtrahend in subtrahends_shapes:
            shape = shape.cut(subtrahend, clean=True)
            shape.display(name=f"{self.identifier}", severity=logging.NOTSET)
        new_shape = shape.combine(glue=True)

        new_shape.display(name=f"{self.identifier}", severity=logging.DEBUG)
        return {self.identifier: new_shape}
