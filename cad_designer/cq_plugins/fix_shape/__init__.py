from cadquery import Workplane

from cad_designer.cq_plugins.fix_shape.fix_shape import fix_shape

Workplane.fix_shape = fix_shape
