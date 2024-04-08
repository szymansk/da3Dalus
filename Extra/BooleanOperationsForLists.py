import logging

import OCP.BRepAlgoAPI as OAlgo

from cadquery import Workplane, Solid


class BooleanCADOperation:


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
        a_solid = a.findSolid().Solids()[0].wrapped
        b_solid = b.findSolid().Solids()[0].wrapped
        a.findSolid().BoundingBox()
        named_shape = Workplane(Solid(
            OAlgo.BRepAlgoAPI_Common(a_solid, b_solid).Shape())).tag(new_name)
        return named_shape

