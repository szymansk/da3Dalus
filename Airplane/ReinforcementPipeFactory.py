import math

import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as Bof
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
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)

        self.fuselage: TConfig.CCPACSFuselage = self.cpacs_configuration.get_fuselage(1)
        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        self.fuselage_koordiantes = PDim.ShapeDimensions(self.fuselage_loft)

        self.namedshape: TGeo.CNamedShape = TGeo.CNamedShape()
        self.shapes: list[TGeo.CNamedShape] = []
        self.m = myDisplay.instance()

    def create_reinforcemente_pipe_option1_wing(self, radius=0.002, thickness=0.0004, quantity=3,
                                                pipe_position=None) -> TGeo.CNamedShape:
        logging.info(f"Creating reinforcement option1")
        ribs = []

        segment_first: TConfig.CPACSWingSegment = self.wing.get_segment(1)
        segment_last: TConfig.CPACSWingSegment = self.wing.get_segment(self.wing.get_segment_count())
        inner: TGeo.CNamedShape = TGeo.CNamedShape(segment_first.get_inner_closure(), "inner_closure")
        outer: TGeo.CNamedShape = TGeo.CNamedShape(segment_last.get_outer_closure(), "outer_closure")

        inner_dimensions = PDim.ShapeDimensions(inner)
        outer_dimensions = PDim.ShapeDimensions(outer)
        inner_x_list = inner_dimensions.get_koordinates_on_achs(quantity)
        outer_x_list = outer_dimensions.get_koordinates_on_achs(quantity)

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
                pipe = self.pipe_section(point1, point2, radius + thickness, f"pipe_section_{i}")
                self.shapes.append(pipe)
                self.m.display_in_origin(pipe)

        cylinders = Bof.fuse_list_of_namedshapes(self.shapes, f"reinforcement_pipe")
        self.shape = cylinders
        return cylinders

    def create_reinforcement_pipe_option1_fuselage(self, radius, y_max, y_min, z_max, z_min) -> TGeo.CNamedShape:
        pipes = []

        # pipe1
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_max, z_max)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_max, z_max)
        pipe1 = self.pipe_section(point1, point2, radius, "pipe_section_")

        # pipe2
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_min, z_max)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_min, z_max)
        pipe2 = self.pipe_section(point1, point2, radius, "pipe_section_2")

        # pipe3
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_min, z_min)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_min, z_min)
        pipe3 = self.pipe_section(point1, point2, radius, "pipe_section_3")
        pipe1.set_name(f"pipe_section_1")

        # pipe4
        point1: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmin(), y_max, z_min)
        point2: Ogp.gp_Pnt = Ogp.gp_Pnt(self.fuselage_koordiantes.get_xmax(), y_max, z_min)
        pipe4 = self.pipe_section(point1, point2, radius, "pipe_section_4")
        pipes.append(pipe4)
        fused_pipes = Bof.fuse_list_of_namedshapes(pipes, "Reinforcement_pipes")
        self.namedshape = fused_pipes
        return fused_pipes

    def get_shape(self) -> TGeo.CNamedShape:
        return self.namedshape

    def pipe_section(self, point1, point2, radius, name) -> TGeo.CNamedShape:
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
        pipe = TGeo.CNamedShape(OOff.BRepOffsetAPI_MakePipe(wire, profile_face).Shape(), name)
        self.m.display_in_origin(pipe)
        return pipe
