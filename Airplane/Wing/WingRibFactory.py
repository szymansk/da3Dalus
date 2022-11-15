import math

import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
import tigl3.boolean_ops as TBoo

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
import Extra.patterns as pat
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class WingRibFactory:
    """
    This class is used to create the Ribs for the given wing_index.
    After initializing the class, call one of the create methods
    """

    def __init__(self, tigl_handle, wing_index):
        self.tigl_handle = tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(wing_index)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_loft)
        self.shape: OTopo.TopoDS_Shape = OTopo.TopoDS_Shape()
        self.shapes: list = []
        self.display = myDisplay.instance()
        logging.info(f"{self.wing_koordinates=}")

    def create_ribs_option1(self, horizontal_rib_quantity=3, rib_width=0.0004) -> TGeo.CNamedShape:
        """
        Creates a rib cage with horizontal oriented ribs and diagonal ribs
        Parameters
        horizontal_rib_quantity default=3
        rib_width in meters default=0.0004m
        """
        logging.info(f"Creating ribs option1")
        logging.info(f"Segment Count: {self.wing.get_segment_count()}")
        ribs: list[TGeo.CNamedShape] = []
        x_dif: float = 0.0
        y_dif: float = 0.0
        for index in range(1, self.wing.get_segment_count() + 1):
            logging.info(f"{index=}")
            segment: TConfig.CCPACSWingSegment = self.wing.get_segment(index)
            inner: TGeo.CNamedShape = TGeo.CNamedShape(segment.get_inner_closure(), "inner_closure")
            outer: TGeo.CNamedShape = TGeo.CNamedShape(segment.get_outer_closure(), "outer_closure")

            inner_dimensions = PDim.ShapeDimensions(inner)
            outer_dimensions = PDim.ShapeDimensions(outer)
            inner_x_list = inner_dimensions.get_koordinates_on_achs(horizontal_rib_quantity)
            outer_x_list = outer_dimensions.get_koordinates_on_achs(horizontal_rib_quantity)

            lenght = inner_dimensions.get_length()
            # height = inner_dimensions.get_height()
            height = self.wing_koordinates.get_height()
            logging.info(f"{lenght=} {height=}")

            x_dif = abs(inner_dimensions.get_xmin() - outer_dimensions.get_xmin())
            y_dif = abs(inner_dimensions.get_ymin() - outer_dimensions.get_ymin())
            width = math.hypot(x_dif, y_dif)
            name = f"segment_{index}"
            # horitzontal_ribs
            ribs.append(self._make_oriented_horizontal_ribs(inner_x_list, outer_x_list, inner_dimensions.get_ymin(),
                                                            inner_dimensions.get_zmin(), lenght, width, height,
                                                            rib_width, name))

        logging.info(f"ribs list lenght: {len(ribs)}")
        if len(ribs) > 1:
            ribs.append(
                BooleanOperationsForLists.fuse_list_of_namedshapes(ribs, f"{self.wing_loft.name()}_oriented_ribs"))

        # diagonaleribs
        front_sweep_angle = math.degrees(math.atan(x_dif / y_dif))
        rib_angle = 60 - front_sweep_angle
        if y_dif > 1:
            rib_distance = 0.5
        else:
            rib_distance = 0.05
        rib_quantity = round(y_dif / rib_distance)
        logging.info(f"{y_dif=} {rib_quantity=}")
        rib_quantity = 12
        ribs.append(self._create_diagonal_ribs(rib_width, rib_angle, rib_quantity))

        # fused ribs
        ribs.append(TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Fuse(ribs[-1].shape(), ribs[-2].shape()).Shape(),
                                     f"{self.wing_loft.name()}_complete_ribs"))
        self.display.display_fuse(ribs[-1], ribs[-2], ribs[-3])

        # trim ribs to wing Shape
        ribs.append(TGeo.CNamedShape(OExs.translate_shp(ribs[-1].shape(), Ogp.gp_Vec(0, 0, -0.005)),
                                     f"{self.wing_loft.name()}_cmoved_ribs"))
        trimed_wing: TGeo.CNamedShape = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(self.wing_shape, ribs[-1].shape()).Shape(), f"trimed_{self.wing_loft.name()}_ribs")

        ribs.append(trimed_wing)
        self.display.display_common(ribs[-1], self.wing_loft, ribs[-2])
        self.shape = ribs[-1]
        return trimed_wing

    def get_shape(self) -> OTopo.TopoDS_Shape:
        """
        returns the shape of the created WingRIb
        """
        return self.shape

    def _make_oriented_horizontal_ribs(self, root_x_list, tip_x_list, root_y, root_z, lenght, width, height,
                                       rib_width, name) -> TGeo.CNamedShape:
        """
        Creates a multiple oriented horizontal rib.
        Paramaters
        root_x_list a list with x kordiante values where the rib should start
        tip_x_list a list with x kordiante values where the rib should end
        root_y y koordinate where the rib schould start
        root_z z koordinate where the rib schould start
        lenght, width, height parameters of the shape that is becoming the rib
        rib_width
        """
        logging.info(f"Creating horizontal ribs for {name} with {len(root_x_list)} ribs and {rib_width=}")
        ribs = []
        for i, x in enumerate(root_x_list):
            ribs.append(self._make_single_box_rib(root_x_list[i], tip_x_list[i], root_y, root_z, width, height,
                                                  rib_width, f"single_rib_{i}"))
        fused_ribs: TGeo.CNamedShape = BooleanOperationsForLists.fuse_list_of_namedshapes(ribs,
                                                                                          f"{name}_oriented_horizontal_ribs")
        return fused_ribs

    def _make_single_box_rib(self, x_inner, x_outer, y_pos, z_pos, seg_width, seg_height,
                             rib_width=0.0004, name="single_rib") -> TGeo.CNamedShape:
        """
        Creates a singl oriented horizontal rib.
        Paramaters
        x_inner a x kordiante where the rib should start
        x_outer a x kordiante where the rib should end
        y_pos y koordinate where the rib schould start
        z_pos z koordinate where the rib schould start
        seg_width, seg_height parameters of the Segment that is becoming the rib
        rib_width
        """
        corner_points = []
        # point1
        x_cor = x_inner + (rib_width / 2)
        logging.info(f"test {x_inner=:.6f} {x_cor=:.6f}")
        y_cor = y_pos
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point2
        x_cor = x_outer + (rib_width / 2)
        y_cor = y_pos + seg_width
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point3
        x_cor = x_outer - (rib_width / 2)
        y_cor = y_pos + seg_width
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        # point4
        x_cor = x_inner - (rib_width / 2)
        y_cor = y_pos
        z_cor = z_pos
        corner_points.append(gp_Pnt(x_cor, y_cor, z_cor))

        mkw = BRepBuilderAPI_MakeWire()
        for i, point in enumerate(corner_points):
            logging.info(f"Creating Edge {i + 1} from {len(corner_points)}")
            if point != corner_points[-1]:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[i + 1]).Edge())
            else:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[0]).Edge())

        logging.info(f"Creating {name} out of Edges")
        prism = BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, seg_height)),
        ).Shape()
        named_single_rib: TGeo.CNamedShape = TGeo.CNamedShape(prism, name)
        return named_single_rib

    def _create_diagonal_ribs(self, rib_width, angle, ribs_quantity=0) -> TGeo.CNamedShape:
        """
        Creates a pattern of diagonal ribs for the class wing
        """
        logging.info(f"Creating diagonal ribs: {rib_width=} {angle=} {ribs_quantity=}")
        prim = []
        # xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        # wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        prim.append(TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(self.wing_koordinates.get_length() * 2, rib_width,
                                                               self.wing_koordinates.get_height() * 1.2).Shape(),
                                     "singlerib_box"))
        prim.append(TGeo.CNamedShape(OExs.rotate_shape(prim[-1].shape(), gp_OZ(), angle), "singlerib_moved_box"))
        prim.append(TGeo.CNamedShape(
            OExs.translate_shp(prim[-1].shape(), Ogp.gp_Vec(self.wing_koordinates.get_xmin(), -rib_width,
                                                            self.wing_koordinates.get_zmin())), "singlerib"))
        # self.display.display_this_shape(prim[-1])
        if ribs_quantity == 0:
            ribs_distance = 0.1
            ribs_quantity = round((self.wing_koordinates.get_width() / ribs_distance) * 2)
        else:
            ribs_distance = self.wing_koordinates.get_width() / ribs_quantity
            ribs_quantity = ribs_quantity * 2
        prim.append(pat.create_linear_pattern(prim[-1], ribs_quantity, ribs_distance, "y"))
        prim.append(TGeo.CNamedShape(
            OExs.translate_shp(prim[-1].shape(), Ogp.gp_Vec(0, -self.wing_koordinates.get_width() / 2, 0)),
            "diagonal ribs"))
        named_diagonal_ribs: TGeo.CNamedShape = TGeo.CNamedShape(prim[-1].shape(), "diagonal ribs")
        self.display.display_this_shape(named_diagonal_ribs)
        return named_diagonal_ribs
