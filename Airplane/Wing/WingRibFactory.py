import logging

import OCP.BRepAlgoAPI as OAlgo
import OCP.BRepPrimAPI as OPrim
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace
from OCP.gp import *

import Dimensions.ShapeDimensions as PDim
from Extra.BooleanOperationsForLists import BooleanCADOperation
import Extra.patterns as pat
from Airplane.aircraft_topology.WingInformation import WingInformation
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from cadquery import Workplane

class WingRibFactory:
    """
    This class is used to create the Ribs for the given wing identifies by the index
    After initializing the class, call one of the create methods
    """

    @classmethod
    def create_ribcage(cls, wing_shape: Workplane, wing_information: WingInformation,
                       rib_distance, rib_width=0.0004) -> Workplane:
        '''
        Creates a rib cage with horizontal oriented ribs and diagonal ribs
        Parameters
        horizontal_rib_quantity: The number of horizontal ribs, setting by default to 3
        rib_width: Width of the inner_closure ribs of wing and fuselage in meters default=0.0004
        :param rib_distance:
        :param WingInformation:
        :param wing_shape:
        '''
        logging.debug(f"Creating ribs option1")
        ribs: list[Workplane] = []

        for index, seg in enumerate(wing_information.segments):
            ribs.append(WingRibFactory._create_oriented_horizontal_ribs(root_x_list=seg.root_x_list,
                                                                        tip_x_list=seg.tip_x_list,
                                                                        root_y_min=seg.root_y_min,
                                                                        root_z_min=seg.root_z_min,
                                                                        width=seg.width,
                                                                        height=seg.height,
                                                                        rib_width=rib_width,
                                                                        name=f"segment_{index}"))
        front_sweep_angle = wing_information.segments[-1].sweep_angle
        y_dif = wing_information.get_wing_length()

        logging.debug(f"ribs list lenght: {len(ribs)}")

        # Fuse if lenght of ribs longer than 1
        if len(ribs) > 1:
            ribs.append(
                BooleanCADOperation.fuse_list_of_named_shapes(ribs, f"{wing_shape.name()}_oriented_ribs"))

        # diagonaleribs
        starting_angle = 60
        rib_angle = starting_angle - front_sweep_angle

        rib_quantity = round(y_dif / rib_distance)
        logging.debug(f"{y_dif=} {rib_quantity=}")
        ribs.append(WingRibFactory._create_diagonal_ribs(rib_width, rib_angle, wing_shape, rib_quantity))

        # fused ribs
        ribs.append(Workplane(OAlgo.BRepAlgoAPI_Fuse(ribs[-1].shape(), ribs[-2].shape()).Shape(),
                                     f"{wing_shape.name()}_complete_ribs"))
        ConstructionStepsViewer.instance().display_fuse(ribs[-1], ribs[-2], ribs[-3], logging.NOTSET)

        # trim ribs to wing Shape
        ribs.append(Workplane(OExs.translate_shp(ribs[-1].shape(), gp_Vec(0, 0, -0.005)),
                                     f"{wing_shape.name()}_cmoved_ribs"))
        trimed_wing: Workplane = Workplane(
            OAlgo.BRepAlgoAPI_Common(wing_shape.shape(), ribs[-1].shape()).Shape(), f"trimed_{wing_shape.name()}_ribs")

        ribs.append(trimed_wing)
        ConstructionStepsViewer.instance().display_common(ribs[-1], wing_shape, ribs[-2], logging.NOTSET)
        return trimed_wing

    @staticmethod
    def _create_oriented_horizontal_ribs(root_x_list: list[float], tip_x_list: list[float], root_y_min: float,
                                         root_z_min: float, width: float, height: float, rib_width: float, name="") \
            -> Workplane:
        """
        Creates a multiple oriented horizontal rib.
        Paramaters:
        root_x_list: a list with x kordiante values where the rib should start
        tip_x_list: a list with x kordiante values where the rib should end
        root_y: y koordinate where the rib schould start
        root_z: z koordinate where the rib schould start
        lenght, width, height parameters of the shape that is becoming the rib
        rib_width: the width of the rib given in meters
        """
        logging.debug(f"Creating horizontal ribs for {name} with {len(root_x_list)} ribs and {rib_width=}")
        ribs = []
        for i in range(0, len(root_x_list)):
            ribs.append(
                WingRibFactory._create_single_box_rib(root_x_list[i], tip_x_list[i], root_y_min, root_z_min, width, height, rib_width,
                                            f"single_rib_{i}"))
        fused_ribs: Workplane = BooleanCADOperation.fuse_list_of_named_shapes(ribs,
                                                                                          f"{name}_oriented_horizontal_ribs")
        return fused_ribs

    @staticmethod
    def _create_single_box_rib(x_inner, x_outer, y_pos, z_pos, seg_width, seg_height,
                               rib_width, name="single_rib") -> Workplane:
        """
        Creates a singl oriented horizontal rib.
        Paramaters:
        x_inner: a x kordiante where the rib should start
        x_outer: a x kordiante where the rib should end
        y_pos: y koordinate where the rib schould start
        z_pos: z koordinate where the rib schould start
        seg_width, seg_height parameters of the Segment that is becoming the rib
        rib_width: the width of the rib given in meters
        """
        corner_points = []
        # point1: bottom right corner of a box, at the root segment
        x_cor = x_inner + (rib_width / 2)
        logging.debug(f"test {x_inner=:.6f} {x_cor=:.6f}")
        y_cor = y_pos
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point2 bottom right corner of a box, at the tip segment
        x_cor = x_outer + (rib_width / 2)
        y_cor = y_pos + seg_width
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point3 bottom left corner of a box, at the tip segment
        x_cor = x_outer - (rib_width / 2)
        y_cor = y_pos + seg_width
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point4 bottom left corner of a box, at the root segment
        x_cor = x_inner - (rib_width / 2)
        y_cor = y_pos
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        make_wire = BRepBuilderAPI_MakeWire()
        for i, point in enumerate(corner_points):
            logging.debug(f"Creating Edge {i + 1} from {len(corner_points)}")
            if point != corner_points[-1]:
                make_wire.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[i + 1]).Edge())
            else:
                make_wire.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[0]).Edge())

        logging.debug(f"Creating {name} out of Edges")
        prism = OPrim.BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(make_wire.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, seg_height)),
        ).Shape()
        named_single_rib: Workplane = Workplane(prism, name)
        return named_single_rib

    @staticmethod
    def _create_diagonal_ribs(rib_width, angle, wing_shape, ribs_quantity) -> Workplane:
        """
        Creates a pattern of diagonal ribs for the class wing
        :param wing_shape:
        """
        logging.debug(f"Creating diagonal ribs: {rib_width=} {angle=} {ribs_quantity=}")
        prim = []
        wing_dimension = PDim.ShapeDimensions(wing_shape)
        prim.append(Workplane(OPrim.BRepPrimAPI_MakeBox(wing_dimension.get_length() * 2, rib_width,
                                                               wing_dimension.get_height() * 1.2).Shape(),
                                     "singlerib_box"))
        prim.append(Workplane(OExs.rotate_shape(prim[-1].shape(), gp_OZ(), angle), "singlerib_moved_box"))
        prim.append(Workplane(
            OExs.translate_shp(prim[-1].shape(), gp_Vec(wing_dimension.get_x_min(), -rib_width,
                                                            wing_dimension.get_z_min())), "singlerib"))
        # ConstructionStepsViewer.instance().display_this_shape(prim[-1])
        if ribs_quantity == 0:
            ribs_distance = 0.03
            ribs_quantity = round((wing_dimension.get_width() / ribs_distance) * 2)
        else:
            ribs_distance = wing_dimension.get_width() / ribs_quantity
            ribs_quantity = ribs_quantity * 2

        prim.append(pat.create_linear_pattern(prim[-1], ribs_quantity, ribs_distance, "y"))
        prim.append(Workplane(
            OExs.translate_shp(prim[-1].shape(), gp_Vec(0, -wing_dimension.get_width() / 2, 0)),
            "diagonal ribs"))
        named_diagonal_ribs: Workplane = Workplane(prim[-1].shape(), "diagonal ribs")
        ConstructionStepsViewer.instance().display_this_shape(named_diagonal_ribs, logging.NOTSET)
        return named_diagonal_ribs
