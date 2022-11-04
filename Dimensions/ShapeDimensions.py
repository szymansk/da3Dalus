import logging

import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs

from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *


class ShapeDimensions:
    def __init__(self, shape: OTopo.TopoDS_Shape, name=""):
        self.shape: OTopo.TopoDS_Shape = shape
        self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax = self._calc_koordinates(shape)
        self.lenght, self.width, self.height = self._calc_dimensions_from_Shape(shape)
        self.xmid, self.ymid, self.zmid = self._calc_mid_kordinates()
        self.points = self._calc_points()
        logging.info(f"{name} dimensions {self.__str__()}")

    def _calc_koordinates(self, shape):
        bbox = Bnd_Box()
        brepbndlib_Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        return xmin, ymin, zmin, xmax, ymax, zmax

    def _calc_dimensions(self, xmin, ymin, zmin, xmax, ymax, zmax):
        xdiff = xmax - xmin
        ydiff = ymax - ymin
        zdiff = zmax - zmin
        return xdiff, ydiff, zdiff

    def _calc_dimensions_from_Shape(self, shape):
        xmin, ymin, zmin, xmax, ymax, zmax = self._calc_koordinates(shape)
        xdiff, ydiff, zdiff = self._calc_dimensions(xmin, ymin, zmin, xmax, ymax, zmax)
        return xdiff, ydiff, zdiff

    def _calc_mid_kordinates(self):
        xmid = self.xmin + (self.lenght / 2)
        ymid = self.ymin + (self.width / 2)
        zmid = self.zmin + (self.height / 2)
        return xmid, ymid, zmid

    def _calc_points(self) -> list:
        point0 = Ogp.gp_Pnt(self.xmid, self.ymid, self.zmid)
        point1 = Ogp.gp_Pnt(self.xmin, self.ymin, self.zmin)
        point2 = Ogp.gp_Pnt(self.xmax, self.ymin, self.zmin)
        point3 = Ogp.gp_Pnt(self.xmax, self.ymax, self.zmin)
        point4 = Ogp.gp_Pnt(self.xmin, self.ymax, self.zmin)
        point5 = Ogp.gp_Pnt(self.xmin, self.ymin, self.zmax)
        point6 = Ogp.gp_Pnt(self.xmax, self.ymin, self.zmax)
        point7 = Ogp.gp_Pnt(self.xmax, self.ymax, self.zmax)
        point8 = Ogp.gp_Pnt(self.xmin, self.ymax, self.zmax)
        points = [point0, point1, point2, point3, point4, point5, point6, point7, point8]
        return points

    def get_xmin(self) -> float:
        return self.xmin

    def get_ymin(self) -> float:
        return self.ymin

    def get_zmin(self) -> float:
        return self.zmin

    def get_xmid(self) -> float:
        return self.xmid

    def get_ymid(self) -> float:
        return self.ymid

    def get_zmid(self) -> float:
        return self.zmid

    def get_xmax(self) -> float:
        return self.xmax

    def get_ymax(self) -> float:
        return self.ymax

    def get_zmax(self) -> float:
        return self.zmax

    def get_length(self) -> float:
        return self.lenght

    def get_width(self) -> float:
        return self.width

    def get_height(self) -> float:
        return self.height

    def get_point(self, index) -> gp_Pnt:
        return self.points[index]

    def get_points(self):
        return self.points

    def __str__(self) -> str:
        return f"{self.xmin=:.4f}, {self.ymin=:.4f}, {self.zmin=:.4f}, {self.xmid=:.4f}, {self.ymid=:.4f}, {self.zmid=:.4f}, {self.xmax=:.4f}, {self.ymax=:.4f}, {self.zmax=:.4f}, { self.lenght=:.4f}, {self.width=:.4f}, { self.height=:.4f}"

    def get_koordinates_on_achs(self, quantity):
        x_diff = self.get_length() / (quantity + 1)
        x_list = []
        for i in range(1, quantity + 1):
            new_x = self.get_xmin() + (i * x_diff)

            x_list.append(new_x)
        logging.info(f"{x_list=}")
        return x_list

    def get_bounding_box_shape(self):
        return OPrim.BRepPrimAPI_MakeBox(self.points[1], self.lenght, self.width, self.height).Shape()


if __name__ == "__main__":
    m = myDisplay.instance(True)
    box = OPrim.BRepPrimAPI_MakeBox(3, 4, 5).Shape()
    moved_box = OExs.translate_shp(box, Ogp.gp_Vec(1, 2, 3))
    box_dimensions = ShapeDimensions(moved_box)
    m.display_in_origin(moved_box, True)
    for i, point in enumerate(box_dimensions.get_points()):
        m.display_point_in_origin(point, 0.1, str(i))
    m.start()
