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
    m = myDisplay.myDisplay.instance(True, 1, False)
    tigl_h = tg.get_tigl_handler("aircombat_v14")
    test_class = ap.AirplaneFactory(tigl_h)
    # test_class.create_right_mainwing()
    # test_class.create_left_mainwing()
    # test_class.create_fuselage()
    test_class.create_airplane()
    m.start()
