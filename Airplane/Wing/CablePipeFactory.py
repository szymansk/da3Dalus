from __future__ import print_function

import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
from OCC.Core.ChFi2d import *  # ChFi2d_AnaFilletAlgo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
from Dimensions import ShapeDimensions
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class CablePipeFactory:
    """
    This CLass is used to create a Cable Pipe in the wing
    """

    def __init__(self, tigl_handle, wing_nr) -> None:
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wing_nr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_shape)
        self.display = myDisplay.instance(True)
        # self.fillet_radius=self.radius*1.5
        self.shape = None
        self.points = None
        self.radius = None

    def get_shape(self):
        """
        :return: Shape of the pipe Shape
        """
        return self.shape

    def create_complete_pipe(self, points: list, radius):
        """
        Create a Pipe that runs trhu the given Points with the given radius
        :param points: list of points
        :param radius: in meters
        :return:
        """
        self.points = points
        self.radius = radius
        pipe_shapes = []
        print(f"{len(self.points)=}")
        for i in range(0, len(self.points) - 1):
            print(f"{i=}")
            pipe_shapes.append(self._pipe_section(self.points[i], self.points[i + 1], self.radius))

        for i in range(1, len(self.points)):
            pipe_shapes.append(self._pipe_corner(self.points[i], self.radius))

        pipe = BooleanOperationsForLists.fuse_list_of_shapes(pipe_shapes)
        self.shape = pipe
        return pipe

    def points_route_thru(self, servo_dimensions: ShapeDimensions, fuselage_dimensions: ShapeDimensions):
        """
        :param servo_dimensions:
        :param fuselage_dimensions:
        :return: list of points
        """
        points = []
        # Point0
        p: Ogp.gp_Pnt = servo_dimensions.get_point(0)
        point0: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X(), p.Y(), p.Z())
        points.append(point0)

        # point1
        p1: Ogp.gp_Pnt = servo_dimensions.get_point(1)
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(p1.X() - 0.04, p1.Y() - 0.05, p.Z())
        points.append(point1)

        # point2
        fuselage_mid_point: Ogp.gp_Pnt = fuselage_dimensions.get_point(0)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X() - 0.05, fuselage_dimensions.get_ymax() / 2,
                                        self.wing_koordinates.get_zmid())
        points.append(point2)

        # point3
        point3: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_mid_point.X(), fuselage_mid_point.Y(), fuselage_mid_point.Z())
        points.append(point3)
        return points

    def _pipe_section(self, point1: Ogp.gp_Pnt, point2: Ogp.gp_Pnt, radius=0.002) -> OTopo.TopoDS_Shape:
        """
        Create a pipe between 2 given points witha given radius
        :param point1:
        :param point2:
        :param radius: in meters
        :return: pipe section
        """
        make_wire = OBuilder.BRepBuilderAPI_MakeWire()
        edge = OBuilder.BRepBuilderAPI_MakeEdge(point1, point2).Edge()
        make_wire.Add(edge)
        make_wire.Build()
        wire = make_wire.Wire()

        mydir = Ogp.gp_Dir(point2.X() - point1.X(), point2.Y() - point1.Y(), point2.Z() - point1.Z())
        circle = Ogp.gp_Circ(gp_Ax2(point1, mydir), radius)

        profile_edge = OBuilder.BRepBuilderAPI_MakeEdge(circle).Edge()
        profile_wire = OBuilder.BRepBuilderAPI_MakeWire(profile_edge).Wire()
        profile_face = OBuilder.BRepBuilderAPI_MakeFace(profile_wire).Face()
        pipe_section = OOff.BRepOffsetAPI_MakePipe(wire, profile_face).Shape()
        return pipe_section

    def _pipe_corner(self, centre, radius) -> OTopo.TopoDS_Shape:
        """
        returss a sphere witch is used in the curves (corners) of the pipe
        :param centre:
        :param radius:
        :return:
        """
        sphere: OTopo.TopoDS_Shape = OPrim.BRepPrimAPI_MakeSphere(centre, radius).Shape()
        self.display.display_this_shape(sphere)
        return sphere
