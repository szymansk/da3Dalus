import OCC.Core.BRepAlgoAPI as OAlgo
import tigl3.geometry as TGeo

from Extra.ConstructionStepsViewer import *


#class BooleanCADListOperation:
def fuse_list_of_namedshapes(shape_list, name="list_of_shapes", trans=False) -> TGeo.CNamedShape:
    """
    fuses all the shapes in the list to one shape
    :param shape_list: list of shapes
    :param msg: text to be displayed
    :trans: set transparency
    :return:
    """
    logging.debug(f"Starting to fuse {name} ")
    fused = []
    md = ConstructionStepsViewer.instance()
    element: TGeo.CNamedShape
    for index, element in enumerate(shape_list):
        logging.debug(f"Fussing {element.name()}: Element {index + 1} from {len(shape_list)}")
        if not fused:
            fused.append(TGeo.CNamedShape(element.shape(), f"{name}_{index + 1}"))
        else:
            fused.append(TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Fuse(fused[-1].shape(), element.shape()).Shape(),
                                          f"{name}_{index + 1}"))
    fused[-1].set_name(f"fused_{name}")
    if len(fused) > 1:
        md.display_fuse(fused[-1], fused[-2], shape_list[-1], logging.NOTSET, name, trans)
    else:
        md.display_this_shape(shape_list[-1], severity=logging.NOTSET, msg=name)
    return fused[-1]

def cut_list_of_namedshapes(shape: TGeo.CNamedShape, shape_list, name="list_of_shapes",
                            trans=False) -> TGeo.CNamedShape:
    """
    returns the shape after cuting all the shapes on the list
    :param shape: to be cut from
    :param shape_list: shapes to be cutout
    :param msg: text to be displayed
    :param trans: set transparency
    :return:
    """
    logging.debug(f"Starting to cut {name}")
    cuted = [shape.shape()]
    md = ConstructionStepsViewer.instance()
    for index, element in enumerate(shape_list):
        logging.debug(f"Cutting {element.name()}: Element {index + 1} from {len(shape_list)}")
        if not cuted:
            cuted.append(OAlgo.BRepAlgoAPI_Cut(shape.shape(), element.shape()).Shape())
        else:
            cuted.append(OAlgo.BRepAlgoAPI_Cut(cuted[-1], element.shape()).Shape())
    if cuted[-1] == None:
        logging.error(f"Cutting list of shapes Failed")
    result: TGeo.CNamedShape = TGeo.CNamedShape(cuted[-1], name)
    md.display_multipe_cuts(result, result, logging.NOTSET, shape_list, name, trans)
    return result


def fuse_list_of_shapes(shape_list: list[OTopo.TopoDS_Shape], msg="", trans=False) -> OTopo.TopoDS_Shape:
    """
    fuses all the shapes in the list to one shape
    :param shape_list: list of shapes
    :param msg: text to be displayed
    :trans: set transparency
    :return:
    """
    logging.debug(f"Starting to fuse_list_of_shapes")
    fused = []
    md = ConstructionStepsViewer.instance()

    for index, shape in enumerate(shape_list):
        logging.debug(f"Fusing shape {index + 1} from {len(shape_list)}")
        if not fused:
            fused.append(shape)
        else:
            fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1], shape).Shape())

    if len(fused) > 1:
        md.display_fuse(TGeo.CNamedShape(fused[-1], ""),
                        TGeo.CNamedShape(fused[-2], ""),
                        TGeo.CNamedShape(shape_list[-1], ""), logging.NOTSET, msg, trans)
    else:
        md.display_this_shape(shape_list[-1], severity=logging.NOTSET)
    return fused[-1]


class BooleanCADOperation:
    @staticmethod
    def cut_list_of_shapes(named_shape: TGeo.CNamedShape, shape_list: list[TGeo.CNamedShape], msg="",
                           trans=False) -> TGeo.CNamedShape:
        """
        returns the shape after cutting all the shapes on the list
        :param named_shape: to be cut from
        :param shape_list: shapes to be cut out
        :param msg: text to be displayed
        :param trans: set transparency
        :return:
        """
        logging.debug(f"Starting to cut from {named_shape.name()}")
        cuted = [named_shape.shape()]
        md = ConstructionStepsViewer.instance()
        for index, shape_to_cut in enumerate(shape_list):
            logging.debug(f"Cutting {shape_to_cut.name()}: Element {index + 1} from {len(shape_list)}")
            if not cuted:
                cuted.append(OAlgo.BRepAlgoAPI_Cut(named_shape.shape(), shape_to_cut.shape()).Shape())
            else:
                cuted.append(OAlgo.BRepAlgoAPI_Cut(cuted[-1], shape_to_cut.shape()).Shape())
        if cuted[-1] is None:
            logging.error(f"cut_list_of_shapes result is None")
        result = TGeo.CNamedShape(cuted[-1], f"cuted_{named_shape.name()}")
        md.display_multipe_cuts(result, named_shape, logging.NOTSET, shape_list, msg, trans)
        return result

    @staticmethod
    def fuse_shapes(a: TGeo.CNamedShape, b: TGeo.CNamedShape, new_name: str) -> TGeo.CNamedShape:
        return TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Fuse(a.shape(), b.shape()).Shape(), new_name)

        #
        # shape: TGeo.CNamedShape = CMergeShapes(a, b).named_shape()
        # shape.set_name(new_name)
        # return shape

    @staticmethod
    def cut_shape_from_shape(a: TGeo.CNamedShape, b: TGeo.CNamedShape, new_name: str) -> TGeo.CNamedShape:
        """
        A-B
        :param A:
        :param B:
        :return:
        """
        return TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(a.shape(), b.shape()).Shape(), new_name)
        # from tigl3.boolean_ops import CCutShape
        # shape: TGeo.CNamedShape = CCutShape(a, b).named_shape()
        # shape.set_name(new_name)
        # return shape

    @staticmethod
    def intersect_shape_with_shape(a: TGeo.CNamedShape, b: TGeo.CNamedShape, new_name: str) -> TGeo.CNamedShape:
        named_shape = TGeo.CNamedShape(
            OAlgo.BRepAlgoAPI_Common(a.shape(), b.shape()).Shape(), new_name)
        named_shape.shape()
        return named_shape

