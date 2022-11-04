import logging
import math

import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as Bof
import Extra.tigl_extractor as tigl_extractor
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class ReinforcementePipeFactory:
    def __init__(self, tigl_handle, wingNr):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_shape)

        self.fuselage: TConfig.CCPACSFuselage = self.cpacs_configuration.get_fuselage(1)
        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        self.fuselage_koordiantes = PDim.ShapeDimensions(self.fuselage_shape)

        self.shape: OTopo.TopoDS_Shape = None
        self.shapes: list = []
        self.m = myDisplay.instance()

    def create_reinforcemente_pipe_option1_wing(self, radius=0.002, thickness=0.0004, quantity=3,
                                                pipe_position=None) -> OTopo.TopoDS_Shape:
        logging.info(f"Creating reinforcement option1")
        ribs = []

        segment_first: TConfig.CPACSWingSegment = self.wing.get_segment(1)
        segment_last: TConfig.CPACSWingSegment = self.wing.get_segment(self.wing.get_segment_count())
        inner: OTopo.TopoDS_Shape = segment_first.get_inner_closure()
        outer: OTopo.TopoDS_Shape = segment_last.get_outer_closure()

        inner_dimensions = PDim.ShapeDimensions(inner)
        outer_dimensions = PDim.ShapeDimensions(outer)
        inner_x_list = inner_dimensions.get_koordinates_on_achs(3)
        outer_x_list = outer_dimensions.get_koordinates_on_achs(3)

        lenght = inner_dimensions.get_length()
        height = inner_dimensions.get_height()
        x_dif = abs(inner_dimensions.get_xmin() - outer_dimensions.get_xmin())
        y_dif = abs(inner_dimensions.get_ymin() - outer_dimensions.get_ymin())
        width = math.hypot(x_dif, y_dif)
        logging.info(f"{radius=:.4f} {thickness=:.4f} {width=:.4f}")

        if pipe_position == None:
            pipe_position = range(0, quantity)

        # Cylinder
        for i, x in enumerate(inner_x_list):
            print(f"{i}")
            if i in pipe_position:
                point1 = Ogp.gp_Pnt(x, inner_dimensions.get_ymin(), inner_dimensions.get_zmid())
                point2 = Ogp.gp_Pnt(outer_x_list[i], outer_dimensions.get_ymin(), outer_dimensions.get_zmid())
                pipe = self.pipe_section(point1, point2, radius + thickness)
                self.shapes.append(pipe)
        cylinders = Bof.fuse_list_of_shapes(self.shapes)
        self.shape = cylinders
        return cylinders

    def create_reinforcement_pipe_option1_fuselage(self, radius: object, y_max: object, y_min: object, z_max: object,
                                                   z_min: object) -> OTopo.TopoDS_Shape:
        pipes = []

        # pipe1
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_max, z_max)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_max, z_max)
        pipe1 = self.pipe_section(point1, point2, radius)
        pipes.append(pipe1)

        # pipe2
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_min, z_max)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_min, z_max)
        pipe2 = self.pipe_section(point1, point2, radius)
        pipes.append(pipe2)

        # pipe3
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_min, z_min)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_min, z_min)
        pipe3 = self.pipe_section(point1, point2, radius)
        pipes.append(pipe3)

        # pipe4
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_max, z_min)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_max, z_min)
        pipe4 = self.pipe_section(point1, point2, radius)
        pipes.append(pipe4)

        fused_pipes = Bof.fuse_list_of_shapes(pipes)
        return fused_pipes

    def get_shape(self) -> OTopo.TopoDS_Shape:
        return self.shape

    def pipe_section(self, point1, point2, radius) -> OTopo.TopoDS_Shape:
        makeWire = BRepBuilderAPI_MakeWire()
        edge = BRepBuilderAPI_MakeEdge(point1, point2).Edge()
        makeWire.Add(edge)
        makeWire.Build()
        wire = makeWire.Wire()

        dir = gp_Dir(point2.X() - point1.X(), point2.Y() - point1.Y(), point2.Z() - point1.Z())
        circle = Ogp.gp_Circ(gp_Ax2(point1, dir), radius)
        profile_edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        profile_wire = BRepBuilderAPI_MakeWire(profile_edge).Wire()
        profile_face = BRepBuilderAPI_MakeFace(profile_wire).Face()
        pipe = OOff.BRepOffsetAPI_MakePipe(wire, profile_face).Shape()
        self.m.display_in_origin(pipe)
        return pipe


if __name__ == "__main__":
    tigl_handle = tigl_extractor.get_tigl_handler("aircombat_v7")
    # tigl_handle= tigl_extractor.get_tigl_handler("simple_aircraft_v2")
    m = myDisplay.instance(True)
    a = ReinforcementePipeFactory(tigl_handle, 1)
    pipe_position = [0, 1]
    a.create_reinforcemente_pipe_option1(0.002, 0.0004, 3, pipe_position)
    m.start()
