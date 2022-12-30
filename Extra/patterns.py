import logging
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp
from Extra.BooleanOperationsForLists import *
import Extra.ConstructionStepsViewer as myDisplay

def create_linear_pattern(namedshape, quantity, distance, direction="x") -> TGeo.CNamedShape:
    pattern = namedshape.shape()
    logstr = f"Creating a linear pattern of {namedshape.name()} with {quantity} x {distance} meters"
    logging.debug(logstr)
    x, y, z = 0.0, 0.0, 0.0
    for i in range(1, quantity):
        if direction == "x":
            x = i * distance
        if direction == "y":
            y = i * distance
        if direction == "z":
            z = i * distance
        moved_shape = OExs.translate_shp(namedshape.shape(), Ogp.gp_Vec(x, y, z))
        newpattern = OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
        pattern = newpattern
    result = TGeo.CNamedShape(pattern, f"{namedshape.name()}_pattern")
    return result


def create_circular_pattern_around_xaxis(namedshape, quantity, bound=360, start=0) -> TGeo.CNamedShape:
    shapes = []
    logging.debug(f"Creating a circular pattern with {quantity} elements, around {bound} degress starting at {start}")

    d_angle = bound / quantity
    for i in range(quantity):
        angle = start + i * d_angle
        shapes.append(
            TGeo.CNamedShape(OExs.rotate_shape(namedshape.shape(), Ogp.gp_OX(), angle), f"{namedshape.name()}_{i}"))

    result = BooleanCADOperation.fuse_list_of_namedshapes(shapes, namedshape.name())
    return result
