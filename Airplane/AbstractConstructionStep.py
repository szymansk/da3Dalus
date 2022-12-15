import abc

from tigl3 import geometry as tgl_geom


class AbstractConstructionStep(metaclass=abc.ABCMeta):
    """
    This is an interface for a construction Step. A construction step can execute
    """

    @abc.abstractmethod
    def construct(self, input_shapes: list[tgl_geom.CNamedShape], **kwargs) -> list[tgl_geom.CNamedShape]:
        pass
