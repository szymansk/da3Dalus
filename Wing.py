#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as config3
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as geo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *

class Wing:
    
    def __init__(self,thikness) -> None:
        self.solid_wing= None
        self.holow_wing= None
        self.thikness= thikness
        self.rib:None
    
    
