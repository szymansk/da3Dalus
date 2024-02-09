import cadquery as cq

from cq_plugins.scaleXyz.scaleXyz import _scaleXyz

cq.Workplane.scaleXyz = _scaleXyz