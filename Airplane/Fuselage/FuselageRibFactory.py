import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
from OCC.Core.TopoDS import TopoDS_Shape

import Dimensions.ShapeDimensions as PDim
import Extra.BooleanOperationsForLists as BOl
import Extra.patterns as pat
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
from _alt.abmasse import *


class FuselageRibFactory:
    """
    This class is used to create the Ribs for the given wing_index.
    After initializing the class, call one of the create methods
    """

    def __init__(self, fuselage_shape, wing_shape):
        self.display = myDisplay.instance()
        logging.info(f"Initilizing FuselageRibFactory")
        self.fuselage_shape = fuselage_shape
        self.fuselage_koordinates = PDim.ShapeDimensions(self.fuselage_shape)
        self.wing_shape = wing_shape
        self.wing_koordinates = PDim.ShapeDimensions(self.wing_shape)
        self.ribwidth = None
        self.factor = None

        self.shape: OTopo.TopoDS_Shape = OTopo.TopoDS_Shape()
        self.shapes: list = []

    def create_sharp_ribs(self, rib_width, y_max, y_min, z_max, z_min):
        """
        Create a rib cage with a # profile
        :param rib_width:
        :param y_max: postion of the first vertikal rib
        :param y_min: postion of the second vertikal rib
        :param z_max: postion of the first horizontal rib
        :param z_min: postion of the first horizontal rib
        :return:
        """
        logstr = f"Quadrat ribs: x_pos=0 y_max={y_max:.3f} y_min={y_min:.3f} z_max={z_max:.3f} z_min={z_min:.3f}"
        logging.info(logstr)
        rib_lenght = self.fuselage_koordinates.get_length() * 1.2
        rib_height = self.fuselage_koordinates.get_height() * 1.2
        box = OPrim.BRepPrimAPI_MakeBox(rib_lenght, rib_width, rib_height).Shape()
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(-rib_lenght * 0.1, -rib_width / 2, 0))

        # vertikal ribs
        logging.info(f"Creating vertikal ribs")
        ver_rib = moved_box
        ver_rib_1 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_max, self.fuselage_koordinates.get_zmin()))
        ver_rib_2 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_min, self.fuselage_koordinates.get_zmin()))

        # Horizontal ribs
        logging.info(f"Creating Horizontal ribs")
        hor_rib = OExs.rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_1 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, rib_height / 2, z_max))
        hor_rib_2 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, rib_height / 2, z_min))

        # Fuse all ribs
        ribs: list[TopoDS_Shape] = [ver_rib_1, ver_rib_2, hor_rib_1, hor_rib_2]
        fused_ribs = BOl.fuse_list_of_shapes(ribs)

        return fused_ribs

    def get_shape(self) -> OTopo.TopoDS_Shape:
        """
        returns the shape of the created WingRIb
        """
        return self.shape

    def _make_single_box_rib(self, x_inner, x_outer, y_pos, z_pos, seg_lenght, seg_width, seg_height,
                             rib_width=0.0004) -> OTopo.TopoDS_Shape:
        """
        Creates a singl oriented horizontal rib.
        Paramaters
        x_inner a x kordiante where the rib should start
        x_outer a x kordiante where the rib should end
        y_pos y koordinate where the rib schould start
        z_pos z koordinate where the rib schould start
        seg_lenght, seg_width, seg_height parameters of the Segment that is becoming the rib
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
            logging.info(f"Creating Edge {i} from {len(corner_points)}")
            if point != corner_points[-1]:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[i + 1]).Edge())
            else:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[0]).Edge())

        logging.info(f"Creating Prism out of Edges")
        prism = BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, seg_height)),
        ).Shape()
        # m.display_in_origin(prism)
        return prism

    def _create_diagonal_ribs(self, rib_width, angle, ribs_quantity=0) -> OTopo.TopoDS_Shape:
        """
        Creates a pattern of diagonal ribs for the class wing
        """
        logging.info(f"Creating diagonal ribs: {rib_width=} {angle=} {ribs_quantity=}")
        prim = []
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        prim.append(OPrim.BRepPrimAPI_MakeBox(self.wing_koordinates.get_length() * 2, rib_width,
                                              self.wing_koordinates.get_height()).Shape())
        prim.append(OExs.rotate_shape(prim[-1], gp_OZ(), angle))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(xmin, -rib_width, zmin)))
        # self.display.display_this_shape(prim[-1])
        if ribs_quantity == 0:
            ribs_distance = 0.1
            ribs_quantity = round((wing_width / ribs_distance) * 2)
            logging.debug(f"{ribs_quantity=} {wing_width}")
        else:
            ribs_distance = wing_width / ribs_quantity
            ribs_quantity = ribs_quantity * 2
        prim.append(pat.create_linear_pattern(prim[-1], ribs_quantity, ribs_distance, "y"))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(0, -wing_width / 2, 0)))
        self.display.display_this_shape(prim[-1])
        self.shape = prim[-1]
        return prim[-1]
