import abc
from cadquery import Workplane

class AbstractConstructionStep(metaclass=abc.ABCMeta):
    """
    This is an interface for a construction Step. A construction step can execute
    """

    @abc.abstractmethod
    def construct(self, input_shapes: list[Workplane], **kwargs) -> list[Workplane]:
        pass
