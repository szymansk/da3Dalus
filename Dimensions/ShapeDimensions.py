import logging

import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import tigl3.geometry as TGeo
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box


class ShapeDimensions:
    '''
    provides information about the boundingbox of the given shape, lenght, width, height and corner points
    '''

    def __init__(self, named_shape: TGeo.CNamedShape) -> None:
        self.named_shape: TGeo.CNamedShape = named_shape
        self.x_min, self.y_min, self.z_min, self.x_max, self.y_max, self.z_max = self._calc_coordinates(
            named_shape.shape())
        self.lenght, self.width, self.height = self._calc_dimensions_from_Shape(named_shape.shape())
        self.x_mid, self.y_mid, self.z_mid = self._calc_mid_kordinates()
        self.points = self._calc_points()
        # logging.info(f"{named_shape.name()} dimensions {self.__str__()}")

    def _calc_coordinates(self, shape: OTopo.TopoDS_Shape) -> (float, float, float, float, float, float):
        '''
        calculates the max and min coordinates of the 3-axis (x,y,z)
        :param shape: TopoDS_Shape
        :return: x_min, y_min, z_min, x_max, y_max, z_max
        '''
        bbox = Bnd_Box()
        brepbndlib_Add(shape, bbox)
        x_min, y_min, z_min, x_max, y_max, z_max = bbox.Get()
        return x_min, y_min, z_min, x_max, y_max, z_max

    def _calc_dimensions(self, x_min, y_min, z_min, x_max, y_max, z_max) -> (float, float, float):
        '''
        Calculates the diference between kordinates on the 3-axis (x,y,z)
        :param xmin: float
        :param ymin: float
        :param zmin: float
        :param xmax: float
        :param ymax: float
        :param zmax: float
        :return: xdiff, ydiff, zdiff
        '''
        x_diff = x_max - x_min
        y_diff = y_max - y_min
        z_diff = z_max - z_min
        return x_diff, y_diff, z_diff

    def _calc_dimensions_from_Shape(self, shape) -> (float, float, float):
        '''
        Calculates the leght, width and height of the shapes bounding box
        :param shape: TopoDS_Shape
        :return: (float, float, float)
        '''
        x_min, y_min, z_min, x_max, y_max, z_max = self._calc_coordinates(shape)
        x_diff, y_diff, z_diff = self._calc_dimensions(x_min, y_min, z_min, x_max, y_max, z_max)
        return x_diff, y_diff, z_diff

    def _calc_mid_kordinates(self) -> (float, float, float):
        '''
        calculates the mid x,y,z coordinates of the shape.
        coordinate between min and max
        :return: (x_mid, y_mid, z_mid)
        '''
        xmid = self.x_min + (self.lenght / 2)
        ymid = self.y_min + (self.width / 2)
        zmid = self.z_min + (self.height / 2)
        return xmid, ymid, zmid

    def _calc_points(self) -> list[Ogp.gp_Pnt]:
        '''
        calculates all 8 corner points of the shape bounding box
        and the middle point(0)
        point(1) ist the corner with all the minimum kordinates.
        the next corners are calculated counterclockwise
        :return:
        '''
        point0 = Ogp.gp_Pnt(self.x_mid, self.y_mid, self.z_mid)
        point1 = Ogp.gp_Pnt(self.x_min, self.y_min, self.z_min)
        point2 = Ogp.gp_Pnt(self.x_max, self.y_min, self.z_min)
        point3 = Ogp.gp_Pnt(self.x_max, self.y_max, self.z_min)
        point4 = Ogp.gp_Pnt(self.x_min, self.y_max, self.z_min)
        point5 = Ogp.gp_Pnt(self.x_min, self.y_min, self.z_max)
        point6 = Ogp.gp_Pnt(self.x_max, self.y_min, self.z_max)
        point7 = Ogp.gp_Pnt(self.x_max, self.y_max, self.z_max)
        point8 = Ogp.gp_Pnt(self.x_min, self.y_max, self.z_max)
        points = [point0, point1, point2, point3, point4, point5, point6, point7, point8]
        return points

    def get_xmin(self) -> float:
        return self.x_min

    def get_ymin(self) -> float:
        return self.y_min

    def get_zmin(self) -> float:
        return self.z_min

    def get_xmid(self) -> float:
        return self.x_mid

    def get_ymid(self) -> float:
        return self.y_mid

    def get_zmid(self) -> float:
        return self.z_mid

    def get_xmax(self) -> float:
        return self.x_max

    def get_ymax(self) -> float:
        return self.y_max

    def get_zmax(self) -> float:
        return self.z_max

    def get_length(self) -> float:
        return self.lenght

    def get_width(self) -> float:
        return self.width

    def get_height(self) -> float:
        return self.height

    def get_point(self, index) -> Ogp.gp_Pnt:
        return self.points[index]

    def get_points(self):
        return self.points

    def __str__(self) -> str:
        return f"{self.x_min=:.4f}, {self.y_min=:.4f}, {self.z_min=:.4f}, {self.x_mid=:.4f}, {self.y_mid=:.4f}, {self.z_mid=:.4f}, {self.x_max=:.4f}, {self.y_max=:.4f}, {self.z_max=:.4f}, { self.lenght=:.4f}, {self.width=:.4f}, { self.height=:.4f}"

    def get_coordinates_on_axis(self, quantity: int) -> list[float]:
        '''
        Returns a list of x-cordinates evenly distributed on the x achis of the shape
        :param quantity: int
        :return: list[float]
        '''
        x_diff = self.get_length() / (quantity + 1)
        x_coordinates = []
        for i in range(1, quantity + 1):
            new_x = self.get_xmin() + (i * x_diff)
            x_coordinates.append(new_x)
        logging.info(f"{self.named_shape.name()} {x_coordinates=}")
        return x_coordinates

    def get_bounding_box_shape(self) -> OTopo.TopoDS_Shape:
        '''
        returns a Shape of the boundingbox
        :return: opoDS_Shape
        '''
        return OPrim.BRepPrimAPI_MakeBox(self.points[1], self.lenght, self.width, self.height).Shape()
