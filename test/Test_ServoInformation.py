import math

from OCP.gp import gp_Vec

from Airplane.aircraft_topology.ServoInformation import ServoInformation
from Extra.tigl_extractor import *
from Airplane.FuselageConstructionSteps import *


if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.NOTSET, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl3: Tigl3 = get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl3._handle.value)

    fuselage_idx = 1
    fuselage_loft = ccpacs_configuration.get_fuselage(fuselage_idx).get_loft()

    servo_information_a = ServoInformation(height=0.023, width=0.012, length=0.024, lever_length=0.024, rot_x=90)

    segment_eta = get_fuselage_segment_and_eta_from_x(tigl3, fuselage_idx, 0.6)

    try:
        if segment_eta != TIGL_NOT_FOUND:
            P = tigl3.fuselageGetPoint(fuselage_idx, *segment_eta, 0.75)
            start = gp_Pnt(*P)
            shapeDisplay.instance().display_point_on_shape(fuselage_loft, start, logging.INFO, color='RED', msg="start")

            servo_information_a.check_if_servo_fits_in_fuselage(tigl3, fuselage_idx, corner=start, rot_angl=3.4)

        pt, ang = servo_information_a.place_elevator_servo(tigl3, fuselage_idx, 2, 0)
        # ConstructionStepsViewer.instance().display.EraseAll()

        shapeDisplay.instance().display_point_on_shape(fuselage_loft, pt, logging.INFO, color='MAGENTA', msg="start")
        servo_information_a.check_if_servo_fits_in_fuselage(tigl3, fuselage_idx, corner=pt, rot_angl=ang, color="BLUE")
    except:
        pass
    shapeDisplay.start()

