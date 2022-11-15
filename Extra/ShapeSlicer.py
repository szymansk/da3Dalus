import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo

from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.BooleanOperationsForLists import cut_list_of_namedshapes
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
from _alt.abmasse import *


class ShapeSlicer:
    def __init__(self, named_shape, quantity, dev=False):
        self.m = myDisplay.instance()
        self.parts_list = []
        self.quantity: int = quantity
        # self.cutout_front_box: OTopo.TopoDS_Shape = None
        # self.cutout_back_box: OTopo.TopoDS_Shape = None
        self.shape_dimensions = ShapeDimensions(named_shape)
        self.namedshape = self.orient_shape(named_shape)
        # self.shape = shape
        self.part_lenght: float = self.shape_dimensions.get_length() / quantity
        self.position_front: float = 0.0
        self.position_back: float = 0.0
        # logstr= "Dividing shape in " + str(quantity) + "equal parts of lenght " + str(self.part_lenght)
        logstr = "initiating slicer"
        logging.info(logstr)

    def orient_shape(self, namedshape) -> TGeo.CNamedShape:
        '''Rotates the shape 90 degrees over the Zaxis if the shape is wider than longer'''
        if self.shape_dimensions.get_length() < self.shape_dimensions.get_width():
            logging.info(f"Rotating {namedshape.name()} by 90 degrees")
            rot_shape = OExs.rotate_shape(namedshape.shape(), Ogp.gp_OZ(), -90)
            result: TGeo.CNamedShape = TGeo.CNamedShape(rot_shape, namedshape.name())
            self.m.display_this_shape(result, f"Rotated {namedshape.name()}")
            self.shape_dimensions = ShapeDimensions(result)
            self.part_lenght: float = self.shape_dimensions.get_length() / self.quantity
        else:
            result = namedshape
        return result

    def slice_by_common(self):
        for i in range(0, self.quantity):
            self.position_front = self.part_lenght * i
            self.cutout_front_box = OPrim.BRepPrimAPI_MakeBox(self.shape_dimensions.get_point(1), self.part_lenght,
                                                              self.shape_dimensions.get_width(),
                                                              self.shape_dimensions.get_height()).Shape()
            self.cutout_front_box = OExs.translate_shp(self.cutout_front_box, Ogp.gp_Vec(self.position_front, 0, 0))
            part: OTopo.TopoDS_Shape = self.namedshape.shape()

            part = OAlgo.BRepAlgoAPI_Common(part, self.cutout_front_box).Shape()
            logstr = "Part " + str(i)
            self.m.display_this_shape(part, logstr)
            self.parts_list.append(part)

    def slice_by_cut(self):
        for i in range(0, self.quantity):
            part_name = f"{self.namedshape.name()}  {i}"
            logstr = f"Slicing {part_name}"
            logging.info(logstr)
            self.position_front = -self.shape_dimensions.get_length() + self.part_lenght * i
            self.position_back = self.part_lenght * (i + 1)
            cutout_box = OPrim.BRepPrimAPI_MakeBox(self.shape_dimensions.get_point(1),
                                                   self.shape_dimensions.get_length(),
                                                   self.shape_dimensions.get_width() * 2,
                                                   self.shape_dimensions.get_height() * 2).Shape()
            cutout_front_box = OExs.translate_shp(cutout_box, Ogp.gp_Vec(self.position_front,
                                                                         -self.shape_dimensions.get_width() / 2,
                                                                         -self.shape_dimensions.get_height() / 2))
            named_cutout_front_box: TGeo.CNamedShape = TGeo.CNamedShape(cutout_front_box, "cutout_front_box")

            cutout_back_box = OExs.translate_shp(cutout_box,
                                                 Ogp.gp_Vec(self.position_back, -self.shape_dimensions.get_width() / 2,
                                                            -self.shape_dimensions.get_height() / 2))
            named_cutout_back_box: TGeo.CNamedShape = TGeo.CNamedShape(cutout_back_box, "cutout_back_box")

            cutout_list = [named_cutout_front_box, named_cutout_back_box]

            wing_part = cut_list_of_namedshapes(self.namedshape, cutout_list, part_name)
            self.parts_list.append(wing_part)

        self.m.display_slice_x(self.parts_list, f"Sliced {self.namedshape.name()}")

    def slice_with_list_cut(self, list_of_pos):
        '''
        slices the shape in given x Koordinates
        :param list_of_pos:
        :return:
        '''
        frontbox = None
        rearbox = None

        for i, front_pos in enumerate(list_of_pos):
            part = self.namedshape
            rearbox = OPrim.BRepPrimAPI_MakeBox(self.total_lenght, self.total_widht, self.total_height).Shape()
            rearbox = OExs.translate_shp(rearbox,
                                         Ogp.gp_Vec(list_of_pos[i], -self.total_widht / 2, -self.total_height / 2))
            part1 = OAlgo.BRepAlgoAPI_Cut(part, rearbox).Shape()
            # self.m.display_cut(part1,part,rearbox)
            if i != len(list_of_pos):
                lenght = list_of_pos[i]
                if i != 0:
                    logging.info("Cutting frontbox " + str(i))
                    frontbox = OPrim.BRepPrimAPI_MakeBox(list_of_pos[i - 1], self.total_widht,
                                                         self.total_height).Shape()
                    frontbox = OExs.translate_shp(frontbox,
                                                  Ogp.gp_Vec(0.0, -self.total_widht / 2, -self.total_height / 2))
                    beforecut = part1
                    part1 = OAlgo.BRepAlgoAPI_Cut(beforecut, frontbox).Shape()
                    self.m.display_cut(part1, beforecut, frontbox)
                    # lenght=list_of_pos[i+1]-list_of_pos[i]
                logstr = f"Part {i}  {lenght=}"
                logging.info(logstr)
            else:
                self.m.display_cut(part1, part, rearbox)
            # self.m.display_this_shape(part1)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)

    def slice_with_list_common(self, list_of_pos, direction="x"):
        frontbox = None

        for i, front_pos in enumerate(list_of_pos):
            part = self.shape
            if i == 0:
                lenght = list_of_pos[i]
            else:
                lenght = list_of_pos[i] - list_of_pos[i - 1]
            if i == 0:
                frontbox = OPrim.BRepPrimAPI_MakeBox(lenght + 0.01, self.total_widht, self.total_height).Shape()
                frontbox = OExs.translate_shp(frontbox,
                                              Ogp.gp_Vec(-0.01, -self.total_widht / 2, -self.total_height / 2))
            else:
                frontbox = OPrim.BRepPrimAPI_MakeBox(lenght, self.total_widht, self.total_height).Shape()
                frontbox = OExs.translate_shp(frontbox, Ogp.gp_Vec(list_of_pos[i - 1], -self.total_widht / 2,
                                                                   -self.total_height / 2))
            part1 = OAlgo.BRepAlgoAPI_Common(part, frontbox).Shape()
            self.m.display_common(part1, frontbox, part)
            logging.info("Coomon frontbox " + str(i))
            logstr = f"Part {i}  {lenght=}"
            logging.info(logstr)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)

    def slice_with_list_common_y(self, list_of_pos):
        frontbox = None
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.shape)
        for i, front_pos in enumerate(list_of_pos):
            part = self.shape
            if i == 0:
                width = list_of_pos[i]
            else:
                width = list_of_pos[i] - list_of_pos[i - 1]
            if i == 0:
                frontbox = OPrim.BRepPrimAPI_MakeBox(self.total_lenght, width, self.total_height).Shape()
                frontbox = OExs.translate_shp(frontbox, Ogp.gp_Vec(xmin, 0.0, zmin))
            else:
                frontbox = OPrim.BRepPrimAPI_MakeBox(self.total_lenght, width, self.total_height).Shape()
                frontbox = OExs.translate_shp(frontbox, Ogp.gp_Vec(xmin, list_of_pos[i - 1], zmin))
            part1 = OAlgo.BRepAlgoAPI_Common(part, frontbox).Shape()
            self.m.display_common(part1, frontbox, part)
            logging.info("Common frontbox " + str(i))
            logstr = f"Part {i}  {width=}"
            logging.info(logstr)
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, self.name)

    def slicing_positions(self):
        result = []
        before_wing = dimensions_mainwing.get("xmin") - 0.02
        after_wing = dimensions_mainwing["xmax"] + 0.002
        mid_wing = (after_wing + before_wing) / 2
        result.append(before_wing / 2)
        result.append(before_wing)
        result.append(after_wing)
        result.append(mid_wing)
        end_fuselage = dimensions_fuselage["xmax"]
        split_rear_fuselage = (end_fuselage + after_wing) / 2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        return result

    def slicing_positions2(self, wing_shape, fuselage_shape):
        result = []
        before_wing = get_koordinate(wing_shape, "xmin") - 0.0004
        after_wing = get_koordinate(wing_shape, "xmax") + 0.0004
        mid_wing = (after_wing + before_wing) / 2
        result.append(before_wing / 2)
        result.append(before_wing)
        result.append(mid_wing)
        result.append(after_wing)
        end_fuselage = get_koordinate(fuselage_shape, "xmax")
        split_rear_fuselage = (end_fuselage + after_wing) / 2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        logging.info(result)
        logging.info(len(result))
        return result

    def slicing_postion_wing(self, wing_shape, factor=0.4):
        result = []
        ymax = get_koordinate(wing_shape, "ymax")
        start_of_flap = ymax * factor + 0.001
        half_of_start = start_of_flap / 2
        rest = ymax - start_of_flap
        dif = rest / 3
        p1 = start_of_flap + dif
        p2 = p1 + dif
        result.append(half_of_start)
        result.append(start_of_flap)
        result.append(p1)
        result.append(p2)
        result.append(ymax)
        logging.info(result)
        logging.info(len(result))
        return result
