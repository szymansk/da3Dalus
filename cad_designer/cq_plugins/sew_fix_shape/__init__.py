from cadquery import Workplane
from cad_designer.cq_plugins.sew_fix_shape.sew_fix_shape import sewAndFixShape
Workplane.sewAndFix = sewAndFixShape
