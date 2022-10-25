import Airplane.Wing.WingFactory as wf
import Airplane.Wing.WingRibFactory as wrf
import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.CablePipe as cp
import Airplane.ReinforcementPipeFactory as rpf
import Extra.tigl_extractor as tg
import Extra.mydisplay as myDisplay

m=myDisplay.myDisplay.instance(True,6)
tigl_h=tg.get_tigl_handler("simple_aircraft_v2")
test_class_name="WingFactory"
if test_class_name== "WingFactory":
    test_class= wf.WingFactory(tigl_h,1)
    test_class.create_wing_option1()
if test_class_name== "WingRibFactory":
    test_class= wrf.WingRibFactory(tigl_h,1)
    test_class.create_ribs_option1()
if test_class_name== "RuderFactory":
    test_class= rf.RuderFactory(tigl_h,1)
    test_class.get_trailing_edge_cutOut()
if test_class_name== "ReinforcementPipeFactory":
    test_class= rpf.ReinforcementePipeFactory(tigl_h,1)
    test_class.create_reinforcemente_pipe_option1(pipe_position=[1,2])
    
    
shape=test_class.get_shape()
m.display_this_shape(shape)
m.start()


