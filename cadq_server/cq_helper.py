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
from OCP.StdFail import StdFail_NotDone
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS_Shape, TopoDS_Face
from OCP.gp import gp_GTrsf, gp_Mat, gp_XYZ
from cadquery import Workplane, Shell, Solid

from cadq_server.cadq_server_connector import CQServerConnector

def _display(self: Workplane, name: str = "", color: cq.Color = cq.Color("gold"), severity: int = logging.NOTSET, url: str = "http://cq-server:5000/json") -> Workplane:
    if severity >= logging.root.level:
        _display._connector = _display._connector if _display._connector is not  None else CQServerConnector(url=url)
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
    fix_shape.Perform()
    solid = Solid(fix_shape.Shape())
    return self.newObject(objlist=[solid])

Workplane.sewAndFix = sewAndFixShape

def offset3D(self: Workplane, offset: float, tol=1e-6, join_mode: Literal["arc", "intersection", "tangent"]="arc",
             remove_internal_edges=False, perform_simple=True) -> Workplane:
    solid = self.findSolid()
    maker = BRepOffsetAPI_MakeOffsetShape()

    if perform_simple:
        maker.PerformBySimple(solid.wrapped, offset)
    else:
        jm = GeomAbs_Arc
        if join_mode=="intersection":
            jm = GeomAbs_Tangent
        elif join_mode == "intersection":
            jm = GeomAbs_Intersection

        maker.PerformByJoin(solid.wrapped, offset, tol,
                                 BRepOffset_Skin, False, False, jm,
                                 remove_internal_edges)

    of_shape = maker.Shape()
    new_solid = cq.Solid(of_shape)
    shell = cq.CQ(new_solid).shells().val().fix()
    return self.newObject([shell])

Workplane.offset3D = offset3D

def scaleXyz(self: Workplane, x_scale: float = 1.0, y_sacle: float = 1.0, z_scale: float = 1.0):

    scale = gp_Mat(x_scale, 0, 0,
                 0, y_sacle, 0,
                 0, 0, z_scale)
    aTrsf = gp_GTrsf(scale, gp_XYZ(0,0,0))
    aBrepTrsf = BRepBuilderAPI_GTransform(self.findSolid().wrapped, aTrsf)
    tShape = aBrepTrsf.Shape()
    return self.newObject(objlist=[tShape])

Workplane.scaleXyz = scaleXyz


def airfoil(self: cq.Workplane, selig_file: str, chord: float, forConstruction: bool = False):
    file = open(selig_file, "r")
    point_list = []
    for line_num, line in enumerate(file):
        line: str = line
        if line_num < 1:
            pass
        else:
            tokens = [n for n in line.strip().split(" ") if n != ""]
            x = float(tokens[0])
            y = float(tokens[1])
            point_list.append((x * chord, y * chord))
    file.close()
    nose_point = min(point_list, key = lambda t: t[0])
    nose_wp = cq.Workplane(inPlane='front').center(-nose_point[0], -nose_point[1])
    wire = (nose_wp.splineApprox(points=point_list, forConstruction=forConstruction, tol=1e-3).close().val())
    face = cq.Face.makeFromWires(outerWire=wire)
    trans_face = face.transformShape(self.plane.rG)

    return self.newObject([trans_face, cq.CQ(trans_face).wires().val()])

cq.Workplane.airfoil = airfoil


def wing_root_segment(self: cq.Workplane, root_airfoil: str,
                      root_chord: float, tip_chord: float, length: float,
                      sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                      root_incidence: float = 0, tip_incidence: float = 0,
                      root_dihedral: float = 0, tip_dihedral: float = 0, tip_airfoil: str = None):
    tip_airfoil = tip_airfoil if tip_airfoil is not None else root_airfoil

    root_plane = self.plane.rotated((root_dihedral, 0, -root_incidence))

    airfoil_root = (cq.Workplane(root_plane).airfoil(root_airfoil, root_chord)).wires().toPending()
    tip_plane: cq.Plane = (airfoil_root.workplane(offset=-length, origin=(sweep, 0, 0))
                 .plane.rotated((tip_dihedral, 0, -(tip_incidence+root_incidence))))
    airfoil_tip = (airfoil_root.copyWorkplane(cq.Workplane(tip_plane))
                   .airfoil(tip_airfoil, tip_chord))
    #airfoil_tip.box(1,1,1000).display(name="wp", severity=logging.WARN)
    airfoil_tip_wire = airfoil_tip.wires().toPending()
    wing = airfoil_tip_wire.loft()  # ruled=True --> airfoils must have same number of points
    shell = wing.shells().val().fix()  # fix the orientation of the faces
    return wing.newObject([tip_plane.location, shell])

cq.Workplane.wing_root_segment = wing_root_segment


def wing_segment(self: cq.Workplane, tip_airfoil: str, tip_chord: float, length: float,
                 sweep: float = 0, sweep_mode: Literal["distance", "angle"] = "distance",
                 tip_incidence: float = 0, tip_dihedral: float = 0):
    airfoil_root = self.faces('>Y')
    airfoil_root.ctx.pendingWires = [airfoil_root.wires().val()]

    loc:cq.Location = self.val()
    origin, rot = loc.toTuple()
    vec = cq.Vector(*origin)
    vec.x = vec.x + sweep

    tip_plane: cq.Plane = (airfoil_root.workplane(offset=-length, origin=vec, invert=False)
                 .plane.rotated((tip_dihedral, 0, -tip_incidence)))
    #airfoil_root.copyWorkplane(cq.Workplane(tip_plane)).box(1,1,500,centered=(True,True,False)).display(name="naca23013.5", severity=logging.WARN)

    airfoil_tip: Workplane = (airfoil_root.copyWorkplane(cq.Workplane(tip_plane))
                   .airfoil(tip_airfoil, tip_chord))
    airfoil_tip.display(name="tip", severity=logging.ERROR)
    airfoil_tip_wire = airfoil_tip.wires().toPending()
    wing = airfoil_tip_wire.loft(combine='a', ruled=True)  # ruled=True --> airfoils must have same number of points
    shell = wing.shells().val().fix()  # fix the orientation of the faces
    return wing.newObject([shell, *self.objects])

cq.Workplane.wing_segment = wing_segment



if __name__ == "__main__":
    airfoil = "../components/airfoils/naca23013.5.dat"
    wing: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=airfoil,
                                                 root_chord=200,
                                                 root_dihedral=10,
                                                 root_incidence=3,
                                                 length=300,
                                                 sweep=100,
                                                 tip_chord=100,
                                                 tip_dihedral=4,
                                                 tip_incidence=-2))
    wing.display(name="naca23013.5", severity=logging.WARN)
    # loc = wing._locs()[-1]
    #
    wing_tip: Workplane = (cq.Workplane('XZ').wing_root_segment(root_airfoil=airfoil,
                                                            root_chord=100,
                                                            root_dihedral=0,
                                                            root_incidence=0,
                                                            length=100,
                                                            sweep=50,
                                                            tip_chord=30,
                                                            tip_dihedral=0,
                                                            tip_incidence=0))

    wing_tip: Workplane = wing.wing_segment(tip_airfoil=airfoil, tip_chord=100, length=50,
                                             tip_dihedral=0, tip_incidence=0, sweep=0)
    # origin, rot = wing.val().toTuple()
    # print(rot)
    # wing_tip = wing_tip.rotate( (0,0,0), (1,0,0), 10+4)
    # wing_tip = wing_tip.rotate( (0,0,0), (0,1,0), 3-2)
    #
    # wing_tip = wing_tip.translate(origin).display(name="naca23013.5_tip", severity=logging.WARN)
    wing_tip.display(name="naca23013.5_tip", severity=logging.WARN)
    #cq.Workplane( wing_tip.findSolid().locate(loc)).display(name="5_tip", severity=logging.WARN)
    pass
