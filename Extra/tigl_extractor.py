import logging
import math

from OCC.Core.gp import gp_Pnt, gp_Vec, gp_Ax1, gp_Dir
from tigl3.core import TIGL_NOT_FOUND
from tigl3.tigl3wrapper import Tigl3
from tixi3.tixi3wrapper import Tixi3
import os


# wrapping functionality from
# https://dlr-sc.github.io/tigl/doc/3.2.3/


def get_tigl_handler(name, base_dir=r'test_cpacs'):
    tixi_handle = Tixi3()
    tigl_handle = Tigl3()
    if name is not None or name != "":
        name = name + ".xml"
        path = os.path.join(base_dir, name)
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            path = os.path.join(os.pardir, path)
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                logging.error("File not found! Extracting tigl was not possible")
        tixi_handle.open(abs_path)
    else:
        logging.error("Extracting tigl was not possible")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle


def get_tixi_handler(name, base_dir=r'test_cpacs'):
    tixi_handle = Tixi3()
    if name is not None or name != "":
        name = name + ".xml"
        path = os.path.join(base_dir, name)
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            path = os.path.join(os.pardir, path)
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                logging.error("File not found! Extracting tigl was not possible")
        tixi_handle.open(abs_path)
    else:
        logging.error("Extracting tixi was not possible")
    return tixi_handle


def get_fuselage_segment_and_eta_from_x(tigl3: Tigl3, fuselage_index: int, x: float):
    fuselage_segments = tigl3.fuselageGetSegmentCount(fuselage_index)

    for segment in range(1, fuselage_segments+1):
        start_segment = tigl3.fuselageGetPoint(fuselageIndex=fuselage_index, segmentIndex=segment, eta=0, zeta=0)
        end_segment = tigl3.fuselageGetPoint(fuselageIndex=fuselage_index, segmentIndex=segment, eta=1, zeta=0)

        # check if x is within fuselage
        if x < start_segment[0]:
            logging.error(
                f"'{x}' lies outside in front of fuselage {fuselage_index}:{tigl3.fuselageGetUID(fuselage_index)}")
            return TIGL_NOT_FOUND
        elif x < end_segment[0]:
            segment_uid = tigl3.fuselageGetSegmentUID(fuselageIndex=fuselage_index, segmentIndex=segment)
            eta = abs(x - start_segment[0]) / abs(start_segment[0] - end_segment[0])
            logging.debug(f"found '{x}' in segment {segment}:{segment_uid} and eta {eta}")
            return segment, eta

    logging.error(f"'{x}' lies outside behind of fuselage {fuselage_index}:{tigl3.fuselageGetUID(fuselage_index)}")
    return TIGL_NOT_FOUND

def get_fuselage_zeta_from_z(tigl3: Tigl3, fuselage_index: int, segment_idx: int, eta: float, z: float, toleranz: float = 0.001):
    _, _, z00 = tigl3.fuselageGetPoint(fuselageIndex=fuselage_index, segmentIndex=segment_idx, eta=eta, zeta=0)
    _, _, z05 = tigl3.fuselageGetPoint(fuselageIndex=fuselage_index, segmentIndex=segment_idx, eta=eta, zeta=0.5)

    if (z05 < z00 and z < z05 and  z00 < z) or (z00 < z05 and z < z00 and z05 < z):
        return TIGL_NOT_FOUND

    dire = 1 if z05 < z00 else -1
    zeta = 0.25
    zeta_interval = zeta/2
    while True:
        _, _, ztt = tigl3.fuselageGetPoint(fuselageIndex=fuselage_index, segmentIndex=segment_idx, eta=eta, zeta=zeta)
        if abs(ztt - z) < toleranz:
            return zeta
        elif ztt > z:
            zeta += dire*zeta_interval
            zeta_interval /= 2.0
        else:
            zeta -= dire*zeta_interval
            zeta_interval /= 2.0




def check_if_points_are_inside_fuselage(tigl3: Tigl3, fuselage_index: int, points: list[gp_Pnt]):
    fuselage_uid = tigl3.fuselageGetUID(fuselage_index)
    inside = True
    for i, point in enumerate(points):
        is_inside = tigl3.checkPointInside(point.X(), point.Y(), point.Z(), fuselage_uid)
        if not is_inside:
            # logging.debug(f"point {i} is not inside.")
            pass
        inside = is_inside and inside
    return inside


def translate_and_rotate_point(start_point: gp_Pnt, vecs: list[gp_Vec],
                               rot_ang: float = 0.0, rot_axis: gp_Ax1 = None):
    """
    Translates and rotates the start point
    :param rot_axis: axis of rotation (default is z-axis at start_point)
    :param rot_ang: angle of rotation
    :param tigl3:
    :param fuselage_index:
    :param start_point:
    :param vecs:
    :return:
    """
    rot_ang = rot_ang * math.pi / 180.0
    rot_axis = gp_Ax1(start_point, gp_Dir(gp_Vec(0, 0, 1))) if rot_axis is None else rot_axis
    points = []
    for vec in vecs:
        test_p = gp_Pnt(start_point.XYZ())
        test_p.Translate(vec)
        test_p.Rotate(rot_axis, rot_ang)
        points.append(test_p)
    return points
