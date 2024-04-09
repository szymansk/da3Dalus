from OCP.gp import *
from airplane.aircraft_topology.components.ComponentInformation import ComponentInformation

class ServoInformation(ComponentInformation):
    def __init__(self, height: float, width: float, length: float, lever_length: float, rot_x: float = 0.0,
                 rot_y: float = 0.0,
                 rot_z: float = 0.0, trans_x: float = 0.0, trans_y: float = 0.0, trans_z: float = 0.0):
        self.lever_length = lever_length

        self.trans_z = trans_z
        self.trans_y = trans_y
        self.trans_x = trans_x
        self.rot_z = rot_z
        self.rot_y = rot_y
        self.rot_x = rot_x
        self.length = length
        self.width = width
        self.height = height

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
