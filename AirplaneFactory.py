from tixi3 import tixi3wrapper
from tigl3 import tigl3wrapper
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

class AirplaneFacory:
    def __init__(self, cpacs_filename) -> None:
        self.cpacs_filename= cpacs_filename
        self.tixi_handler, self.tigl_handler= self.cpacs_einlesen(cpacs_filename)
        self.airplane_configuration= self.get_configuration() 

    def cpacs_einlesen(self,filename):
        #self.filename=filename
        tixi_h = tixi3wrapper.Tixi3()
        tigl_h = tigl3wrapper.Tigl3()
        tixi_h.open(filename)
        tigl_h.open(tixi_h, "")

        return tixi_h, tigl_h
    
    def get_configuration(self):
        mgr = tigl3.configuration.CCPACSConfigurationManager_get_instance()
        return mgr.get_configuration(self.tigl_handler._handle.value)
    
    def create_airplane(self):
        pass
    
    