import cadquery as cq

from cad_designer.cq_plugins.scaleXyz.scaleXyz import _scaleXyz

cq.Workplane.scaleXyz = _scaleXyz