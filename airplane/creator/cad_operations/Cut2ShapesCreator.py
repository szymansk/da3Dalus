import logging

from cadquery import Workplane

from airplane.AbstractShapeCreator import AbstractShapeCreator


class Cut2ShapesCreator(AbstractShapeCreator):
    """
    Cut the subtrahend from the minuend (minuend - subtrahend = new_shape).
    """

    def __init__(self, creator_id: str,
                 minuend: str = None,
                 subtrahend: str = None, loglevel=logging.INFO):
        self.minuend = minuend
        self.subtrahend = subtrahend
        super().__init__(creator_id, shapes_of_interest_keys=[self.minuend, self.subtrahend], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(
            f"cutting shapes '{list(shapes_of_interest.keys())[0]}' - '{list(shapes_of_interest.keys())[1]}' "
            f"--> '{self.identifier}'")

        shape__minuend = shape_list[0]
        shape__subtrahend = shape_list[1]
        try:
            cut_shape = shape__minuend.cut(shape__subtrahend.solids().val(), clean=True).combine(glue=True)
        except:
            logging.error(
                f"FAILED: cutting shapes '{list(shapes_of_interest.keys())[0]}' - "
                f"'{list(shapes_of_interest.keys())[1]}' --> '{self.identifier}'")
            cut_shape = shape__minuend

        cut_shape.display(name=self.identifier, severity=logging.DEBUG)
        return {self.identifier: cut_shape}
