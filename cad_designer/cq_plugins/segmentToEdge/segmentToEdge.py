from typing import Tuple, TypeVar, Optional, Literal, Union, cast as tcast
from multimethod import multimethod

from cadquery.occ_impl.shapes import Edge
from cadquery.occ_impl.geom import Vector

from scipy.spatial.transform import Rotation as R

T = TypeVar("T", bound="Sketch")
Modes = Literal["a", "s", "i", "c"]  # add, subtract, intersect, construct
Point = Union[Vector, Tuple[Union[int, float], Union[int, float]]]

def _line(p1, p2):
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0] * p2[1] - p2[0] * p1[1])
    return A, B, -C

def _intersection(L1, L2):
    D = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x, y
    else:
        return False

_ERR_PARALLEL = "defined segment would be parallel to target edge"


def _line_segments_intersection(edge: Edge, v1: Point, v2: Point) -> Edge:
    s1 = edge.startPoint()
    s2 = edge.endPoint()
    L1 = _line([v1.x, v1.y], [v2.x, v2.y])
    L2 = _line([s1.x, s1.y], [s2.x, s2.y])
    I = _intersection(L1, L2)
    if (I == False):
        return False
    return Edge.makeLine(v1, Vector(I))


def _intersect_to_edge(self: T, v1: Vector, v2: Vector, edge: Edge, tag: Optional[str], forConstruction: bool) -> T:
    """Shared intersection logic for all segmentToEdge overloads."""
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if not val:
            raise RuntimeError(_ERR_PARALLEL)
    else:
        return self
    return self.edge(val, tag, forConstruction)


def _angle_to_direction(angle: Union[float, int], v1: Vector) -> Vector:
    """Convert an angle (degrees from +x) to a target vector relative to v1."""
    r = R.from_euler("z", angle, degrees=True)
    direction = Vector(tuple(r.apply((10.0, 0.0, 0.0))))
    return direction * 10 + v1


@multimethod
def segmentToEdge(self: T, point: Point, direction: Point, end_tag: str, tag: Optional[str] = None, forConstruction: bool = False) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the given point.

    point    : start point
    start_tag: start edge tag
    direction: direction of the segment
    end_tag  : the finale edge to reach
    """

    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(point)
    v2: Vector = Vector(direction) * 10 + v1
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)

@segmentToEdge.register
def segmentToEdge(self: T, point: Point, angle: Union[float, int], end_tag: str, tag: Optional[str] = None,
                     forConstruction: bool = False
                     ) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the given point.

    point    : start point
    angle    : direction of the segment as angle in degrees from positive x
    end_tag  : the finale edge to reach
    """

    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(point)
    v2: Vector = _angle_to_direction(angle, v1)
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, direction: Point, end_tag: str, tag: Optional[str] = None, forConstruction: bool = False
) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the last edge.

    direction: direction vector of the segment
    end_tag  : the finale edge to reach
    """

    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(self._endPoint())
    v2: Vector = Vector(direction) * 10 + v1
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, start_tag: str, direction: Point, end_tag: str, tag: Optional[str] = None,
        forConstruction: bool = False) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the tagged start edge.

    start_tag: start edge tag
    direction: direction of the segment
    end_tag  : the finale edge to reach
    """

    point = tcast(Edge, self._tags[start_tag][0]).endPoint()
    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(point)
    v2: Vector = Vector(direction) * 10 + v1
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, angle: Union[float, int], end_tag: str, tag: Optional[str] = None, forConstruction: bool = False) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the last edge.

    angle    : direction of the segment as angle in degrees from positive x
    end_tag  : the finale edge to reach
    """

    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(self._endPoint())
    v2: Vector = _angle_to_direction(angle, v1)
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, start_tag: str, angle: Union[float, int], end_tag: str, tag: Optional[str] = None,
        forConstruction: bool = False
) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the tagged start edge.

    start_tag: start edge tag
    angle    : direction of the segment as angle in degrees from positive x
    end_tag  : the finale edge to reach
    """

    point = tcast(Edge, self._tags[start_tag][0]).endPoint()
    edge = tcast(Edge, self._tags[end_tag][0])
    v1: Vector = Vector(point)
    v2: Vector = _angle_to_direction(angle, v1)
    return _intersect_to_edge(self, v1, v2, edge, tag, forConstruction)

@segmentToEdge.register
def segmentToEdge(
        self: T, start_tag: str, r: Union[float, int], end_tag: str, s: Union[float, int], tag: Optional[str] = None,
        forConstruction: bool = False) -> T:
    """
    Construction of a segment between two edges.

    start_tag: start edge tag
    r        : path parameter [0,1] 0 - start point 1 - end point but accepts also factors r > 1 or r < 0
    end_tag  : the finale edge to reach
    s        : path parameter [0,1] 0 - start point 1 - end point but accepts also factors s > 1 or s < 0
    """

    seg1 = self._tags[start_tag][0]
    start_1 = tcast(Edge, seg1).startPoint()
    end_1 = tcast(Edge, seg1).endPoint()
    point_1 = (end_1-start_1)*r + start_1

    seg2 = self._tags[end_tag][0]
    start_2 = tcast(Edge, seg2).startPoint()
    end_2 = tcast(Edge, seg2).endPoint()
    point_2 = (end_2-start_2)*s + start_2

    val = Edge.makeLine(point_1, point_2)
    return self.edge(val, tag, forConstruction)

@segmentToEdge.register
def segmentToEdge(self: T, end_tag: str, s: Union[float, int], point: Point, tag: Optional[str] = None, forConstruction: bool = False) -> T:
    """
    Construction of a segment between the point and a point on an edge segment defined by end_tag and s as
    the path parameter.

    point    : start point
    end_tag  : the finale edge to reach
    s        : path parameter [0,1] 0 - start point 1 - end point but accepts also factors s > 1 or s < 0
    point    : start point
    """

    point_1 = Vector(point)

    seg2 = self._tags[end_tag][0]
    start_2 = tcast(Edge, seg2).startPoint()
    end_2 = tcast(Edge, seg2).endPoint()
    point_2 = (end_2-start_2)*s + start_2

    val = Edge.makeLine(point_1, point_2)
    return self.edge(val, tag, forConstruction)
