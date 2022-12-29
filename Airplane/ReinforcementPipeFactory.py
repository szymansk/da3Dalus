import logging
import math

import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as Bof
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class ReinforcementePipeFactory:
    '''
    This class ist used to create the reinforcementpipe for the wing and the fuselage
    '''

    def __init__(self, wing):

        self.wing: TConfig.CCPACSWing = wing
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)

        # self.fuselage: TConfig.CCPACSFuselage = fuselage
        # self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        # self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        # self.fuselage_coordinates = PDim.ShapeDimensions(self.fuselage_loft)

        self.named_shape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list[TGeo.CNamedShape] = []
        self.m = ConstructionStepsViewer.instance()

    def create_reinforcemente_pipe_wing(self, radius=0.002, thickness=0.0004, quantity=3,
                                        pipe_position=None) -> TGeo.CNamedShape:
        logging.debug(f"Creating reinforcement option1")

        segment_first: TConfig.CPACSWingSegment = self.wing.get_segment(1)
        segment_last: TConfig.CPACSWingSegment = self.wing.get_segment(self.wing.get_segment_count())
        inner_closure: TGeo.CNamedShape = TGeo.CNamedShape(segment_first.get_inner_closure(), "inner_closure")
        outer_closure: TGeo.CNamedShape = TGeo.CNamedShape(segment_last.get_outer_closure(), "outer_closure")

        inner_dimensions = PDim.ShapeDimensions(inner_closure)
        outer_dimensions = PDim.ShapeDimensions(outer_closure)
        inner_x_list = inner_dimensions.get_coordinates_on_axis(quantity)
        outer_x_list = outer_dimensions.get_coordinates_on_axis(quantity)

        x_dif = abs(inner_dimensions.get_x_min() - outer_dimensions.get_x_min())
        y_dif = abs(inner_dimensions.get_y_min() - outer_dimensions.get_y_min())
        width = math.hypot(x_dif, y_dif)
        logging.debug(f"{radius=:.4f} {thickness=:.4f} {width=:.4f}")

        if pipe_position is None:
            pipe_position = range(0, quantity)

        # Cylinder
        for i, x in enumerate(inner_x_list):
            if i in pipe_position:
                start = Ogp.gp_Pnt(x, inner_dimensions.get_y_min(), inner_dimensions.get_z_mid())
                end = Ogp.gp_Pnt(outer_x_list[i], outer_dimensions.get_y_min(), outer_dimensions.get_z_mid())
                pipe = ReinforcementePipeFactory.create_pipe_section(start, end, radius + thickness, f"pipe_section_{i}")
                self.shapes.append(pipe)
                self.m.display_in_origin(pipe, logging.NOTSET)

        cylinders = Bof.fuse_list_of_namedshapes(self.shapes, f"reinforcement_pipe")
        self.shape = cylinders
        return cylinders

    @classmethod
    def create_reinforcement_pipe_fuselage(cls, radius, y_max, y_min, z_max, z_min,
                                           fuselage_dimensions: PDim.ShapeDimensions) -> TGeo.CNamedShape:

        length = abs(fuselage_dimensions.get_x_min() - fuselage_dimensions.get_x_max())

        # pipe1
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_max, z_max)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_max, z_max)
        pipe1 = ReinforcementePipeFactory.create_pipe_section(start, end, radius, "pipe_section_1")

        # pipe2
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_min, z_max)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_min, z_max)
        pipe2 = ReinforcementePipeFactory.create_pipe_section(start, end, radius, "pipe_section_2")

        # pipe3
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_min, z_min)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_min, z_min)
        pipe3 = ReinforcementePipeFactory.create_pipe_section(start, end, radius, "pipe_section_3")

        # pipe4
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_max, z_min)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_max, z_min)
        pipe4 = ReinforcementePipeFactory.create_pipe_section(start, end, radius, "pipe_section_4")

        pipes = [pipe1, pipe2, pipe3, pipe4]
        fused_pipes = Bof.fuse_list_of_namedshapes(pipes, "Reinforcement_pipes")
        return fused_pipes

    def get_shape(self) -> TGeo.CNamedShape:
        return self.named_shape

    @classmethod
    def create_pipe_section(cls, start: Ogp.gp_Pnt, end: Ogp.gp_Pnt, radius: float, name="") -> TGeo.CNamedShape:
        '''
        Creates a cylinder between the start and end, with the given radius
        :param start: starting point
        :param end: ending point
        :param radius: radius of the cylinder
        :param name: name to be given
        :return: pipesection
        '''
        make_wire = BRepBuilderAPI_MakeWire()
        edge = BRepBuilderAPI_MakeEdge(start, end).Edge()
        make_wire.Add(edge)
        make_wire.Build()
        wire = make_wire.Wire()

        direction = Ogp.gp_Dir(end.X() - start.X(), end.Y() - start.Y(), end.Z() - start.Z())
        circle = Ogp.gp_Circ(Ogp.gp_Ax2(start, direction), radius)
        profile_edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        profile_wire = BRepBuilderAPI_MakeWire(profile_edge).Wire()
        profile_face = BRepBuilderAPI_MakeFace(profile_wire).Face()
        pipe = TGeo.CNamedShape(OOff.BRepOffsetAPI_MakePipe(wire, profile_face).Shape(), name)
        return pipe
