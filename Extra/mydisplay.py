import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display
from OCC.Core.Graphic3d import Graphic3d_RenderingParams
from  OCC.Display.SimpleGui import *
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp
import OCC.Core.BRepPrimAPI as OPrim
import logging

from _alt.abmasse import *

class myDisplay:
    my_instance: 'myDisplay'= None
    
    def __init__(self, distance=0.5, dev=False) -> None:
        if dev:
            self.display, self.start_display, add_menu, add_function_to_menu = init_display()
            self.id=0
            self.y_position=0
            self.distance=distance
            self.dev=dev
            self.origin= -distance
            self.half_widht= None
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
            add_function_to_menu("view",self.myview_Top)
            add_function_to_menu("view",self.myview_Bottom)
            add_function_to_menu("view", self.myview_Right)
            add_function_to_menu("view", self.myview_Left)
            add_function_to_menu("view", self.myview_Front)
            add_function_to_menu("view", self.myview_Rear)
        else:
            self.dev=False
    
    @staticmethod
    def instance(dev=False, distance=1):

        if myDisplay.my_instance is None:
            if dev:
                myDisplay.my_instance= myDisplay(distance, True)
            else:
                myDisplay.my_instance=myDisplay(distance)
        return myDisplay.my_instance

    def display_this_shape(self,shape,msg="",trans=False):
        if self.dev:
            try:           
                self.id+=1                
                shape=OExs.translate_shp(shape,Ogp.gp_Vec(0.0,self.y_position,0.0))
                #self.y_position=self.my_y_position(shape)
                if trans:
                    self.display.DisplayShape(shape, transparency=0.8)    
                else:
                    self.display.DisplayShape(shape)
                self.display.DisplayMessage(point=Ogp.gp_Pnt(0.0,self.y_position-0.2,0.0), text_to_write=msg)
                self.display.FitAll()
                self.y_position=self.next_y_position(shape)
            except:
                logging.warning("Display this Shape: Shape can not be displayed: posible Null")
                self.start()
            
    def my_y_position(self, shape):

        xdiff,ydiff,zdiff=get_dimensions_from_Shape(shape)
        pos= self.y_position + (ydiff/2)
        #print("ydiff:", ydiff, "pos:", pos)
        return pos
    
    def next_y_position(self, shape):

        xdiff, self.ydiff, zdiff = get_dimensions_from_Shape(shape)
        pos = self.y_position + self.distance + (self.ydiff / 2)
        # print("ydiff:", ydiff, "pos:", pos)
        return pos
          
    def get_display(self):
        return self.display
    
    def display_in_origin(self,shape,text="",trans=False):
        if self.dev:
            shape=OExs.translate_shp(shape,Ogp.gp_Vec(0.0,self.origin,0.0))
            if trans:
                self.display.DisplayShape(shape, transparency=0.8) 
            else:
                self.display.DisplayShape(shape)
        self.display.FitAll()
    
    def display_point_in_origin(self,point:Ogp.gp_Pnt,radius=0.005,text=""):
        if self.dev:
            sphere = OPrim.BRepPrimAPI_MakeSphere(point, radius).Shape()
            tpoint = point
            ypos = point.Y() + self.origin
            print(f"{ypos=} = {point.Y()=} {self.origin=}")
            tpoint.SetY(ypos)
            self.display.DisplayMessage(point, text_to_write=text)
            self.display.DisplayMessage(point, text)
            self.display_in_origin(sphere, text, True)
            
    def display_fuse(self, fused_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1=OExs.translate_shp(shape1,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            shape2=OExs.translate_shp(shape2,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="GREEN")
            self.display_this_shape(fused_shape, msg, trans)
            self.display.FitAll()
        
    def display_cut(self, cuted_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1=OExs.translate_shp(shape1,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            shape2=OExs.translate_shp(shape2,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="RED")
            self.display_this_shape(cuted_shape, msg, trans)
            self.display.FitAll()

    def display_common(self, common_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1 = OExs.translate_shp(shape1, Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            shape2 = OExs.translate_shp(shape2, Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(shape1, color="Yellow", transparency=0.8)
            self.display.DisplayShape(shape2)
            self.display_this_shape(common_shape, msg, trans)
            self.display.FitAll()

    def display_multipe_cuts(self, shape, list_to_cut, msg="", trans=False):
        if self.dev:
            shape = OExs.translate_shp(shape, Ogp.gp_Vec(0.0, self.y_position, -self.distance))
            self.display.DisplayShape(shape, transparency=0.8)
            for shape_to_cut in list_to_cut:
                shape_n = OExs.translate_shp(shape_to_cut, Ogp.gp_Vec(0.0, self.y_position, -self.distance))
                self.display.DisplayShape(shape_n, color="Red", transparency=0.5)
            self.display_this_shape(shape, msg, trans)
            self.display.FitAll()

    def display_slice_x(self, parts_list, name=""):
        if self.dev:
            x_position = 0
            x_position_msg = x_position
            for i, part in enumerate(parts_list):
                msg = f"displaying {name} {i}"
                logging.info(msg)
                part = OExs.translate_shp(part, Ogp.gp_Vec(x_position, self.y_position, 0.0))
                self.display.DisplayShape(part)
                x, y, z = get_dimensions_from_Shape(part)
                # self.display.DisplayMessage(point=Ogp.gp_Pnt(x_position,self.y_position-0.2,0.0), text_to_write=msg)
                x_position += self.distance / 16
                x_position_msg += (x_position + x)

    def display_this_shape2(self, shape):
        if self.dev:
            display, start_display, add_menu, add_function_to_menu = init_display()
            display.DisplayShape(shape)
            display.FitAll()
            start_display()

    def start(self):
        if self.dev:
            self.start_display()

    def perspective(self, event=None):
        self.display.SetPerspectiveProjection()
        self.display.FitAll()


    def orthographic(self,event=None):
        self.display.SetOrthographicProjection()
        self.display.FitAll()


    def anaglyph_red_cyan(self,event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_RedCyan_Simple)
        self.display.FitAll()


    def anaglyph_red_cyan_optimized(self,event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_RedCyan_Optimized)
        self.display.FitAll()


    def anaglyph_yellow_blue(self,event=None):
        self.display.SetAnaglyphMode(Graphic3d_RenderingParams.Anaglyph_YellowBlue_Simple)
        self.display.FitAll()


    def anaglyph_green_magenta(self,event=None):
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

