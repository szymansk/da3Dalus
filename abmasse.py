#!/usr/bin/env python
# coding: utf-8

from __future__ import print_function
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box



# In[ ]:


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

def get_koordinate(shape, koordinate_name="xmin"):
    bbox = Bnd_Box()
    brepbndlib_Add(shape,bbox)
    xmin,ymin,zmin,xmax,ymax,zmax = bbox.Get()
    koordinate_dict={"xmin":xmin,"ymin": ymin, "zmin": zmin, "xmax":xmax, "ymax": ymax, "zmax":zmax}#
    return koordinate_dict.get(koordinate_name)