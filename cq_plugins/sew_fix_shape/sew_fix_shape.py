from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopAbs import TopAbs_SHELL
from OCP.TopExp import TopExp_Explorer
from cadquery import Workplane, Shell, Solid


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
