import OCC.Core.BRepAlgoAPI as OAlgo

from Extra.mydisplay import *


def fuse_list_of_shapes(shape_list, msg="", trans=False) -> OTopo.TopoDS_Shape:
    """
    fuses all the shapes in the list to one shape
    :param shape_list: list of shapes
    :param msg: text to be displayed
    :trans: set transparency
    :return:
    """
    logging.info(f"Starting to fuse_list_of_shapes")
    fused = []
    shape = None
    md = myDisplay.instance()
    for index, shape in enumerate(shape_list):
        logging.info(f"Fussing Shape {index + 1} from {len(shape_list)}")
        if not fused:
            fused.append(shape)
        else:
            fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1], shape).Shape())
    md.display_fuse(fused[-1], fused[-2], shape, msg, trans)
    return fused[-1]


def cut_list_of_shapes(shape, shape_list, msg="", trans=False) -> OTopo.TopoDS_Shape:
    """
    returns the shape after cuting all the shapes on the list
    :param shape: to be cut from
    :param shape_list: shapes to be cutout
    :param msg: text to be displayed
    :param trans: set transparency
    :return:
    """
    logging.info(f"Starting to cut_list_of_shapes")
    cuted = []
    md = myDisplay.instance()
    for index, shape_to_cut in enumerate(shape_list):
        logging.info(f"Cutting Shape {index + 1} from {len(shape_list)}")
        if not cuted:
            cuted.append(OAlgo.BRepAlgoAPI_Cut(shape, shape_to_cut).Shape())
        else:
            cuted.append(OAlgo.BRepAlgoAPI_Cut(cuted[-1], shape_to_cut).Shape())
    if cuted[-1] == None:
        logging.error(f"cut_list_of_shapes result is None")
    md.display_multipe_cuts(shape, shape_list, msg, trans)
    return cuted[-1]
