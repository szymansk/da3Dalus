from typing import Optional

from OCP.gp import *
from pydantic import PositiveFloat
from pydantic import NonNegativeFloat

from cad_designer.airplane.aircraft_topology.components import Servo
from cad_designer.airplane.aircraft_topology.components.ComponentInformation import ComponentInformation


class ServoInformation(ComponentInformation):

    @property
    def length(self):
        return self.servo.length

    @length.setter
    def length(self, value):
        pass

    @property
    def width(self):
        return self.servo.width

    @width.setter
    def width(self, value):
        pass

    @property
    def height(self):
        return self.servo.height

    @height.setter
    def height(self, value):
        pass

    def __init__(self,
                 height: PositiveFloat, width: PositiveFloat, length: PositiveFloat,
                 lever_length: NonNegativeFloat,
                 rot_x: float = 0.0, rot_y: float = 0.0, rot_z: float = 0.0,
                 trans_x: float = 0.0, trans_y: float = 0.0, trans_z: float = 0.0,
                 servo: Optional[Servo] = None):
        self.lever_length = lever_length
        self.servo: Servo = servo if servo is not None \
            else Servo(length, width, height, 0, 0, 0, 0, 0, 0, 0, 0)

        self.trans_z = trans_z
        self.trans_y = trans_y
        self.trans_x = trans_x
        self.rot_z = rot_z
        self.rot_y = rot_y
        self.rot_x = rot_x

        self._corner_vecs = [gp_Vec(0.000000000, 0.000, 0),
                             gp_Vec(self.length, 0.000, 0),
                             gp_Vec(self.length, 0.000, -self.height),
                             gp_Vec(0.000000000, 0.000, -self.height),

                             gp_Vec(0.000000000, -self.width, 0),
                             gp_Vec(self.length, -self.width, 0),
                             gp_Vec(self.length, -self.width, -self.height),
                             gp_Vec(0.000000000, -self.width, -self.height)]

        super().__init__(trans_z=self.trans_z,
                         trans_y=self.trans_y,
                         trans_x=self.trans_x,
                         rot_z=self.rot_z,
                         rot_y=self.rot_y,
                         rot_x=self.rot_x,
                         length=self.length,
                         width=self.width,
                         height=self.height)
