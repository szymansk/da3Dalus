import logging

import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
import OCC.Core.BRepPrimAPI as OPrim

import Airplane.AirplaneFactory as ap
import Airplane.ReinforcementPipeFactory as rpf
import Airplane.Wing.CablePipeFactory as cp
import Airplane.Wing.RuderFactory as rf
import Airplane.Wing.ServoRecessFactory as srf
import Airplane.Wing.WingFactory as wf
import Airplane.Wing.WingRibFactory as wrf
import Airplane.Fuselage.FuselageFactory as ff
import Airplane.Fuselage.EngineMountFactory as em
import Extra.mydisplay as myDisplay
import Extra.tigl_extractor as tg
import tigl3.boolean_ops as boo
import Extra.ShapeSlicer as ss
import Extra.ShellCreator as cs
import Extra.CollisionDetector as cd
import stl_exporter.Ausgabeservice as exp
from Dimensions.ShapeDimensions import ShapeDimensions

if __name__ == "__main__":
    m = myDisplay.myDisplay.instance(True, 1.5)
    # try:
    tigl_h = tg.get_tigl_handler("simple_aircraft")
    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_h._handle.value)
    fuselage: TConfig.CCPACSWing = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = ShapeDimensions(fuselage_loft)
    m.display_in_origin(fuselage_loft, "", True)

    for i in range(1, cpacs_configuration.get_wing_count() + 1):

        wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(i)
        wing_loft: TGeo.CNamedShape = wing.get_loft()
        wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
        wing_dimensions = ShapeDimensions(wing_loft)
        m.display_in_origin(wing_loft, "", True)
        try:
            mirroered_loft = wing.get_mirrored_loft()
            m.display_in_origin(mirroered_loft, "", True)
        except:
            logging.warning(f"No mirrored {wing_loft.name()}")

    wing: TConfig.CCPACSWing = cpacs_configuration.get_wing(1)

    compseg: TConfig.CCPACSWingComponentSegment = wing.get_component_segment(1)
    control_surface: TConfig.CCPACSControlSurfaces = compseg.get_control_surfaces()
    trailing_edge_devices: TConfig.CCPACSTrailingEdgeDevices = control_surface.get_trailing_edge_devices()
    trailing_edge_device: TConfig.CCPACSTrailingEdgeDevice = trailing_edge_devices.get_trailing_edge_device(1)
    ruder_loft: TGeo.CNamedShape = trailing_edge_device.get_loft()
    m.display_in_origin(ruder_loft, "", True)
    try:
        mirroered_loft = trailing_edge_device.get_mirrored_loft()
        m.display_in_origin(mirroered_loft, "", True)
    except:
        logging.warning(f"No mirrored {ruder_loft.name()}")

    m.start()

    '''
    engines: TConfig.CPACSEngines = cpacs_configuration.get_engines()
    print(engines.get_next_uidparent())
    print(f"{engines.get_engine_count()=}")
    engine: TConfig.CPACSEngine= engines.get_engine(1)
    print(engine.get_thrust_00scaling())
    #engine_loft: TGeo.CNamedShape = engines.get
    #engine_shape: OTopo.TopoDS_Shape = engine_loft.shape()
    #engine_dimensions = ShapeDimensions(engine_loft)
    #m.display_in_origin(engine_loft, "", True)
    m.start()
    #except:
    #    m.start()
    '''
