#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from operator import length_hint
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box

dimensions_mainwing={}
dimensions_fuselage={}

def claculate_mainwing_dimension(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    global dimensions_mainwing
    dimensions_mainwing = {"x_min": xmin, "y_min": ymin, "z_min": zmin,
                           "x_max": xmax, "y_max": ymax, "z_max": zmax,
                           "lenght": xmax - xmin, "width": ymax - ymin, "height": zmax - zmin,
                           "x_mid": (xmax - xmin) / 2, "y_mid": ymax - ymin, "z_mid": zmax - zmin
                           }
    print(dimensions_mainwing)

def claculate_fuselage_dimension(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    global dimensions_fuselage
    dimensions_fuselage = {"x_min": xmin, "y_min": ymin, "z_min": zmin,
                           "x_max": xmax, "y_max": ymax, "z_max": zmax,
                           "lenght": xmax - xmin, "width": ymax - ymin, "height": zmax - zmin,
                           "x_mid": (xmax - xmin) / 2, "y_mid": ymax - ymin, "z_mid": zmax - zmin
                           }

def get_fuselage_dimensions():
    length=dimensions_fuselage("lenght")
    width=dimensions_fuselage("width")
    height=dimensions_fuselage("height")
    return length, width, height

def get_mainwing_dimensions():
    length=dimensions_mainwing("lenght")
    width=dimensions_mainwing("width")
    height=dimensions_mainwing("height")
    return length, width, height
    
#class abmessungen:
def get_koordinates(shape) :
    bbox = Bnd_Box()
    brepbndlib_Add(shape,bbox)
    xmin,ymin,zmin,xmax,ymax,zmax = bbox.Get()
    return xmin, ymin, zmin,xmax,ymax,zmax

def get_dimensions(xmin,ymin,zmin,xmax,ymax,zmax):
    xdiff = xmax - xmin
    ydiff = ymax - ymin
    zdiff = zmax - zmin
    return xdiff,ydiff,zdiff

def get_dimensions_from_Shape(shape):
    xmin, ymin, zmin,xmax,ymax,zmax=get_koordinates(shape)
    xdiff,ydiff,zdiff= get_dimensions(xmin, ymin, zmin,xmax,ymax,zmax)
    return xdiff, ydiff, zdiff


def get_koordinate(shape, koordinate_name="x_min"):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    global koordinate_dict
    koordinate_dict = {"x_min": xmin, "y_min": ymin, "z_min": zmin, "x_max": xmax, "y_max": ymax, "z_max": zmax}
    return koordinate_dict.get(koordinate_name)


'''
XMIN=None
XMAX=None
YMIN=None
YMAX=None
ZMIN=None
ZMAX=None
HEIGHT=None
WIDTH=None
LENGHT=None

XMIN=None
XMAX=None
YMIN=None
YMAX=None
ZMIN=None
ZMAX=None
HEIGHT=None
WIDTH=None
LENGHT=None

def claculate_koordinates(shape):
    global XMIN
    global XMAX
    global YMIN= get_koordinate(shape, "y_min")
    
    YMAX=None
    ZMIN=None
    ZMAX=None
    '''
