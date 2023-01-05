import abc
import logging
from typing import Union

from OCC.Wrapper.wrapper_utils import deprecated
from tigl3.configuration import CCPACSEnginePositions, CCPACSEnginePosition, CCPACSConfiguration
from tigl3.geometry import CCPACSTransformation, CTiglPoint, CCPACSPointAbsRel

from Airplane.aircraft_topology.ComponentInformation import ComponentInformation


class Position:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def get_x(self):
        return self.x

    def get_y(self):
        return self.y

    def get_z(self):
        return self.z


class EngineInformation(ComponentInformation):

    def __init__(self, down_thrust: float, side_thrust: float, position: Union[CCPACSPointAbsRel, Position],
                 length: float, width: float, height: float, screw_hole_circle: float, mount_box_length: float,
                 screw_din_diameter: float, screw_length: float):
        self.engine_screw_length = screw_length
        self.engine_screw_din_diameter = screw_din_diameter
        self.engine_mount_box_length = mount_box_length
        self.engine_screw_hole_circle = screw_hole_circle
        self.height = height
        self.width = width
        self.length = length
        self.position = position
        self.side_thrust = side_thrust
        self.down_thrust = down_thrust

        super().__init__(trans_z=self.position.get_z(),
                         trans_y=self.position.get_y(),
                         trans_x=self.position.get_x(),
                         rot_z=self.side_thrust,
                         rot_y=self.down_thrust,
                         rot_x=0.0,
                         length=self.length,
                         width=self.width,
                         height=self.height)

class CPACSEngineInformation(EngineInformation):

    def __init__(self, engine_index: int, cpacs_configuration: CCPACSConfiguration, engine_screw_hole_circle,
                 engine_mount_box_length, engine_screw_din_diameter, engine_screw_length):
        down_thrust_angle, right_thrust_angle, motor_position, engine_length, engine_width, engine_height = \
            CPACSEngineInformation._calc_motor_dimensions(engine_index, cpacs_configuration)
        super().__init__(down_thrust_angle, right_thrust_angle, motor_position, engine_length, engine_width,
                         engine_height, engine_screw_hole_circle, engine_mount_box_length, engine_screw_din_diameter,
                         engine_screw_length)

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
    def _calc_motor_dimensions(cls, engine_index: int, cpacs_configuration: CCPACSConfiguration) \
            -> tuple[float, float, Union[CCPACSPointAbsRel, Position], float, float, float]:
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
