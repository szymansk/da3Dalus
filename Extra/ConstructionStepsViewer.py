import OCP.BRepPrimAPI as OPrim

import OCP.gp as Ogp
from OCP.Aspect import Aspect_TOM_BALL, Aspect_TypeOfMarker
from cadq_server import CQServerConnector
from cadquery import Workplane, Assembly, Color

import logging


class ConstructionStepsViewer:
    distance: float
    my_instance: CQServerConnector = None

    def __init__(self, distance=0.5, dev=False, log=False) -> None:
        self.dev = dev
        if dev:
            self.display = CQServerConnector("http://cq-server:5000/json")
        else:
            self.dev = False

    @staticmethod
    def instance(dev=False, distance=1, log=False):

        if ConstructionStepsViewer.my_instance is None:
            if dev:
                ConstructionStepsViewer.my_instance = ConstructionStepsViewer(distance, True, log)
            else:
                ConstructionStepsViewer.my_instance = ConstructionStepsViewer(distance)
        return ConstructionStepsViewer.my_instance

    def display_this_shape(self, named_shape: Workplane, severity, msg="", trans=False) -> None:
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, named_shape)

    def display_point_on_shape(self, named_shape: Workplane, p: Ogp.gp_Pnt, severity, msg="", color="GREEN", trans=True) -> None:
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, named_shape)

    def display_points(self, points: list[tuple[Ogp.gp_Pnt]], severity, msg="", color="RED") -> None:
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, named_shape)

    def display_points_on_shape(self,  named_shape: Workplane,points: list[tuple[Ogp.gp_Pnt]], severity, msg="", color="RED", trans=True, point_aspect: Aspect_TypeOfMarker = Aspect_TOM_BALL) -> None:
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, named_shape)

    def my_y_position(self, named_shape: Workplane):
        #shape_dimensions = sd.ShapeDimensions(named_shape)
        #pos = self.y_position + (shape_dimensions.get_y_mid())
        #return pos
        pass

    def next_y_position(self, named_shape: Workplane):

        #shape_dimensions = sd.ShapeDimensions(named_shape)
        #ydiff = shape_dimensions.get_width()
        #pos = self.y_position + self.distance + ydiff
        # print("ydiff:", ydiff, "pos:", pos)
        #return pos
        pass

    def get_display(self):
        return self.display

    def display_in_origin(self, named_shape: Workplane, severity, text="", trans=False):
        if self.dev and severity >= logging.root.level:
            moved_shape = OExs.translate_shp(named_shape.shape(), Ogp.gp_Vec(0.0, self.origin, 0.0))
            if trans:
                self.display.DisplayShape(moved_shape, text, transparency=0.8)
            else:
                self.display.DisplayShape(moved_shape, text)
        self.display.FitAll()

    def display_in_secondfloor(self, named_shape: Workplane, text="", trans=False):
        if self.dev:
            moved_shape = OExs.translate_shp(named_shape.shape(), Ogp.gp_Vec(0.0, self.origin, -self.origin))
            if trans:
                self.display.DisplayShape(moved_shape, text, transparency=0.8)
            else:
                self.display.DisplayShape(moved_shape, text)
        self.display.FitAll()

    def display_point_in_origin(self, point: Ogp.gp_Pnt, radius=0.005, text=""):
        if self.dev:
            sphere = OPrim.BRepPrimAPI_MakeSphere(point, radius).Shape()
            tpoint = point
            ypos = point.Y() + self.origin
            print(f"{ypos=} = {point.Y()=} {self.origin=}")
            tpoint.SetY(ypos)
            if self.log:
                self.display.DisplayMessage(point, text_to_write=text)
            named_spere = Workplane(sphere, text)
            self.display_in_origin(named_spere, logging.NOTSET, text, True)

    def display_fuse(self, fused_shape: Workplane, named_shape1: Workplane,
                     named_shape2: Workplane, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, fused_shape)

    def display_fused_shapes(self, fused_shape: Workplane, shape_dict: dict[str, Workplane], severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, fused_shape)

    def display_cut_shapes(self, cut_shape: Workplane, shape_dict: dict[str, Workplane], severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, cut_shape)


    def display_cut(self, result: Workplane, minuend: Workplane, subtrahend: Workplane,
                    severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            min_ass = Assembly()
            min_ass.add(minuend).color = Color("blue")
            sub_ass = Assembly()
            sub_ass.add(subtrahend).color=Color("red")
            res_ass = Assembly()
            res_ass.add(result).add(min_ass).add(sub_ass)
            self.display.render(msg, res_ass)

    def display_scale_larger(self, scaled_shape: Workplane, scaled: Workplane, to_be_scaled: Workplane,
                    severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, scaled_shape)

    def display_common(self, common_shape: Workplane, named_shape1: Workplane,
                       named_shape2: Workplane, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, common_shape)

    def display_offset(self, common_shape: Workplane, named_shape1: Workplane,
                       named_shape2: Workplane, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, common_shape)

    def display_multipe_cuts(self, cuted_shape: Workplane, original_shape: Workplane, severity,
                             list_to_cut=list[: Workplane], msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, cuted_shape)

    def display_colission(self, kollision_shape: Workplane, named_shape1: Workplane,
                          named_shape2: Workplane, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            self.display.render(msg, kollision_shape)

    def display_slice_x(self, parts_list: list[Workplane], severity, name=""):
        if self.dev and severity >= logging.root.level:
            self.display.render(name, parts_list)

    
