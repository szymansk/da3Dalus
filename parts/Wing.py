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
import logging
from OCC.Display.SimpleGui import init_display

from _alt.abmasse import *
from stl_exporter.Ausgabeservice import *
from _alt.Aussparungen import *
from _alt.Innenstruktur import *
from parts.Rib import *
from _alt.shape_verschieben import *
from _alt.Wand_erstellen import *


class Wing:
    
    def __init__(self) -> None:
        logging.info("Wing init")
        self.shape: OTopo.TopoDS_Shape= None
        self.hollow: OTopo.TopoDS_Shape= None
        self.with_ribs: OTopo.TopoDS_Shape= None
        self.mirrored_shape: OTopo.TopoDS_Shape= None
        self.mirrored_with_ribs: OTopo.TopoDS_Shape= None
        self.complete:OTopo.TopoDS_Shape= None
        """         
        self.rib= None
        self.ribs= None
        self.rib_profile=None
        self.rib_spacing=None
        self.rib_height= None
        self.rib_thikness= None
        self.rib_extrude_lenght= None
         """
        self.rib:Rib=Rib()
        self.type:str=type
        self.xmin:float=None
        self.ymin:float=None
        self.zmin:float=None
        self.xmax:float=None
        self.ymax:float=None
        self.zmax:float=None
        self.lenght:float=None
        self.width:float=None
        self.height:float=None    
    
    def get_wingspan(self):
        return self.cpacs_wing.get_wingspan()
    
    def has_mirrored_shape(self) -> boolean:     
        mirorred_loft= self.cpacs_wing.get_mirrored_loft
        return mirorred_loft!= None
    
    def calculate_koordinates(self) :
        bbox = Bnd_Box()
        brepbndlib_Add(self.shape,bbox)
        self.xmin, self.ymin, self.zmin, self.xmax,self.ymax,self.zmax = bbox.Get()

    def calculate_outter_dimensions(self):
        self.width = self.xmax - self.xmin
        self.height = self.zmax - self.zmin
        self.lenght = self.ymax - self.ymin

    def __str__(self) -> str:
        return "Wing:", "xmin:" ,"{:.2f}".format(self.xmin), "ymin" ,"{:.2f}".format(self.ymin), "zmin:", "{:.2f}".format(self.zmin), "xmax:", "{:.2f}".format(self.xmax), "ymax:", "{:.2f}".format(self.ymax), "zmax:", "{:.2f}".format(self.zmax), "\nlenght:", "{:.2f}".format(self.lenght), "width:", "{:.2f}".format(self.width), "height:", "{:.2f}".format(self.height)
