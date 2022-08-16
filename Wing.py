#!/usr/bin/env python
# coding: utf-8

# In[1]:


from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored
from xmlrpc.client import boolean


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as TExp
import tigl3.geometry
import tigl3.geometry as TGeo
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
    
    def __init__(self, cpacs_wing_configuration:TConfig.CCPACSConfiguration,nr, name) -> None:
        self.cpacs_wing_configuration: TConfig.CCPACSConfiguration= cpacs_wing_configuration
        self.cpacs_wing: TConfig.CCPACSWing= cpacs_wing_configuration.get_wing(nr)
        wing_loft: TGeo.CNamedShape= self.cpacs_wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape= wing_loft.shape()
        self.wing_hollow: OTopo.TopoDS_Shape= None
        self.rib:None
        print("Wing", wing_loft.name, "was initialized")
    
    
    def get_wingspan(self):
        return self.cpacs_wing.get_wingspan()
    
    def has_mirrored_shape(self) -> boolean:     
        mirorred_loft= self.cpacs_wing.get_mirrored_loft
        return mirorred_loft!= None
    
