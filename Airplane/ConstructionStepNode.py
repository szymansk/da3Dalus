from typing import MutableMapping, Union
from cadquery import Workplane

from Airplane.AbstractShapeCreator import AbstractShapeCreator

class ConstructionStepNode(AbstractShapeCreator, MutableMapping):
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
        super().__init__(f"{creator.identifier}", shapes_of_interest_keys=None)

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

    def _create_shape(self, shapes_of_interest, input_shapes: dict[str, Workplane], **kwargs) \
            -> dict[str, Union[object, Workplane]]:
        """
        Executes the construction of all shapes based on the defined workflow structure.
        :param shapes_of_interest: 
        :param input_shapes: the shapes that have been constructed in the predecessor step
        :param kwargs: holding the shapes of all previous steps as a dict of shapes
        :return: a dict with all shapes that have been created up to this step
        """
        output_shapes = self.creator.create_shape(input_shapes=input_shapes, **kwargs)

        if input_shapes is None:
            _input_shapes = {}
        else:
            _input_shapes = input_shapes.copy()  # otherwise we will give a reverence down, which will be changed

        # remove existing objects
        for key in output_shapes:
            try:
                del _input_shapes[key]
            except KeyError:
                pass
        # and overwrite with new values so that the last created shapes are at the end of the dict
        _input_shapes.update(output_shapes.copy())

        kwargs.update(output_shapes.copy())
        for key in self.successors:
            kwargs.update(self.successors.get(key).create_shape(_input_shapes, **kwargs))
        # del _input_shapes  # deleting this list
        return kwargs


class ConstructionRootNode(AbstractShapeCreator, MutableMapping):
    """
    A node that is a map and holds in itself the following steps in the construction tree
    """

    def __init__(self, creator_id: str, successors=None):
        """
        :param geometry: the geometry, that is created in this node
        :param successors: all following construction steps
        """
        self.successors = {} if successors is None else successors
        self._output_shapes = None
        super().__init__(f"{creator_id}.root", shapes_of_interest_keys=None)

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

    def _create_shape(self, shapes_of_interest, input_shapes: dict[str, Workplane], **kwargs) \
            -> dict[str, Union[object, Workplane]]:
        """
        Executes the construction of all shapes based on the defined workflow structure.
        :param input_shapes: the shapes that have been constructed in the predecessor step
        :param kwargs: holding the shapes of all previous steps as a dict of shapes
        :return: a dict with all shapes that have been created up to this step
        """
        for key in self.successors:
            kwargs.update(self.successors.get(key).create_shape(input_shapes={}, **kwargs))
        return kwargs


class JSONStepNode(ConstructionStepNode):
    def __init__(self, json_file_path: str, **kwargs):
        """
        :param geometry: the geometry, that is created in this node
        :param successors: all following construction steps
        """
        import json
        from Airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder

        self.json_file_path = json_file_path
        self._to_be_injected = kwargs
        _json_file = open(self.json_file_path)
        creator: ConstructionStepNode = json.load(_json_file,
                                                  cls=GeneralJSONDecoder,
                                                  **self._to_be_injected)
        _json_file.close()
        if "successors" in kwargs.keys():
            kwargs.pop("successors")
        if "creator" in kwargs.keys():
            kwargs.pop("creator")
        super().__init__(creator=creator.creator, successors=creator.successors, **kwargs)
        pass
