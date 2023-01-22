import logging

import OCP.BRepPrimAPI as OPrim
import OCP.TopoDS as OTopo
import OCP.gp as Ogp
#from OCP.BRepBndLib import brepbndlib_Add
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box

from OCP.TopoDS import TopoDS_Shape
import cadquery as cq

class ShapeDimensions:
    """
    Provides information about the bounding box of the given shape, length, width, height and corner points
    """

    def __init__(self, named_shape: TopoDS_Shape) -> None:
        self.named_shape: TopoDS_Shape = named_shape
        self.x_min, self.y_min, self.z_min, self.x_max, self.y_max, self.z_max = self._calc_coordinates(
            named_shape)
        self.lenght, self.width, self.height = self._calc_dimensions_from_Shape(named_shape)
        self.x_mid, self.y_mid, self.z_mid = self._calc_mid_coordinates()
        self.points = self._calc_points()
        # logging.debug(f"{named_shape.name()} dimensions {self.__str__()}")

    def _calc_coordinates(self, shape: OTopo.TopoDS_Shape) -> (float, float, float, float, float, float):
        '''
        calculates the max and min coordinates of the 3-axis (x,y,z)
        :param shape: TopoDS_Shape
        :return: x_min, y_min, z_min, x_max, y_max, z_max
        '''
        bbox = cq.CQ(shape).findSolid().BoundingBox()
        return bbox.xmin, bbox.ymin, bbox.zmin, bbox.xmax, bbox.ymax, bbox.zmax

    def _calc_dimensions(self, x_min, y_min, z_min, x_max, y_max, z_max) -> (float, float, float):
        '''
        Calculates the difference between coordinates on the 3-axis (x,y,z) from the min and max values of the axes
        :param x_min: float
        :param y_min: float
        :param z_min: float
        :param x_max: float
        :param y_max: float
        :param z_max: float
        :return: x_diff, y_diff, z_diff
        '''
        x_diff = x_max - x_min
        y_diff = y_max - y_min
        z_diff = z_max - z_min
        return x_diff, y_diff, z_diff

    def _calc_dimensions_from_Shape(self, shape) -> (float, float, float):
        '''
        Calculates the length, width and height of the shapes bounding box
        :param shape: TopoDS_Shape
        :return: (float, float, float)
        '''
        x_min, y_min, z_min, x_max, y_max, z_max = self._calc_coordinates(shape)
        x_diff, y_diff, z_diff = self._calc_dimensions(x_min, y_min, z_min, x_max, y_max, z_max)
        return x_diff, y_diff, z_diff

    def _calc_mid_coordinates(self) -> (float, float, float):
        '''
        calculates the mid x,y,z coordinates of the shape.
        coordinate between min and max
        :return: (x_mid, y_mid, z_mid)
        '''
        x_mid = self.x_min + (self.lenght / 2)
        y_mid = self.y_min + (self.width / 2)
        z_mid = self.z_min + (self.height / 2)
        return x_mid, y_mid, z_mid

    def _calc_points(self) -> list[Ogp.gp_Pnt]:
        """
        calculates all 8 corner points of the shape bounding box
        and the middle point(0)
        point(1) ist the corner with all the minimum coordinates.
        the next corners are calculated counterclockwise
        :return: the 8 corner points as list
        """
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

    def get_x_min(self) -> float:
        return self.x_min

    def get_y_min(self) -> float:
        return self.y_min

    def get_z_min(self) -> float:
        return self.z_min

    def get_x_mid(self) -> float:
        return self.x_mid

    def get_y_mid(self) -> float:
        return self.y_mid

    def get_z_mid(self) -> float:
        return self.z_mid

    def get_x_max(self) -> float:
        return self.x_max

    def get_y_max(self) -> float:
        return self.y_max

    def get_z_max(self) -> float:
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
        Returns a list of x-coordinates evenly distributed on the x-axis of the shape
        :param quantity: int
        :return: list[float]
        '''
        x_diff = self.get_length() / (quantity + 1)
        x_coordinates = []
        for i in range(1, quantity + 1):
            new_x = self.get_x_min() + (i * x_diff)
            x_coordinates.append(new_x)
        logging.debug(f"{self.named_shape.name()} {x_coordinates=}")
        return x_coordinates

    def get_bounding_box_shape(self) -> OTopo.TopoDS_Shape:
        '''
        returns a Shape of the bounding box
        :return: opoDS_Shape
        '''
        return OPrim.BRepPrimAPI_MakeBox(self.points[1], self.lenght, self.width, self.height).Shape()
