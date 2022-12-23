import abc

from tigl3 import geometry as tgl_geom


class AbstractShapeCreator(metaclass=abc.ABCMeta):
    """
    Base class for shape creating/modifying nodes.
    """

    @property
    @abc.abstractmethod
    def identifier(self):
        """
        This property is abstract and used in the ConstructionStepKnode. The variable, that ist used to hold the
        property should not be private (does not start with an '_'). Otherwise, it will not be de-/serialized.
        :return: identifier as name of this shape. If used several times the shape will be overwritten in future steps.
        """
        pass

    @abc.abstractmethod
    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        """
        This method will create a shape. The shape can depend on shapes of previous steps. All previous steps
        occur in the kwargs variable. The key are the 'identifier's and the values hold the shapes.
        :param input_shapes: shapes created in the step before
        :param kwargs: the previously created shapes identified by their 'identifier's
        :return: a new dictionary with new shapes. the naming convention is that shapes, which have known name
        get a key like <identifier>.<known_name>, shapes which are created like a list get a key that
        corresponds to a list key that is <identifier>[#increasing_number]
        """
        pass

    @classmethod
    def check_if_shapes_are_available(cls, needed_shapes: list[str], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
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
                raise KeyError(f'shapes are missing: {missing}')
        return shapes

    @classmethod
    def return_needed_shapes(cls,
                             shapes_needed: list[str],
                             input_shapes: dict[str, tgl_geom.CNamedShape],
                             **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        # for each none position of shapes_need, we take one of the input_shapes
        # we expect input shapes ordered most significant last
        if sum(x is None for x in shapes_needed) > len(input_shapes):
            raise KeyError('there are less input_shapes than shapes_needed.')
        enum = input_shapes.keys().__iter__()
        needed_shapes = [shape_key if shape_key is not None else next(enum) for i, shape_key in enumerate(shapes_needed)]
        shapes = AbstractShapeCreator.check_if_shapes_are_available(needed_shapes, **kwargs)
        return {key: shapes[key] for key in needed_shapes}
