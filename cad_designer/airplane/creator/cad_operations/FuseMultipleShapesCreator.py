import logging

from cadquery import Workplane

from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class FuseMultipleShapesCreator(AbstractShapeCreator):
    """Fuses multiple shapes into a single solid using boolean union.

    Attributes:
        shapes (list[str]): List of shape keys to fuse together.

    Returns:
        {id} (Workplane): Boolean union of all input shapes.
    """

    def __init__(self, creator_id: str, shapes: list[str], loglevel=logging.INFO):
        self.shapes = shapes
        super().__init__(creator_id, shapes_of_interest_keys=shapes, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, Workplane],
                      input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        shape_list = list(shapes_of_interest.values())
        logging.info(f"fusing shapes '{' + '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")

        fused_shape = shape_list[0]
        for shape in shape_list[1:]:
            fused_shape = fused_shape.union(toUnion=shape)
        fused_shape = fused_shape.combine()
        fused_shape.display(self.identifier, logging.DEBUG)
        return {self.identifier: fused_shape}
