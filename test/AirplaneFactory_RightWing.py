import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

import Airplane.AirplaneFactory as ap
import Airplane.ReinforcementPipeFactory as rpf
import Airplane.Wing.CablePipeFactory as cp
import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.ServoRecessFactory as srf
import Airplane.Wing.WingFactory as wf
import Airplane.Wing.WingRibFactory as wrf
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 6)
    tigl_h = tg.get_tigl_handler("simple_aircraft_v2")
    test_class = ap.AirplaneFactory(tigl_h)
    test_class.create_wing(1, "right_wing")
    m.start()
