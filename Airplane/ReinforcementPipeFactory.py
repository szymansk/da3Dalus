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
from Airplane.aircraft_topology.WingInformation import WingInformation
from Extra.ConstructionStepsViewer import ConstructionStepsViewer


class ReinforcementPipeFactory:
    '''
    This class ist used to create the reinforcementpipe for the wing and the fuselage
    '''

    @classmethod
    def create_reinforcemente_pipe_wing(cls, wing_information: WingInformation, radius, thickness,
                                        pipe_position=None) -> TGeo.CNamedShape:
        logging.debug(f"Creating reinforcement option1")

        root_segment = wing_information.segments[0]
        tip_segment = wing_information.segments[-1]
        inner_x_list = root_segment.root_x_list
        outer_x_list = tip_segment.tip_x_list

        width = root_segment.width
        logging.debug(f"{radius=:.4f} {thickness=:.4f} {width=:.4f}")

        shapes: list[TGeo.CNamedShape] = []
        # Cylinder
        for i, x in enumerate(inner_x_list):
            if i in pipe_position:
                start = Ogp.gp_Pnt(x, root_segment.root_y_min, root_segment.root_z_mid)
                end = Ogp.gp_Pnt(outer_x_list[i], tip_segment.tip_y_min, tip_segment.tip_z_mid)
                pipe = ReinforcementPipeFactory.create_pipe_section(start, end, radius + thickness, f"pipe_section_{i}")
                shapes.append(pipe)
                ConstructionStepsViewer.instance().display_in_origin(pipe, logging.NOTSET)

        cylinders = Bof.BooleanCADOperation.fuse_list_of_named_shapes(shapes, f"reinforcement_pipe")
        return cylinders

    @classmethod
    def create_reinforcement_pipe_fuselage(cls, radius, y_max, y_min, z_max, z_min,
                                           fuselage_dimensions: PDim.ShapeDimensions) -> TGeo.CNamedShape:

        length = abs(fuselage_dimensions.get_x_min() - fuselage_dimensions.get_x_max())

        # pipe1
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_max, z_max)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_max, z_max)
        pipe1 = ReinforcementPipeFactory.create_pipe_section(start, end, radius, "pipe_section_1")

        # pipe2
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_min, z_max)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_min, z_max)
        pipe2 = ReinforcementPipeFactory.create_pipe_section(start, end, radius, "pipe_section_2")

        # pipe3
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_min, z_min)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_min, z_min)
        pipe3 = ReinforcementPipeFactory.create_pipe_section(start, end, radius, "pipe_section_3")

        # pipe4
        start: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_min()-length/2.0, y_max, z_min)
        end: Ogp.gp_Pnt = Ogp.gp_Pnt(fuselage_dimensions.get_x_max(), y_max, z_min)
        pipe4 = ReinforcementPipeFactory.create_pipe_section(start, end, radius, "pipe_section_4")

        pipes = [pipe1, pipe2, pipe3, pipe4]
        fused_pipes = Bof.BooleanCADOperation.fuse_list_of_named_shapes(pipes, "Reinforcement_pipes")
        return fused_pipes

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
