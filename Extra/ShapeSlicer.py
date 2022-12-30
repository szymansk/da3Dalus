import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo

from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.BooleanOperationsForLists import BooleanCADOperation
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
import logging


class ShapeSlicer:
    '''
    This class provides methods to slice/divide a Shape into different parts(shapes)
    '''

    def __init__(self, named_shape: TGeo.CNamedShape, quantity=3):
        '''
        to initialize this class the shape is need and the quantity of pices you want to devide it in
        :param named_shape: CNamedShape
        :param quantity: int default=3
        '''
        logging.debug("Initiating slicer")
        self.m = ConstructionStepsViewer.instance()
        self.parts_list = []
        self.quantity: int = quantity
        self.shape_dimensions = ShapeDimensions(named_shape)
        self.namedshape = self.orient_shape(named_shape)
        self.part_lenght: float = self.shape_dimensions.get_length() / quantity
        self.position_front: float = 0.0
        self.position_back: float = 0.0

    def orient_shape(self, namedshape) -> TGeo.CNamedShape:
        '''
        Rotates the shape 90 degrees over the Zaxis if the shape is wider than longer
        '''
        if self.shape_dimensions.get_length() < self.shape_dimensions.get_width():
            logging.debug(f"Rotating {namedshape.name()} by 90 degrees")
            rotated_shape = OExs.rotate_shape(namedshape.shape(), Ogp.gp_OZ(), -90)
            result: TGeo.CNamedShape = TGeo.CNamedShape(rotated_shape, namedshape.name())
            self.m.display_this_shape(result, severity=logging.NOTSET, msg=f"Rotated {namedshape.name()}")
            self.shape_dimensions = ShapeDimensions(result)
            self.part_lenght: float = self.shape_dimensions.get_length() / self.quantity
        else:
            result = namedshape
        return result

    def slice_by_common(self):
        '''
        slices the shape using the common method from Opencascade and stores the parts in the partslist of the class.
        A box cutout moves stepwise from front to back, evrything that is encapsulated by the box equals to the new part
        '''
        for i in range(0, self.quantity):
            position_front = self.part_lenght * i
            cutout_box = OPrim.BRepPrimAPI_MakeBox(self.shape_dimensions.get_point(1), self.part_lenght,
                                                   self.shape_dimensions.get_width(),
                                                   self.shape_dimensions.get_height()).Shape()
            cutout_box = OExs.translate_shp(cutout_box, Ogp.gp_Vec(position_front, 0, 0))
            part: TGeo.CNamedShape = self.namedshape
            name = f"{self.namedshape.name()}_{i}"
            part = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(part.shape(), cutout_box).Shape(), name)
            self.m.display_this_shape(part, severity=logging.NOTSET)
            self.parts_list.append(part)

    def slice_by_cut(self):
        '''
        slices the shape using the cut method from Opencascade and stores the parts in the partslist of the class.
        2 Cutout boxes move from front to back of the shape. Everything inside the box is removed. The leftover is the new part
        '''
        for i in range(0, self.quantity):
            part_name = f"{self.namedshape.name()}  {i}"
            logstr = f"Slicing {part_name}"
            logging.debug(logstr)
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

            wing_part = BooleanCADOperation.cut_list_of_namedshapes(self.namedshape, cutout_list, part_name)
            self.parts_list.append(wing_part)

        self.m.display_slice_x(self.parts_list, logging.NOTSET, f"Sliced {self.namedshape.name()}")

    def slice_with_list_cut(self, list_of_pos: list[float]):
        '''
        Instead of slicing the Shape in equal parts, this method slices the shape in the positions given in a list.
        :param list_of_pos: list[float] with x-koordinates, slicing positions
        '''
        frontbox = None
        rearbox = None
        for i in range(0, len(list_of_pos)):
            part = self.namedshape.shape()
            # Create a box cutout box for the back, and move it wo the postion on the list and cut it from the shape
            rearbox = OPrim.BRepPrimAPI_MakeBox(self.shape_dimensions.get_point(0), self.shape_dimensions.get_length(),
                                                self.shape_dimensions.get_width(),
                                                self.shape_dimensions.get_height()).Shape()
            rearbox = OExs.translate_shp(rearbox, Ogp.gp_Vec(list_of_pos[i], 0, 0))
            part1 = OAlgo.BRepAlgoAPI_Cut(part, rearbox).Shape()
            # Check if its not the last position
            if i != len(list_of_pos):
                lenght = list_of_pos[i]
                if i != 0:
                    logging.debug("Cutting frontbox " + str(i))
                    # Create a box for the front with the lenght of the position on the list and cut it from the shape
                    frontbox = OPrim.BRepPrimAPI_MakeBox(self.shape_dimensions.get_point(0), list_of_pos[i - 1],
                                                         self.shape_dimensions.get_width(),
                                                         self.shape_dimensions.get_height()).Shape()
                    beforecut = part1
                    part1 = OAlgo.BRepAlgoAPI_Cut(beforecut, frontbox).Shape()
                logging.debug(f"Part {i}  {lenght=}")
            self.parts_list.append(part1)
        self.m.display_slice_x(self.parts_list, logging.NOTSET, self.namedshape.name())

    def slicing_positions(self, fuselage_shape):
        result = []
        spacing = 0.0004
        before_wing = self.shape_dimensions.get_x_min() - spacing
        after_wing = self.shape_dimensions.x_max + spacing
        mid_wing = (after_wing + before_wing) / 2
        result.append(before_wing / 2)
        result.append(before_wing)
        result.append(mid_wing)
        result.append(after_wing)
        fuselage_dimensions = ShapeDimensions(fuselage_shape)
        end_fuselage = fuselage_dimensions.get_x_max()
        split_rear_fuselage = (end_fuselage + after_wing) / 2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        logging.debug(result)
        logging.debug(len(result))
        return result
