import tigl3.geometry as tgl_geom

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ReinforcementPipeFactory import ReinforcementPipeFactory
from Airplane.Wing.WingFactory import WingFactory
from Airplane.Wing.WingRibFactory import WingRibFactory
from Airplane.aircraft_topology.WingInformation import WingInformation
from Extra.BooleanOperationsForLists import BooleanCADOperation

from Extra.ConstructionStepsViewer import *


class WingRibCageCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_loft: str, wing_index: int, rib_distance, cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None, loglevel=logging.INFO):
        self.rib_distance = rib_distance
        self._wing_information = wing_information
        self.wing_loft = wing_loft
        self.wing_index = wing_index
        self._cpacs_configuration = cpacs_configuration
        super().__init__(creator_id, shapes_of_interest_keys=[self.wing_loft], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, tgl_geom.CNamedShape],
                      input_shapes: dict[str, tgl_geom.CNamedShape],
                      **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(
            f"wing rib cage '{', '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        shape = WingRibFactory.create_ribcage(shapes_of_interest[self.wing_loft],
                                              wing_information=self._wing_information[self.wing_index],
                                              rib_distance=self.rib_distance)

        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class ReinforcementPipesCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, wing_index: int, pipe_diameter: float, wall_thickness: float,
                 pipe_position: list[int], wing_information: dict[int, WingInformation] = None, loglevel=logging.INFO):
        self.pipe_position = pipe_position
        self.wall_thickness = wall_thickness
        self.pipe_diameter = pipe_diameter
        self._wing_information = wing_information
        self.wing_index = wing_index
        super().__init__(creator_id, shapes_of_interest_keys=None, loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, tgl_geom.CNamedShape],
                      input_shapes: dict[str, tgl_geom.CNamedShape],
                      **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(
            f"wing pipes  --> '{self.identifier}'")

        # Pipes for reinforcement rod, radius is given by the chosen carbon fiber stick, thickness is given by the
        # used printing configuration. Quantity has been chosen to ensure tha the pipes
        # are at closer to the front edge of the wing.
        shape = ReinforcementPipeFactory.create_reinforcemente_pipe_wing(self._wing_information[self.wing_index],
                                                                         radius=self.pipe_diameter / 2,
                                                                         thickness=self.wall_thickness,
                                                                         pipe_position=self.pipe_position)

        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}


class WingRestCreator(AbstractShapeCreator):
    def __init__(self,
                 creator_id: str,
                 wing_loft: str,
                 reinforcement: str,
                 pipes: str,
                 wing_index: int,
                 cpacs_configuration=None,
                 wing_information: dict[int, WingInformation] = None,
                 loglevel=logging.INFO):
        self.pipes = pipes
        self._wing_information = wing_information
        self.wing_loft = wing_loft
        self.wing_index = wing_index
        self.reinforcement = reinforcement
        self._cpacs_configuration = cpacs_configuration
        super().__init__(creator_id, shapes_of_interest_keys=[self.wing_loft, reinforcement, pipes], loglevel=loglevel)

    def _create_shape(self, shapes_of_interest: dict[str, tgl_geom.CNamedShape],
                      input_shapes: dict[str, tgl_geom.CNamedShape],
                      **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(
            f"wing rest '{', '.join(shapes_of_interest.keys())}' --> '{self.identifier}'")
        factory = WingFactory(self._cpacs_configuration, self.wing_index)
        shape, _ = factory.create_wing_with_inbuilt_servo(shapes_of_interest[self.reinforcement],
                                                          shapes_of_interest[self.pipes],
                                                          self._wing_information[self.wing_index])

        ConstructionStepsViewer.instance().display_this_shape(shape, logging.DEBUG, msg=f"{self.identifier}")

        return {self.identifier: shape}

