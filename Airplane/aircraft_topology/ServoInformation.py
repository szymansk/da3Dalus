from OCC.Core.gp import *

from Airplane.aircraft_topology.ComponentInformation import ComponentInformation
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from Extra.tigl_extractor import *


class ServoInformation(ComponentInformation):
    def __init__(self, height: float, width: float, length: float, lever_length: float, rot_x: float = 0.0, rot_y: float = 0.0,
                 rot_z: float = 0.0, trans_x: float = 0.0, trans_y: float = 0.0, trans_z: float = 0.0):
        self.lever_length = lever_length

        self.trans_z = trans_z
        self.trans_y = trans_y
        self.trans_x = trans_x
        self.rot_z = rot_z
        self.rot_y = rot_y
        self.rot_x = rot_x
        self.length = length
        self.width = width
        self.height = height

        self._corner_vecs = [gp_Vec(0.000000000, 0.000, 0),
                       gp_Vec(self.length, 0.000, 0),
                       gp_Vec(self.length, 0.000, -self.height),
                       gp_Vec(0.000000000, 0.000, -self.height),

                       gp_Vec(0.000000000, -self.width, 0),
                       gp_Vec(self.length, -self.width, 0),
                       gp_Vec(self.length, -self.width, -self.height),
                       gp_Vec(0.000000000, -self.width, -self.height)]
        super().__init__(trans_z=self.trans_z,
                         trans_y=self.trans_y,
                         trans_x=self.trans_x,
                         rot_z=self.rot_z,
                         rot_y=self.rot_y,
                         rot_x=self.rot_x,
                         length=self.length,
                         width=self.width,
                         height=self.height)

    def check_if_servo_fits_in_fuselage(self, tigl3: Tigl3, fuselage_idx: int, corner: gp_Pnt,
                                        rot_angl: float = 0.0, rot_axis: gp_Ax1 = None, color='RED'):
        """
        Check if the servo fits in the fuselage.
        :param tigl3:
        :param fuselage_idx:
        :param corner: top right corner of servo in world coordinates
        :return: true if all points are inside the fuselage
        """

        vecs = [vec.Rotated(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), self.rot_x*math.pi/180.0)
                .Rotated(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), self.rot_y*math.pi/180.0)
                .Rotated(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), self.rot_z*math.pi/180.0) for vec in self._corner_vecs]

        points = translate_and_rotate_point(corner, vecs, rot_angl, rot_axis)
        inside = check_if_points_are_inside_fuselage(tigl3, fuselage_idx, points)
        # logging.debug(f"points are inside: {inside}")
        ConstructionStepsViewer.instance().display_points(points=points, severity=logging.NOTSET, color=color)

        return inside

    def place_rudder_servo(self, tigl3: Tigl3, fuselage_idx: int, rudder_idx: int, elevator_idx: int, side: int):
        # depending on the placement of the rudder and the elevator


        pass

    def place_elevator_servo(self, tigl3: Tigl3, fuselage_idx: int, elevator_wing_idx: int, side: int):
        # depending on the placement of the elevator the servo has to be placed
        # below or above the elevator
        eta_start = 0 # along the wing length
        xsi_start = 0 # along the wing chord
        xsi_end = 1
        point_bottom = tigl3.wingGetLowerPoint(elevator_wing_idx, segmentIndex=1, eta=eta_start, xsi=xsi_end)
        point_top = tigl3.wingGetUpperPoint(elevator_wing_idx, segmentIndex=1, eta=eta_start, xsi=xsi_start)

        ConstructionStepsViewer.instance().display_points([gp_Pnt(*point_bottom), gp_Pnt(*point_top)], logging.NOTSET, color='BLACK', msg="test")

        min_x = min(point_top[0], point_bottom[0])
        segment_eta = get_fuselage_segment_and_eta_from_x(tigl3, fuselage_idx, min_x)
        segment = segment_eta[0]
        top = tigl3.fuselageGetPoint(fuselage_idx, *segment_eta, 0)
        bottom = tigl3.fuselageGetPoint(fuselage_idx, *segment_eta, 0.5)

        zeta_middle = 0.25
        segment_length = (tigl3.fuselageGetPoint(fuselage_idx, segment, 1, zeta_middle)[0] \
                          - tigl3.fuselageGetPoint(fuselage_idx, segment, 0, zeta_middle)[0])
        servo_max_eta = max(self.length, max(self.width, self.height))/segment_length

        start_eta = segment_eta[1]
        start_zeta = 1 - get_fuselage_zeta_from_z(tigl3, fuselage_idx, segment_eta[0], start_eta,
                                                  point_bottom[2] - (self.lever_length - self.width/2)*1.2)
        pnt = tigl3.fuselageGetPoint(fuselage_idx, segment, start_eta, start_zeta)
        ConstructionStepsViewer.instance().display_points([gp_Pnt(*pnt)], logging.NOTSET, color='GREEN', msg="test")


        grid = 10
        # let's place it step for step
        for eta_idx in range(grid):
            eta = start_eta - (start_eta/grid)*eta_idx
            for zeta_idx in range(grid):
                zeta = start_zeta + (0.5-start_zeta)/grid*zeta_idx
                logging.debug(f"zeta: {zeta}, eta: {eta}")
                pt = tigl3.fuselageGetPoint(fuselage_idx, segment_eta[0], eta, zeta)
                corner_pt = gp_Pnt(*pt)
                servo_eta = eta + servo_max_eta if eta + servo_max_eta < 1.0 else 1.0

                pt_test = tigl3.fuselageGetPoint(fuselage_idx, segment_eta[0], servo_eta, zeta)
                # angle between pt_test and pt
                ang = gp_Vec(*pt_test).AngleWithRef(gp_Vec(1, 0, 0), gp_Vec(0, 0, 1))*180./math.pi
                inside = self.check_if_servo_fits_in_fuselage(tigl3, fuselage_idx, corner_pt, ang)
                if inside:
                    ConstructionStepsViewer.instance().display_points([gp_Pnt(*pt_test)], logging.NOTSET, color='YELLOW', msg="test")
                    return corner_pt, ang

        return None