import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.geometry as TGeo
from OCC.Core.Graphic3d import Graphic3d_RenderingParams
from OCC.Display.SimpleGui import *

# from Dimensions.ShapeDimensions import ShapeDimensions
import Dimensions.ShapeDimensions as sd

import logging


class ConstructionStepsViewer:
    distance: float
    my_instance: 'ConstructionStepsViewer' = None

    def __init__(self, distance=0.5, dev=False, log=False) -> None:
        if dev:
            self.display, self.start_display, add_menu, add_function_to_menu = init_display()
            self.id = 0
            self.y_position = 0
            self.distance = distance
            self.dev = dev
            self.log = log
            self.origin = -distance
            self.half_widht = None
            add_menu("camera projection")
            add_menu("view")
            add_function_to_menu("camera projection", self.perspective)
            add_function_to_menu("camera projection", self.orthographic)
            add_function_to_menu("camera projection", self.anaglyph_red_cyan)
            add_function_to_menu("camera projection", self.anaglyph_red_cyan_optimized)
            add_function_to_menu("camera projection", self.anaglyph_yellow_blue)
            add_function_to_menu("camera projection", self.anaglyph_green_magenta)
            add_function_to_menu("camera projection", self.exit)
            self.display.View_Top()
            add_function_to_menu("view", self.myview_Top)
            add_function_to_menu("view", self.myview_Bottom)
            add_function_to_menu("view", self.myview_Right)
            add_function_to_menu("view", self.myview_Left)
            add_function_to_menu("view", self.myview_Front)
            add_function_to_menu("view", self.myview_Rear)
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

    def display_this_shape(self, named_shape: TGeo.CNamedShape, severity, msg="", trans=False) -> None:
        if self.dev and severity >= logging.root.level:
            if OTopo.TopoDS_Iterator(named_shape.shape()).More():
                self.id += 1
                shape = OExs.translate_shp(named_shape.shape(), Ogp.gp_Vec(0.0, self.y_position, 0.0))
                if trans:
                    self.display.DisplayShape(shape, transparency=0.8)
                else:
                    self.display.DisplayShape(shape)
                if self.log:
                    self.display.DisplayMessage(point=Ogp.gp_Pnt(0.0, self.y_position - 0.2, 0.0), text_to_write=msg)
                self.display.FitAll()
                self.y_position = self.next_y_position(named_shape)
            else:
                logstr = f"Shape can not be displayed: {msg}"
                logging.warning(logstr)
                self.display.DisplayMessage(point=Ogp.gp_Pnt(0.0, self.y_position - 0.2, 0.0), text_to_write=logstr)
                self.y_position = self.y_position + 3 * self.distance

    def my_y_position(self, named_shape: TGeo.CNamedShape):
        shape_dimensions = sd.ShapeDimensions(named_shape)
        pos = self.y_position + (shape_dimensions.get_y_mid())
        return pos

    def next_y_position(self, named_shape: TGeo.CNamedShape):

        shape_dimensions = sd.ShapeDimensions(named_shape)
        ydiff = shape_dimensions.get_width()
        pos = self.y_position + self.distance + ydiff
        # print("ydiff:", ydiff, "pos:", pos)
        return pos

    def get_display(self):
        return self.display

    def display_in_origin(self, named_shape: TGeo.CNamedShape, severity, text="", trans=False):
        if self.dev and severity >= logging.root.level:
            moved_shape = OExs.translate_shp(named_shape.shape(), Ogp.gp_Vec(0.0, self.origin, 0.0))
            if trans:
                self.display.DisplayShape(moved_shape, text, transparency=0.8)
            else:
                self.display.DisplayShape(moved_shape, text)
        self.display.FitAll()

    def display_in_secondfloor(self, named_shape: TGeo.CNamedShape, text="", trans=False):
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
            named_spere = TGeo.CNamedShape(sphere, text)
            self.display_in_origin(named_spere, logging.NOTSET, text, True)

    def display_fuse(self, fused_shape: TGeo.CNamedShape, named_shape1: TGeo.CNamedShape,
                     named_shape2: TGeo.CNamedShape, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            shape1 = OExs.translate_shp(named_shape1.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            shape2 = OExs.translate_shp(named_shape2.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="GREEN")
            self.display_this_shape(fused_shape, severity=severity,
                                    msg=f"{msg}: {fused_shape.name()}: fusion between {named_shape1.name()} and {named_shape2.name()}",
                                    trans=trans)
            self.display.FitAll()

    def display_cut(self, cuted_shape: TGeo.CNamedShape, named_shape1: TGeo.CNamedShape, named_shape2: TGeo.CNamedShape,
                    severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            shape1 = OExs.translate_shp(named_shape1.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            shape2 = OExs.translate_shp(named_shape2.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="RED")
            self.display_this_shape(cuted_shape, severity=severity, msg=f"{cuted_shape.name()} {msg}", trans=trans)
            self.display.FitAll()

    def display_common(self, common_shape: TGeo.CNamedShape, named_shape1: TGeo.CNamedShape,
                       named_shape2: TGeo.CNamedShape, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            shape1 = OExs.translate_shp(named_shape1.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            shape2 = OExs.translate_shp(named_shape2.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            logging.debug(f"{self.y_position=}")
            self.display.DisplayShape(shape1, color="Yellow", transparency=0.8)
            self.display.DisplayShape(shape2)
            self.display_this_shape(common_shape, severity=severity, msg=f"{common_shape.name()} {msg}", trans=trans)
            self.display.FitAll()

    def display_multipe_cuts(self, cuted_shape: TGeo.CNamedShape, original_shape: TGeo.CNamedShape, severity,
                             list_to_cut=list[: TGeo.CNamedShape], msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            moved_shape = OExs.translate_shp(original_shape.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(moved_shape, transparency=0.8)
            for shape_to_cut in list_to_cut:
                shape_n = OExs.translate_shp(shape_to_cut.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
                self.display.DisplayShape(shape_n, color="Red", transparency=0.5)
            self.display_this_shape(cuted_shape, severity=severity, msg=f"{msg}", trans=trans)
            self.display.FitAll()

    def display_colission(self, kollision_shape: TGeo.CNamedShape, named_shape1: TGeo.CNamedShape,
                          named_shape2: TGeo.CNamedShape, severity, msg="", trans=False):
        if self.dev and severity >= logging.root.level:
            shape1 = OExs.translate_shp(named_shape1.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            shape2 = OExs.translate_shp(named_shape2.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(shape1, color="Yellow", transparency=0.8)
            self.display.DisplayShape(shape2, transparency=0.8)
            if OTopo.TopoDS_Iterator(kollision_shape.shape()).More():
                shape3a = OExs.translate_shp(kollision_shape.shape(), Ogp.gp_Vec(0.0, self.y_position, -self.distance))
                self.display.DisplayShape(shape3a, color="Red")
            self.display_this_shape(kollision_shape, severity=severity,
                                    msg=f"collision between {named_shape1.name()} and {named_shape2.name()}", trans=trans)
            self.display.FitAll()

    def display_slice_x(self, parts_list: list[TGeo.CNamedShape], severity, name=""):
        if self.dev and severity >= logging.root.level:
            x_position = 0
            x_position_msg = x_position
            moved_part: TGeo.CNamedShape = TGeo.CNamedShape()
            for i, part in enumerate(parts_list):
                logging.debug(f"Displaying {part.name()}")
                moved_part = TGeo.CNamedShape(
                    OExs.translate_shp(part.shape(), Ogp.gp_Vec(x_position, self.y_position, 0.0)),
                    f"Moved_{part.name()}")
                self.display.DisplayShape(moved_part.shape())
                part_dimensions = sd.ShapeDimensions(moved_part)
                x_position += self.distance / 16
                x_position_msg += (x_position + part_dimensions.get_length())

            if self.log:
                self.display.DisplayMessage(point=Ogp.gp_Pnt(0.0, self.y_position - 0.2, 0.0), text_to_write=name)
            self.display.FitAll()
            self.y_position = self.next_y_position(moved_part)

    def start(self):
        if self.dev:
            self.start_display()

    def perspective(self, event=None):
        self.display.SetPerspectiveProjection()
        self.display.FitAll()

    def orthographic(self, event=None):
        self.display.SetOrthographicProjection()
        self.display.FitAll()

    def anaglyph_red_cyan(self, event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_RedCyan_Simple)
        self.display.FitAll()

    def anaglyph_red_cyan_optimized(self, event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_RedCyan_Optimized)
        self.display.FitAll()

    def anaglyph_yellow_blue(self, event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_YellowBlue_Simple)
        self.display.FitAll()

    def anaglyph_green_magenta(self, event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_GreenMagenta_Simple)
        self.display.FitAll()

    def myview_Top(self):
        self.display.View_Top()
        self.display.FitAll()

    def myview_Bottom(self):
        self.display.View_Bottom()
        self.display.FitAll()

    def myview_Right(self):
        self.display.View_Right()
        self.display.FitAll()

    def myview_Left(self):
        self.display.View_Left()
        self.display.FitAll()

    def myview_Front(self):
        self.display.View_Front()
        self.display.FitAll()

    def myview_Rear(self):
        self.display.View_Rear()
        self.display.FitAll()

    def exit(event=None):
        sys.exit()
