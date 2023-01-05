import math

from OCC.Core.gp import gp_Vec

from Extra.tigl_extractor import *
from Airplane.FuselageConstructionSteps import *


def findServoPosition(tigl_h: Tigl3, fuselage_index: int):
    import math
    segments = tigl_h.fuselageGetSegmentCount(fuselage_index)

    servo_length = 0.024
    servo_height = 0.024
    servo_width = 0.012
    z_max = 0.018-(0.023)
    x_max = 0.72

    while True:
        # sweep through segments
        for segment in reversed(range(1, segments + 1)):
            # sweep through x-positions in mm steps
            eta = 1.0  # along the x-axis (0..1)
            zeta_top = 0
            zeta_middle = 0.25
            zeta_bottom = 0.5

            segment_length = (tigl_h.fuselageGetPoint(fuselage_index, segment, eta, zeta_middle)[0] \
                              - tigl_h.fuselageGetPoint(fuselage_index, segment, 0, zeta_middle)[0])
            mm_step = 1.0/(segment_length*1000)
            servo_length_steps = math.ceil(servo_length * 1000)
            max_steps = math.floor(segment_length * 1000) - servo_length_steps

            for step in reversed(range(0, max_steps)):
                eta = step * mm_step
                segment_width_servo_start = abs(tigl_h.fuselageGetPoint(fuselage_index, segment, eta, zeta_middle)[1]
                                                - tigl_h.fuselageGetPoint(fuselage_index, segment, eta, zeta_middle+0.5)[1])
                segment_width_servo_end = abs(
                    tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, zeta_middle)[1]
                    - tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, zeta_middle+0.5)[1])
                x_end, y_end, z_end = \
                tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, zeta_middle)

                if segment_width_servo_start > servo_height and segment_width_servo_end > servo_height and x_end < x_max:
                    #  we found a height and length fit
                    # let's check the width and
                    alpha_steps = 20
                    for alpha_index in range(alpha_steps):
                        alpha = alpha_index * 0.5/alpha_steps + 0.5
                        segment_height_servo_start = abs(tigl_h.fuselageGetPoint(fuselage_index, segment, eta, 0.+alpha)[2] \
                                                      - tigl_h.fuselageGetPoint(fuselage_index, segment, eta, 0.5-alpha)[2])
                        segment_height_servo_end = abs(
                            tigl_h.fuselageGetPoint(fuselage_index, segment,  eta + mm_step * servo_length_steps, 0.+alpha)[2]
                            - tigl_h.fuselageGetPoint(fuselage_index, segment, eta  + mm_step * servo_length_steps, 0.5-alpha)[2])

                        if segment_height_servo_start > servo_width and segment_height_servo_end > servo_height:
                            segment_width_servo_start = abs(
                                tigl_h.fuselageGetPoint(fuselage_index, segment, eta, 0.+alpha)[1]
                                - tigl_h.fuselageGetPoint(fuselage_index, segment, eta, 1-alpha)[1])
                            segment_width_servo_end = abs(
                                tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, 0.+alpha)[1]
                                - tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, 1-alpha)[1])
                            x_end, y_end, z_end = tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, 0.5-alpha)
                            if segment_width_servo_start > servo_height and segment_width_servo_end > servo_height and z_end+servo_width < z_max:
                                point_found_start = tigl_h.fuselageGetPoint(fuselage_index, segment, eta, 0.5-alpha)
                                point_found_end = tigl_h.fuselageGetPoint(fuselage_index, segment, eta + mm_step * servo_length_steps, 0.5-alpha)
                                return point_found_start, point_found_end

            pass


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

    segment_eta = get_fuselage_segment_and_eta_from_x(tigl3, fuselage_idx, 0.6)

    if segment_eta != TIGL_NOT_FOUND:
        P = tigl3.fuselageGetPoint(fuselage_idx, *segment_eta, 0.75)
        start = gp_Pnt(*P)
        shapeDisplay.display_point_on_shape(fuselage_loft, start, logging.INFO, color='RED', msg="start")

        vecs = [gp_Vec(0.024, 0.000, 0),
                gp_Vec(0.024, 0.000, 0.012),
                gp_Vec(0.000, 0.000, 0.012),
                gp_Vec(0.000, 0.024, 0),
                gp_Vec(0.024, 0.024, 0),
                gp_Vec(0.024, 0.024, 0.012),
                gp_Vec(0.000, 0.024, 0.012)]

        points = translate_and_rotate_point(start, vecs, 3.4)
        inside = check_if_points_are_inside_fuselage(tigl3, fuselage_idx, points)
        logging.info(f"points are inside: {inside}")
        shapeDisplay.display_points(points, logging.INFO)


    shapeDisplay.start()

