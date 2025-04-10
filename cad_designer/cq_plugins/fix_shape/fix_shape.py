from OCP.ShapeFix import ShapeFix_Shape
from cadquery import Workplane, Solid

from cadquery.occ_impl.shapes import Solid

def fix_shape(self: Workplane) -> Workplane:
    fix_shape = ShapeFix_Shape(self.findSolid().wrapped)
    fix_shape.SetPrecision(1e-3)
    fix_shape.SetMaxTolerance(1e-1)
    fix_shape.SetMinTolerance(1e-4)
    fix_shape.Perform()
    solid = Solid(fix_shape.Shape())
    return self.newObject(objlist=[solid])
