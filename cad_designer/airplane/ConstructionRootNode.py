from __future__ import annotations

from typing import MutableMapping
from collections import OrderedDict

from cadquery import Workplane

from cad_designer.airplane import ConstructionStepNode
from cad_designer.airplane.AbstractShapeCreator import AbstractShapeCreator


class ConstructionRootNode(AbstractShapeCreator, MutableMapping):
    """
    A node that is a map and holds in itself the following steps in the construction tree
    """

    def __init__(self, creator_id: str, successors: OrderedDict[str, ConstructionStepNode] = None):
        """
        :param successors: all following construction steps
        """
        self.successors = OrderedDict() if successors is None else successors
        self._output_shapes = None
        super().__init__(f"{creator_id}.root", shapes_of_interest_keys=None)

    def __getitem__(self, key: str):
        return self.successors[key]

    def __setitem__(self, key: str, value):
        self.successors[key] = value

    def __delitem__(self, key: str):
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

    def _create_shape(self, shapes_of_interest: list[str] | None, input_shapes: dict[str, Workplane], **kwargs) \
            -> dict[str, object | Workplane]:
        """
        Executes the construction of all shapes based on the defined workflow structure.
        :param input_shapes: the shapes that have been constructed in the predecessor step
        :param kwargs: holding the shapes of all previous steps as a dict of shapes
        :return: a dict with all shapes that have been created up to this step
        """
        for key in self.successors:
            kwargs.update(self.successors.get(key).create_shape(input_shapes={}, **kwargs))
        return kwargs
