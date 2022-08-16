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

from RibFactory import *
from Wing import *
from Rib import *

from abmasse import *
from Ausgabeservice import *
from Aussparungen import *
from Innenstruktur import *
from shape_verschieben import *
from Wand_erstellen import *

class WingFactory:
    def __init__(self, wing_configuration) -> None:
        self.wing:Wing= Wing(wing_configuration)
        self.rib_factory: RibFactory= RibFactory()
        
    def create_solid_wing(self, wing:Wing):
        pass
    
    def create_holow_wing(self, thickness:float):
        self.wing.wing_hollow= create_hollowedsolid(thickness)
    
    def create_mirrored_wing(self) -> Wing:
        if self.wing.has_mirrored_shape:
            # Set up the mirror
                aTrsf= Ogp.gp_Trsf()
                aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0,0,0),Ogp.gp_Dir(0,1,0)))
                # Apply the mirror transformation
                aBRespTrsf = OBuilder.BRepBuilderAPI_Transform(verbunden, aTrsf)

                # Get the mirrored shape back out of the transformation and convert back to a wire
                aMirroredShape = aBRespTrsf.Shape()
                aMirroredShape
                
                fluegelgesamt=OAlgo.BRepAlgoAPI_Fuse(verbunden,aMirroredShape).Shape()
            
    
    
    def add_ribs(self):
        pass
    
    def calculate_ribs_quantity(self, spacing):
        return self.wing.get_wingspan()/spacing
    
        