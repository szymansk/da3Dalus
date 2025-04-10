from OCP.BRepBuilderAPI import BRepBuilderAPI_GTransform
from OCP.gp import gp_Mat, gp_GTrsf, gp_XYZ
from cadquery import Workplane


def _scaleXyz(self: Workplane, x_scale: float = 1.0, y_sacle: float = 1.0, z_scale: float = 1.0):
    scale = gp_Mat(x_scale, 0, 0,
                   0, y_sacle, 0,
                   0, 0, z_scale)
    aTrsf = gp_GTrsf(scale, gp_XYZ(0, 0, 0))
    aBrepTrsf = BRepBuilderAPI_GTransform(self.findSolid().wrapped, aTrsf)
    tShape = aBrepTrsf.Shape()
    return self.newObject(objlist=[tShape])
