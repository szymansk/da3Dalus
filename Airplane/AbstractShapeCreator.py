import abc
import logging
from typing import Union

from cadquery import Workplane

class AbstractShapeCreator(metaclass=abc.ABCMeta):
    """
    Base class for shape creating/modifying nodes.
    """
    def __init__(self, creator_id, shapes_of_interest_keys: Union[list[str], None], loglevel=logging.FATAL):
        self.loglevel = loglevel
        self._shapes_of_interest_keys = shapes_of_interest_keys
        self.creator_id = creator_id

    @property
    def identifier(self) -> str:
        """
        This property is abstract and used in the ConstructionStepKnode. The variable, that ist used to hold the
        property should not be private (does not start with an '_'). Otherwise, it will not be de-/serialized.
        :return: identifier as name of this shape. If used several times the shape will be overwritten in future steps.
        """
        return self.creator_id
        pass

    @property
    def shapes_of_interest_keys(self) -> list[str]:
        return self._shapes_of_interest_keys

    @abc.abstractmethod
    def _create_shape(self, shapes_of_interest, input_shapes: dict[str, Workplane],
                      **kwargs) -> dict[str, Workplane]:
        """
        This method will create a shape. The shape can depend on shapes of previous steps. All previous steps
        occur in the kwargs variable. The keys are the 'identifier's and the values hold the shapes.
        :param shapes_of_interest: all shapes declared in the list of 'shapes_of_interest_keys' None values will be
        filled with shapes from the input_shapes most significant last.
        :param input_shapes: shapes created in the step before
        :param kwargs: the previously created shapes identified by their 'identifier's
        :return: a new dictionary with new shapes. the naming convention is that shapes, which have known name
        get a key like <identifier>.<known_name>, shapes which are created like a list get a key that
        corresponds to a list key that is <identifier>[#increasing_number]
        """
        pass

    def create_shape(self, input_shapes: dict[str, Workplane] = None, **kwargs) -> dict[str, Workplane]:
        shapes_of_interest = self.return_needed_shapes(shapes_needed=self.shapes_of_interest_keys,
                                                       input_shapes=input_shapes, **kwargs) \
            if self.shapes_of_interest_keys is not None else None
        # setting the module specific log-level
        actual_loglevel = logging.getLogger().getEffectiveLevel()
        if self.loglevel < actual_loglevel:
            logging.getLogger().setLevel(level=self.loglevel)
        # do the construction
        result = self._create_shape(shapes_of_interest, input_shapes, **kwargs)
        # reset to actual log-level
        logging.getLogger().setLevel(level=actual_loglevel)
        return result

    def check_if_shapes_are_available(self, needed_shapes: list[str], **kwargs) -> dict[str, Workplane]:
        """
        Check if the shapes, that are needed, have been created before and are available in kwargs.
        :param needed_shapes: list of str with shape identifiers
        :param kwargs: dictionary of keyword arguments
        :return: a dictionary with the needed_shapes
        """
        shapes = {}
        if needed_shapes is not None:
            shapes = {k: kwargs[k] for k in kwargs.keys() & needed_shapes}
            missing = {(k if k not in kwargs.keys() else None) for k in needed_shapes}  # check what is missing
            missing = [i for i in missing if i is not None]  # remove all Nones
            if len(missing) > 0:
                raise KeyError(f"shapes are missing in step '{self.identifier}': {missing}")
        return shapes

    def return_needed_shapes(self,
                             shapes_needed: list[str],
                             input_shapes: dict[str, Workplane],
                             **kwargs) -> dict[str, Workplane]:
        # for each none position of shapes_need, we take one of the input_shapes
        # we expect input shapes ordered most significant last
        len_input_shapes = 0 if input_shapes is None else len(input_shapes)
        if sum(x is None for x in shapes_needed) > len_input_shapes:
            raise KeyError(f'{self.identifier}: there are less input_shapes than shapes_needed.')
        if input_shapes is not None:
            enum = input_shapes.keys().__reversed__()
            shapes_needed = [shape_key if shape_key is not None else next(enum) for shape_key in shapes_needed]
        shapes = self.check_if_shapes_are_available(shapes_needed, **kwargs)
        return {key: shapes[key] for key in shapes_needed}
