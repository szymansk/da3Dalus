import logging

from OCC.Wrapper.wrapper_utils import deprecated
from tigl3.configuration import CCPACSEnginePositions, CCPACSEnginePosition, CCPACSConfiguration
from tigl3.geometry import CCPACSTransformation, CTiglPoint, CCPACSPointAbsRel


class EngineInformation:

    def __init__(self, engine_index: int, cpacs_configuration: CCPACSConfiguration):
        self.down_thrust, self.side_thrust, self.position, \
            self.length, self.width, self.height = \
            EngineInformation._calc_motor_dimensions(engine_index=engine_index,
                                                     cpacs_configuration=cpacs_configuration)

    @classmethod
    def get_engine_down_thrust_angle(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration) -> float:
        engine_positions: CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: CCPACSTransformation = engine_position.get_transformation()
        return engine_position_transformation.get_rotation()

    @classmethod
    def get_engine_side_thrust_angle(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration) -> float:
        engine_positions: CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: CCPACSTransformation = engine_position.get_transformation()
        return engine_position_transformation.get_rotation()

    @classmethod
    def get_motor_position(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration) -> CCPACSTransformation:
        engine_positions: CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: CCPACSTransformation = engine_position.get_transformation()
        return engine_position_transformation.get_translation()

    @classmethod
    def get_motor_dimensions(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration) \
            -> tuple[float, float, float]:
        """
        :param engine_index:
        :param cpacs_configuration:
        :return: length, width, height
        """
        engine_positions: CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: CCPACSTransformation = engine_position.get_transformation()
        engine_scaling: CTiglPoint = engine_position_transformation.get_scaling()
        return engine_scaling.x, engine_scaling.y, engine_scaling.z

    @classmethod
    def _calc_motor_dimensions(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration)\
            -> tuple[float, float, CCPACSPointAbsRel, float, float, float]:
        """
        obsolete do not use
        :param engine_index:
        :param cpacs_configuration:
        :return:
        """
        engine_positions: CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(engine_index)
        engine_position_transformation: CCPACSTransformation = engine_position.get_transformation()
        rotation: CTiglPoint = engine_position_transformation.get_rotation()
        down_thrust_angle = rotation.y
        right_thrust_angle = rotation.z
        motor_position: CCPACSPointAbsRel = engine_position_transformation.get_translation()
        engine_scaling: CTiglPoint = engine_position_transformation.get_scaling()
        engine_length = engine_scaling.x
        engine_width = engine_scaling.y
        engine_height = engine_scaling.z
        return down_thrust_angle, right_thrust_angle, motor_position, engine_length, engine_width, engine_height
