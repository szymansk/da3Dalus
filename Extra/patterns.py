import logging
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp
from Extra.BooleanOperationsForLists import *

def create_linear_pattern(shape, quantity, distance,direction="x"):
    pattern=shape
    logstr= f"Creating a linear pattern of {quantity} x {distance} meters"
    logging.info(logstr)
    x,y,z=0.0,0.0,0.0
    for i in range(1, quantity):
        if direction == "x":
            x = i * distance
        if direction == "y":
            y = i * distance
        if direction == "z":
            z = i * distance
        moved_shape = OExs.translate_shp(shape, Ogp.gp_Vec(x, y, z))
        newpattern = OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
        pattern = newpattern
    return pattern


def create_circular_pattern(shape, quantity, bound=360, start=0):
    shapes = []
    logging.info(f"Creating a circular pattern with {quantity} elements, around {bound} degress starting at {start}")

    d_angle = bound / quantity
    for i in range(quantity):
        angle = start + i * d_angle
        shapes.append(OExs.rotate_shape(shape, Ogp.gp_OX(), angle))

    result = fuse_list_of_shapes(shapes)
    return result
