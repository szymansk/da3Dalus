import OCP.BRepAlgoAPI as OAlgo

from Extra.ConstructionStepsViewer import *
from cadquery import Workplane

class BooleanCADOperation:

    @staticmethod
    def cut_list_of_namedshapes(shape: Workplane, shape_list, name="list_of_shapes",
                                trans=False) -> Workplane:
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
        result: Workplane = Workplane(cuted[-1], name)
        md.display_multipe_cuts(result, result, logging.NOTSET, shape_list, name, trans)
        return result

    @staticmethod
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
            logging.debug(f"fusing shape {index} from {len(shape_list)}")
            if not fused:
                fused.append(shape)
            else:
                fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1], shape).Shape())

        if len(fused) > 1:
            md.display_fuse(Workplane(fused[-1], ""),
                            Workplane(fused[-2], ""),
                            Workplane(shape_list[-1], ""), logging.NOTSET, msg, trans)
        else:
            md.display_this_shape(shape_list[-1], severity=logging.NOTSET)
        return fused[-1]

    @staticmethod
    def fuse_list_of_named_shapes(shape_list: list[Workplane], msg="", trans=False) -> Workplane:
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

        for index, named_shape in enumerate(shape_list):
            shape = named_shape.shape()
            logging.debug(f"fusing shape {index} from {len(shape_list)}")
            if not fused:
                fused.append(shape)
            else:
                fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1], shape).Shape())

        # if len(fused) > 1:
        #     md.display_fuse(Workplane(fused[-1], ""),
        #                     Workplane(fused[-2], ""),
        #                     Workplane(shape_list[-1], ""), logging.NOTSET, msg, trans)
        # else:
        #     md.display_this_shape(shape_list[-1], severity=logging.NOTSET)
        return Workplane(fused[-1], "fused")

    @staticmethod
    def cut_list_of_named_shapes(named_shape: Workplane, shape_list: list[Workplane], msg="",
                                 trans=False) -> Workplane:
        """
        returns the shape after cutting all the shapes on the list
        :param named_shape: to be cut from
        :param shape_list: shapes to be cut out
        :param msg: text to be displayed
        :param trans: set transparency
        :return:
        """
        logging.debug(f"Starting to cut from {named_shape.name()}")
        cut_topods = [named_shape.shape()]
        md = ConstructionStepsViewer.instance()
        for index, shape_to_cut in enumerate(shape_list):
            logging.debug(f"Cutting {shape_to_cut.name()}: Element {index + 1} from {len(shape_list)}")
            if not cut_topods:
                cut_topods.append(OAlgo.BRepAlgoAPI_Cut(named_shape.shape(), shape_to_cut.shape()).Shape())
            else:
                cut_topods.append(OAlgo.BRepAlgoAPI_Cut(cut_topods[-1], shape_to_cut.shape()).Shape())
        if cut_topods[-1] is None:
            logging.error(f"cut_list_of_shapes result is None")
        result = Workplane(cut_topods[-1], f"cuted_{named_shape.name()}")
        md.display_multipe_cuts(result, named_shape, logging.NOTSET, shape_list, msg, trans)
        return result

    @staticmethod
    def fuse_shapes(a: Workplane, b: Workplane, new_name: str) -> Workplane:
        return Workplane(OAlgo.BRepAlgoAPI_Fuse(a.shape(), b.shape()).Shape(), new_name)

    @staticmethod
    def cut_shape_from_shape(a: Workplane, b: Workplane, new_name: str) -> Workplane:
        """
        A-B
        :param A:
        :param B:
        :return:
        """
        return a.cut(b)
        #return Workplane(OAlgo.BRepAlgoAPI_Cut(a.shape(), b.shape()).Shape(), new_name)

    @staticmethod
    def intersect_shape_with_shape(a: Workplane, b: Workplane, new_name: str) -> Workplane:
        named_shape = Workplane(
            OAlgo.BRepAlgoAPI_Common(a.shape(), b.shape()).Shape(), new_name)
        named_shape.shape()
        return named_shape

