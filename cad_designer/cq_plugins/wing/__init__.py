from cad_designer.cq_plugins.wing.airfoil import airfoil
from cad_designer.cq_plugins.wing.wing_root_segment import wing_root_segment
from cad_designer.cq_plugins.wing.wing_segment import wing_segment

import cadquery as cq

cq.Workplane.airfoil = airfoil
cq.Workplane.wing_root_segment = wing_root_segment
cq.Workplane.wing_segment = wing_segment
