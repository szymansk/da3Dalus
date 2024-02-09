from cadquery import Workplane

from cq_plugins.fix_shape import fix_shape

Workplane.fix_shape = fix_shape
