from cadquery import Workplane

from cq_plugins.sew_fix_shape.sew_fix_shape import sewAndFixShape

Workplane.sewAndFix = sewAndFixShape
