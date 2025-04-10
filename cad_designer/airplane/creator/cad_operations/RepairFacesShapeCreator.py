import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class RepairFacesShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    def __init__(self, creator_id: str,
                 shape: str = None,
                 repair_tool: str = None,
                 loglevel=logging.INFO):
        self.repair_tool = repair_tool
        self.shape = shape

        super().__init__(creator_id, shapes_of_interest_keys=[shape, repair_tool], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"repair shape '{list(shapes_of_interest.keys())[0]}' with {list(shapes_of_interest.keys())[1]} --> '{self.identifier}'")

        faces = shape_list[1].faces()
        shape = shape_list[0].add(faces).combine(glue=True, tol=0.05).display(name=self.identifier, severity=logging.DEBUG)

        return {self.identifier: shape}
