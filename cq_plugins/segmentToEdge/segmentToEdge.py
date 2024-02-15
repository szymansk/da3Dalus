from typing import Tuple, TypeVar, Optional, Literal, Union, cast as tcast
from multimethod import multimethod

from cadquery.occ_impl.shapes import Edge
from cadquery.occ_impl.geom import Vector

from scipy.spatial.transform import Rotation as R

T = TypeVar("T", bound="Sketch")
Modes = Literal["a", "s", "i", "c"]  # add, subtract, intersect, construct
Point = Union[Vector, Tuple[float, float]]

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

def _line_segments_intersection(edge: Edge, v1: Point, v2: Point) -> Edge:
    s1 = edge.startPoint()
    s2 = edge.endPoint()
    L1 = _line([v1.x, v1.y], [v2.x, v2.y])
    L2 = _line([s1.x, s1.y], [s2.x, s2.y])
    I = _intersection(L1, L2)
    if (I == False):
        return False
    return Edge.makeLine(v1, Vector(I))

@multimethod
def segmentToEdge(self: T, point: Point, direction: Point, end_tag: str, tag: Optional[str] = None,
                     forConstruction: bool = False
                     ) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the given point.

    point.   : start point
    start_tag: start edge tag
    direction: direction of the segment
    end_tag  : the finale edge to reach
    """

    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    v2: Vector = Vector(direction) * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
    # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(self: T, point: Point, angle: Union[float, int], end_tag: str, tag: Optional[str] = None,
                     forConstruction: bool = False
                     ) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the given point.

    point.   : start point
    start_tag: start edge tag
    angle    : direction of the segment as angle in degrees from positive x
    end_tag  : the finale edge to reach
    """

    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    r = R.from_euler('z', angle, degrees=True)
    direction = Vector(tuple(r.apply((10., 0., 0.))))  # x-unit vector rotate by root_incidence
    v2: Vector = Vector(direction) * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
            # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)


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

    point = self._endPoint()
    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    v2: Vector = direction * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
    # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, start_tag: str, direction: Point, end_tag: str, tag: Optional[str] = None,
        forConstruction: bool = False
) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the tagged start edge.

    start_tag: start edge tag
    direction: direction of the segment
    end_tag  : the finale edge to reach
    """

    seg1 = self._tags[start_tag][0]
    point = tcast(Edge, seg1).endPoint()

    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    v2: Vector = direction * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
    # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)


@segmentToEdge.register
def segmentToEdge(
        self: T, angle: Union[float, int], end_tag: str, tag: Optional[str] = None, forConstruction: bool = False
) -> T:
    """
    Construction of a segment that stops at the given tagged end edge.
    Starting at the end point of the last edge.

    angle    : direction of the segment as angle in degrees from positive x
    end_tag  : the finale edge to reach
    """

    point = self._endPoint()
    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    r = R.from_euler('z', angle, degrees=True)
    direction = Vector(tuple(r.apply((10., 0., 0.))))  # x-unit vector rotate by root_incidence
    v2: Vector = direction * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
    # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)


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

    seg1 = self._tags[start_tag][0]
    point = tcast(Edge, seg1).endPoint()

    seg2 = self._tags[end_tag][0]
    edge = tcast(Edge, seg2)
    v1: Vector = Vector(point)
    r = R.from_euler('z', angle, degrees=True)
    direction = Vector(tuple(r.apply((10., 0., 0.))))  # x-unit vector rotate by root_incidence
    v2: Vector = direction * 10 + v1

    # dispatch on geom type
    if edge.geomType() == "LINE":
        val = _line_segments_intersection(edge, v1, v2)
        if (val == False):
            return self
    # elif v0.geomType() == "CIRCLE":
    else:
        return self

    return self.edge(val, tag, forConstruction)
