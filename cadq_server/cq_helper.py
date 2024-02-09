import math
import random
import uuid
from typing import Literal

import cadquery as cq
import logging

from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_GTransform
from OCP.BRepOffset import BRepOffset_Skin
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Tangent, GeomAbs_Intersection
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from OCP.gp import gp_GTrsf, gp_Mat, gp_XYZ
from cadquery import Workplane, Shell, Solid

from cadq_server.cadq_server_connector import CQServerConnector

def _display(self: Workplane, name: str = "", color: cq.Color = cq.Color("gold"), severity: int = logging.NOTSET,
             url: str = "http://cq-server:5000/json") -> Workplane:
    if severity >= logging.root.level:
        _display._connector = _display._connector if _display._connector is not None else CQServerConnector(url=url)
        _display._connector.render(name=name, cq_model=self)
    return self

_display._connector = None
Workplane.display = _display


def sewAndFixShape(self: Workplane) -> Workplane:
    sewing_tool = BRepBuilderAPI_Sewing(1e-2)
    sewing_tool.Load(self.findSolid().wrapped)
    sewing_tool.Perform()
    sewed_shape = sewing_tool.SewedShape()

    exp_shell = TopExp_Explorer()
    make_solid = BRepBuilderAPI_MakeSolid()
    # make_solid = TopOpeBRepBuild_ShellToSolid()

    exp_shell.Init(sewed_shape, TopAbs_SHELL)
    while exp_shell.More():
        shell = Shell(exp_shell.Current()).wrapped
        make_solid.Add(shell)
        exp_shell.Next()

    solid_shape = make_solid.Solid()

    fix_shape = ShapeFix_Shape(solid_shape)
    fix_shape.SetPrecision(1e-3)
    fix_shape.SetMaxTolerance(1)
    fix_shape.SetMinTolerance(0.01)
    fix_shape.Perform()
    solid = Solid(fix_shape.Shape())
    return self.newObject(objlist=[solid])


Workplane.sewAndFix = sewAndFixShape

def fix_shape(self: Workplane) -> Workplane:
    fix_shape = ShapeFix_Shape(self.findSolid().wrapped)
    fix_shape.SetPrecision(1e-3)
    fix_shape.SetMaxTolerance(1)
    fix_shape.SetMinTolerance(0.01)
    fix_shape.Perform()
    solid = Solid(fix_shape.Shape())
    return self.newObject(objlist=[solid])

Workplane.fix_shape = fix_shape

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


Workplane.offset3D = offset3D


def scaleXyz(self: Workplane, x_scale: float = 1.0, y_sacle: float = 1.0, z_scale: float = 1.0):
    scale = gp_Mat(x_scale, 0, 0,
                   0, y_sacle, 0,
                   0, 0, z_scale)
    aTrsf = gp_GTrsf(scale, gp_XYZ(0, 0, 0))
    aBrepTrsf = BRepBuilderAPI_GTransform(self.findSolid().wrapped, aTrsf)
    tShape = aBrepTrsf.Shape()
    return self.newObject(objlist=[tShape])


Workplane.scaleXyz = scaleXyz

