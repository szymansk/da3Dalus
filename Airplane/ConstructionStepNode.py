from typing import MutableMapping

from tigl3 import geometry as tgl_geom

from Airplane.AbstractConstructionStep import AbstractConstructionStep
from Airplane.AbstractShapeCreator import AbstractShapeCreator


class ConstructionStepNode(AbstractConstructionStep, MutableMapping):
    """
    A node that is a map and holds in itself the following steps in the construction tree
    """

    def __init__(self, creator: AbstractShapeCreator, successors=None, **kwargs):
        """
        :param geometry: the geometry, that is created in this node
        :param successors: all following construction steps
        """
        self.successors = {} if successors is None else successors
        self.creator: AbstractShapeCreator = creator
        self._output_shapes = None

    def __getitem__(self, key: str):
        return self.successors[key]

    def __setitem__(self, key, value):
        self.successors[key] = value

    def __delitem__(self, key):
        del self.successors[key]

    def __len__(self):
        return len(self.successors)

    def __iter__(self):
        return iter(self.successors)

    def append(self, value) -> None:
        """
        Append a ConstructionStepNode to this map.
        :param value: ConstructionStepNode
        """
        self.update({value.creator.identifier: value})

    def construct(self, input_shapes: dict[str, tgl_geom.CNamedShape] = None, **kwargs) -> dict[str, object]:
        """
        Executes the construction of all shapes based on the defined workflow structure.
        :param input_shapes: the shapes that have been constructed in the last step
        :param kwargs: holding the shapes of the previous steps as a dict of shape lists
        (input_shapes is the last entry of this dict)
        :return: a dict with all shapes created during the workflow
        """
        self._output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)
        kwargs.update(self._output_shapes)
        output_dict = self._output_shapes
        for key in self.successors:
            output_dict.update(self.successors.get(key).construct(input_shapes=self._output_shapes, **kwargs))
        return output_dict
