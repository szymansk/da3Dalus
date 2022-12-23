from __future__ import print_function

import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
from Dimensions import ShapeDimensions
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *


class CablePipeFactory:
    """
    This CLass is used to create a Cable Pipe in the wing
    """

    def __init__(self, wing) -> None:

        self.wing: TConfig.CCPACSWing = wing

        self.named_shape = TGeo.CNamedShape()
        self.points: list[Ogp.gp_Pnt] = []
        self.radius: float = 0.002
        self.display = ConstructionStepsViewer.instance()

    def get_shape(self) -> TGeo.CNamedShape:
        return self.named_shape

    def create_complete_pipe(self, points: list, radius) -> TGeo.CNamedShape:
        """
        Create a Pipe that runs through the given Points with the given radius
        :param points: list of points
        :param radius: in meters
        :return: the named shape of the created pipe
        """
        self.points = points
        self.radius = radius
        pipe_shapes = []
        logging.debug(f"Creating a pipe through {len(self.points)=} points")

        for i in range(0, len(self.points) - 1):
            pipe_shapes.append(self._pipe_section(self.points[i], self.points[i + 1], self.radius, i))

        for i in range(1, len(self.points)):
            pipe_shapes.append(self._pipe_corner(self.points[i], self.radius, i))

        named_pipe = BooleanOperationsForLists.fuse_list_of_namedshapes(pipe_shapes, "cable_pipe")
        self.loft = named_pipe
        return named_pipe

    def points_route_through(self, servo_dimensions: ShapeDimensions, fuselage_dimensions: ShapeDimensions):
        """
        This method returns a list of point that describe the route of a pipe. It starts at the centre of the servo and
        ends at the centre of the fuselage
        :param servo_dimensions: dimensions of the servo
        :param fuselage_dimensions: dimensions of the fuselage
        :return: list of points
        """
        points = []

        # Point0
        p: Ogp.gp_Pnt = servo_dimensions.get_point(0)
        point0: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X(), p.Y(), p.Z())
        points.append(point0)

        # point1
        p1: Ogp.gp_Pnt = servo_dimensions.get_point(1)
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(p1.X() - servo_dimensions.get_length() / 2,
                                        p1.Y() - servo_dimensions.get_width() / 2, p.Z())
        points.append(point1)

        # point2
        wing_inner_cord = self._get_segment_dimensions(1)
        fuselage_mid_point: Ogp.gp_Pnt = fuselage_dimensions.get_point(0)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(p.X(), fuselage_dimensions.get_y_max() / 2,
                                        wing_inner_cord.get_z_mid())
        points.append(point2)

        # point3
        point3: Ogp.gp_Pnt = Ogp.gp_Pnt(wing_inner_cord.get_x_mid(), fuselage_mid_point.Y(), fuselage_mid_point.Z())
        points.append(point3)
        return points

    def _pipe_section(self, start: Ogp.gp_Pnt, end: Ogp.gp_Pnt, radius=0.002, index=0) -> TGeo.CNamedShape:
        """
        Create a pipe between 2 given points with a given radius
        :param start: starting point of the pipe section
        :param end: ending point of the pipe section
        :param radius: in meters default set to 0.002 meters
        :param index: a number to identify the pipesection
        :return: named shape of pipe section
        """
        logging.debug(f"Creating pipesection_{index}")
        make_wire = OBuilder.BRepBuilderAPI_MakeWire()
        edge = OBuilder.BRepBuilderAPI_MakeEdge(start, end).Edge()
        make_wire.Add(edge)
        make_wire.Build()
        wire = make_wire.Wire()

        my_dir = Ogp.gp_Dir(end.X() - start.X(), end.Y() - start.Y(), end.Z() - start.Z())
        circle = Ogp.gp_Circ(gp_Ax2(start, my_dir), radius)

        profile_edge = OBuilder.BRepBuilderAPI_MakeEdge(circle).Edge()
        profile_wire = OBuilder.BRepBuilderAPI_MakeWire(profile_edge).Wire()
        profile_face = OBuilder.BRepBuilderAPI_MakeFace(profile_wire).Face()
        pipe_section = TGeo.CNamedShape(OOff.BRepOffsetAPI_MakePipe(wire, profile_face).Shape(), "Pipesection")
        return pipe_section

    def _pipe_corner(self, centre: Ogp.gp_Pnt, radius: float, index=0) -> TGeo.CNamedShape:
        """
        returns a sphere witch is used in the curves (corners) of the pipe
        :param centre: a point at the center of the corner
        :param radius: radius of the corner
        :param index: a number to identify the corner
        :return: named shape of the corner
        """
        logging.debug(f"Creating pipecorner_{index}")
        sphere: OTopo.TopoDS_Shape = OPrim.BRepPrimAPI_MakeSphere(centre, radius).Shape()
        named_sphere: TGeo.CNamedShape = TGeo.CNamedShape(sphere, f"pipecorner_{index}")
        return named_sphere

    def _get_segment_dimensions(self, index):
        segment: TConfig.CCPACSWingSegment = self.wing.get_segment(index)
        wire: OTopo.TopoDS_Wire = segment.get_inner_closure()
        named_wire = TGeo.CNamedShape(wire, "wire")
        wire_dimensions = PDim.ShapeDimensions(named_wire)
        return wire_dimensions
