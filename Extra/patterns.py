import logging
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp

def create_linear_pattern(shape, quantity, distance,direction="x"):
    pattern=shape
    logstr= f"Creating a linear pattern of {quantity} x {distance} meters"
    logging.info(logstr)
    x,y,z=0.0,0.0,0.0
    for i in range(1,quantity):
        if direction=="x":
            x= i*distance
        if direction=="y":
            y= i*distance
        if direction=="z":
            z= i*distance
        moved_shape= OExs.translate_shp(shape,Ogp.gp_Vec(x,y,z))
        newpattern= OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
        pattern=newpattern
    return pattern