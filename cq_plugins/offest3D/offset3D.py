from typing import Literal

import cadquery as cq
from OCP.BRepOffset import BRepOffset_Skin
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Tangent, GeomAbs_Intersection
from cadquery import Workplane


def offset3D(self: Workplane, offset: float, tol=1e-3, join_mode: Literal["arc", "intersection", "tangent"] = "arc",
             remove_internal_edges=True, perform_simple=True) -> Workplane:
    solid = self.findSolid()
    maker: BRepOffsetAPI_MakeOffsetShape = BRepOffsetAPI_MakeOffsetShape()

    if perform_simple:
        maker.PerformBySimple(solid.wrapped, offset)
        of_shape = maker.Shape()
    else:
        jm = GeomAbs_Arc
        if join_mode == "intersection":
            jm = GeomAbs_Tangent
        elif join_mode == "intersection":
            jm = GeomAbs_Intersection

        maker.PerformByJoin(solid.wrapped, offset, tol,
                            BRepOffset_Skin, False, False, jm,
                            remove_internal_edges)

    of_shape = maker.Shape()
    new_solid = cq.Solid(of_shape)
    shell = cq.CQ(new_solid).shells().val().fix()
    return self.newObject([cq.Solid.makeSolid(shell)])
