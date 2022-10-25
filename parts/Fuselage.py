from __future__ import print_function

from math import radians
from re import A
from turtle import Shape
from unicodedata import mirrored


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
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

from factories.RibFactory import *
from parts.Wing import *
from parts.Rib import *
import logging

from _alt.abmasse import *
from stl_exporter.Ausgabeservice import *
from _alt.Aussparungen import *
from _alt.Innenstruktur import *
from _alt.shape_verschieben import *
from _alt.Wand_erstellen import *

class Fuselage:
    def __init__(self) -> None:
        self.prim= OrderedDict()
        self.compound=OrderedDict()
        self.loft: TGeo.CNamedShape=None
        self.shape: OTopo.TopoDS_Shape= None
        self.hollow: OTopo.TopoDS_Shape= None
        self.with_ribs: OTopo.TopoDS_Shape= None
        self.cutted= TGeo.CNamedShape= None
        self.type:str=type
        
        
    def calculate_koordinates(self) :
        bbox = Bnd_Box()
        brepbndlib_Add(self.shape,bbox)
        self.xmin, self.ymin, self.zmin, self.xmax,self.ymax,self.zmax = bbox.Get()

    def calculate_outter_dimensions(self):
        self.lenght = self.xmax - self.xmin
        self.height = self.zmax - self.zmin
        self.width = self.ymax - self.ymin
        
    def __str__(self) -> str:
        return "Fuselage:", "xmin:" ,"{:.2f}".format(self.xmin), "ymin" ,"{:.2f}".format(self.ymin), "zmin:", "{:.2f}".format(self.zmin), "xmax:", "{:.2f}".format(self.xmax), "ymax:", "{:.2f}".format(self.ymax), "zmax:", "{:.2f}".format(self.zmax), "\nlenght:", "{:.2f}".format(self.lenght), "width:", "{:.2f}".format(self.width), "height:", "{:.2f}".format(self.height)
    