from OCP.gp import *
from pydantic import PositiveFloat

gp_DX: gp_Dir = gp_Dir(gp_XYZ(1, 0, 0))
gp_DY: gp_Dir = gp_Dir(gp_XYZ(0, 1, 0))
gp_DZ: gp_Dir = gp_Dir(gp_XYZ(0, 0, 1))

class ComponentInformation:

    def __init__(self, height: PositiveFloat, width: PositiveFloat, length: PositiveFloat, rot_x: float = 0.0, rot_y: float = 0.0,
                 rot_z: float = 0.0, trans_x: float = 0.0, trans_y: float = 0.0, trans_z: float = 0.0):

        self.trans_z = trans_z
        self.trans_y = trans_y
        self.trans_x = trans_x
        self.rot_z = rot_z
        self.rot_y = rot_y
        self.rot_x = rot_x
        self.length = length
        self.width = width
        self.height = height

    def get_corner_point(self) -> gp_Pnt:
        return gp_Pnt(self.trans_x, self.trans_y, self.trans_z)

    def get_middle_point(self) -> gp_Vec:
        middle = gp_Vec(self.trans_x + self.length/2, self.trans_y - self.width/2, self.trans_z - self.length/2)
        middle.Rotate(gp_Ax1(self.get_corner_point(), gp_DX), self.rot_x)
        middle.Rotate(gp_Ax1(self.get_corner_point(), gp_DY), self.rot_y)
        middle.Rotate(gp_Ax1(self.get_corner_point(), gp_DZ), self.rot_z)
        return middle

    def get_z_axis(self) -> gp_Dir:
        z = gp_DZ
        z.Rotate(gp_Ax1(self.get_corner_point(), gp_DX), self.rot_x)
        z.Rotate(gp_Ax1(self.get_corner_point(), gp_DY), self.rot_y)
        z.Rotate(gp_Ax1(self.get_corner_point(), gp_DZ), self.rot_z)
        return z