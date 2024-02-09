import math
import random
import uuid
from typing import Literal
import numpy as np
from numpy.linalg import norm

import cadquery as cq
import logging

from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid, BRepBuilderAPI_GTransform
from OCP.BRepOffset import BRepOffset_Skin
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
from OCP.BRepTools import BRepTools_ReShape
from OCP.GeomAbs import GeomAbs_Arc, GeomAbs_Tangent, GeomAbs_Intersection
from OCP.ShapeFix import ShapeFix_Shape
from OCP.StdFail import StdFail_NotDone
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Shape, TopoDS_Face, TopoDS_Solid
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


def airfoil(self: cq.Workplane, selig_file: str, chord: float, offset: float = 0, forConstruction: bool = False):
    file = open(selig_file, "r")
    point_list = []
    for line_num, line in enumerate(file):
        line: str = line
        if line_num < 1:
            pass
        else:
            tokens = [n for n in line.strip().split(" ") if n != ""]
            tok_y = float(tokens[1])
            tok_x = float(tokens[0])
            point_list.append((tok_x, tok_y))

    if offset == 0:
        scaled_point_list = [(p[0] * chord, p[1] * chord) for p in point_list]
    else:

        points = [(point_list[i - 1], point_list[i], point_list[(i + 1) % len(point_list)]) for i in range(len(point_list))]

        # (norm((np.array(p[0]) - np.array(p[1]))) * (np.array(p[2]) - np.array(p[1])) + norm((np.array(p[2]) - np.array(p[1]))) * (np.array(p[0]) - np.array(p[1]))) / (norm((np.array(p[2]) - np.array(p[1]))) + norm((np.array(p[0]) - np.array(p[1]))))
        # a = (np.array(p[2]) - np.array(p[1]))
        # b = (np.array(p[0]) - np.array(p[1]))
        correction_vecs = [  (norm((np.array(p[0]) - np.array(p[1]))) * (np.array(p[2]) - np.array(p[1])) + norm((np.array(p[2]) - np.array(p[1]))) * (np.array(p[0]) - np.array(p[1]))) / (norm((np.array(p[2]) - np.array(p[1]))) + norm((np.array(p[0]) - np.array(p[1])))) for p in points]
        correction_vecs_norm = [cv / norm(cv) for cv in correction_vecs]
        correction_vecs_norm_tup = [ (cv[0], cv[1]) for cv in correction_vecs_norm]

        offset_point_list = [(point_list[i][0] * chord + offset * correction_vecs_norm_tup[i][0],
          point_list[i][1] * chord + offset * correction_vecs_norm_tup[i][1]) for i in range(len(point_list))]

        ## remove the crossing at the wings tail edge
        # 1. simple solution
        offset_point_list_copy = offset_point_list.copy()
        for i in range(len(offset_point_list)):
            if offset_point_list[i][1] <= offset_point_list[-i-1][1]:
                del offset_point_list_copy[0]
                del offset_point_list_copy[-1]
            else:
                break

    file.close()
    plane = self.plane
    new_plane = cq.Plane(xDir=plane.xDir, origin=(0, 0, 0), normal=plane.zDir)
    shape = (cq.Workplane(inPlane=new_plane)
             .splineApprox(points=scaled_point_list if offset == 0 else offset_point_list_copy,
                           forConstruction=forConstruction,
                           tol=1e-3).close()
             .val())
    trans_shape = shape.translate(plane.origin)

    return self.newObject([trans_shape]).toPending()


cq.Workplane.airfoil = airfoil

from typing import Literal


def wing_root_segment(self: cq.Workplane, root_airfoil: str,
                      root_chord: float, tip_chord: float, length: float,
                      sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                      root_incidence: float = 0, tip_incidence: float = 0,
                      root_dihedral: float = 0, tip_dihedral: float = 0,
                      tip_airfoil: str = None,
                      offset: float = 0):
    tip_airfoil = tip_airfoil if tip_airfoil is not None else root_airfoil
    if sweep_mode == "angle":
        e = length
        b = e / math.cos(math.radians(sweep))
        sweep = math.sqrt(b * b - e * e)

    root_plane = self.plane.rotated((root_dihedral, 0, -root_incidence))
    airfoil_root = (cq.Workplane(root_plane).airfoil(root_airfoil, root_chord, offset=offset))
    tip_plane = (airfoil_root.workplane(offset=-length, origin=(sweep, 0, 0))
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    airfoil_tip = (airfoil_root.copyWorkplane(cq.Workplane(tip_plane))
                   .airfoil(tip_airfoil, tip_chord, offset=offset))
    wing = airfoil_tip.loft(combine='a')  # ruled=True --> airfoils must have same number of points
    
    return wing.newObject([tip_plane.location, airfoil_tip.val(), wing.val()])

cq.Workplane.wing_root_segment = wing_root_segment


def wing_segment(self: cq.Workplane, tip_airfoil: str, tip_chord: float, length: float,
                 sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                 tip_incidence: float = 0, tip_dihedral: float = 0, offset: float = 0):
    airfoil_root = self
    airfoil_root.ctx.pendingWires = [self.vals()[1]]
    root_plane = airfoil_root.plane
    tip_origin = root_plane.origin
    if sweep_mode == "distance":
        tip_origin.x = tip_origin.x + sweep
    else:
        e = length
        b = e / math.cos(math.radians(sweep))
        sweep_by_ang = math.sqrt(b * b - e * e)
        tip_origin.x = tip_origin.x + sweep_by_ang

    tip_plane = (cq.Workplane().copyWorkplane(airfoil_root).workplane(offset=-length, origin=tip_origin)
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    airfoil_tip = (cq.Workplane().copyWorkplane(cq.Workplane(tip_plane)).add(airfoil_root.vals()[1]).toPending()
                   .airfoil(tip_airfoil, tip_chord, offset=offset))
    pending = airfoil_tip.ctx.pendingWires
    try:
        _wing = airfoil_tip.loft().union(airfoil_root.vals()[2])  # ruled=True --> airfoils must have same number of points
        return _wing.newObject([tip_plane.location, airfoil_tip.val(), _wing.val()])
    except:
        loft = cq.Solid.makeLoft(pending)
        _wing = cq.Workplane(obj=loft).copyWorkplane(
            airfoil_tip)  # ruled=True --> airfoils must have same number of points0
        return _wing.newObject([tip_plane.location, airfoil_tip.val(), self.findSolid(), _wing.findSolid()])


cq.Workplane.wing_segment = wing_segment

if __name__ == "__main__":
    _airfoil = "../components/airfoils/naca23013.5.dat"
    wing: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=_airfoil,
                                                            root_chord=200,
                                                            root_dihedral=0,
                                                            root_incidence=0,
                                                            length=200,
                                                            sweep=5,
                                                            sweep_mode="angle",
                                                            tip_chord=100,
                                                            tip_dihedral=4,
                                                            tip_incidence=-2))
    wing.display(name="naca23013.5", severity=logging.WARN)

    wing = wing.wing_segment(tip_airfoil=_airfoil, tip_chord=40, length=100, tip_dihedral=0, sweep_mode="angle",
                             sweep=5)
    wing.display(name="naca23013.5_middle", severity=logging.WARN)

    wing = wing.wing_segment(tip_airfoil=_airfoil, tip_chord=20, length=20, tip_dihedral=0, sweep_mode="angle", sweep=5)
    wing.display(name="naca23013.5_tip", severity=logging.WARN)

    off_wing: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=_airfoil,
                                                                root_chord=200,
                                                                root_dihedral=0,
                                                                root_incidence=0,
                                                                length=200,
                                                                sweep=5,
                                                                sweep_mode="angle",
                                                                tip_chord=100,
                                                                tip_dihedral=4,
                                                                tip_incidence=-2,
                                                                offset=-0.8))
    off_wing.display(name="off_wing.5", severity=logging.WARN)

    off_wing = off_wing.wing_segment(tip_airfoil=_airfoil, tip_chord=40, length=100, tip_dihedral=0, sweep_mode="angle",
                                     sweep=5, offset=-0.8)
    off_wing.display(name="off_wing.5_middle", severity=logging.WARN)

    off_wing = off_wing.wing_segment(tip_airfoil=_airfoil, tip_chord=20, length=20, tip_dihedral=0, sweep_mode="angle",
                                     sweep=5, offset=-0.8)
    off_wing.display(name="off_wing.5_tip", severity=logging.WARN)
    pass
