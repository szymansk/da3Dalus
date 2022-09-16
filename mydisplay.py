from cgitb import text
from pickle import FALSE
import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display
from  OCC.Display.SimpleGui import *
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp
import logging

from abmasse import *

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
        else:
            self.dev=False
    
    @staticmethod
    def instance(dev):

        if myDisplay.my_instance is None:
            if dev:
                myDisplay.my_instance= myDisplay(0.5, True)
            else:
                myDisplay.my_instance=myDisplay()
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

        xdiff,ydiff,zdiff=get_dimensions_from_Shape(shape)
        pos= self.y_position+ self.distance + (ydiff/2)
        #print("ydiff:", ydiff, "pos:", pos)
        return pos
          
    def get_display(self):
        return self.display
    
    def display_in_origin(self,shape,trans=False):
        if self.dev:
            shape=OExs.translate_shp(shape,Ogp.gp_Vec(0.0,self.origin,0.0))
            if trans:
                self.display.DisplayShape(shape, transparency=0.8) 
            else:
                self.display.DisplayShape(shape)
            
    def display_fuse(self, fused_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1=OExs.translate_shp(shape1,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            shape2=OExs.translate_shp(shape2,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="GREEN")
            self.display_this_shape(fused_shape, msg, trans)
        
    def display_cut(self, cuted_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1=OExs.translate_shp(shape1,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            shape2=OExs.translate_shp(shape2,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            self.display.DisplayShape(shape1, transparency=0.8)
            self.display.DisplayShape(shape2, color="RED")
            self.display_this_shape(cuted_shape, msg, trans)
    
    def display_common(self, common_shape, shape1, shape2, msg="", trans=False):
        if self.dev:
            shape1=OExs.translate_shp(shape1,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            shape2=OExs.translate_shp(shape2,Ogp.gp_Vec(0.0,self.y_position,-self.distance))
            self.display.DisplayShape(shape1, color="Yellow", transparency=0.8)
            self.display.DisplayShape(shape2)
            self.display_this_shape(common_shape, msg, trans)
        
    def display_slice_x(self, parts_list, name=""):
        if self.dev:
            x_position= 0 
            x_position_msg=x_position
            for i,part in enumerate(parts_list):
                part=OExs.translate_shp(part,Ogp.gp_Vec(x_position,self.y_position, 0.0))
                self.display.DisplayShape(part)
                x,y,z= get_dimensions_from_Shape(part)
                msg= name + str(i)
                self.display.DisplayMessage(point=Ogp.gp_Pnt(x_position,self.y_position-0.2,0.0), text_to_write=msg)
                x_position+= self.distance/4
                x_position_msg+= (x_position+ x)
            
        
    def display_this_shape2(shape):
        display, start_display, add_menu, add_function_to_menu = init_display()
        display.DisplayShape(shape) 
        display.FitAll()
        start_display()
    
    def start(self):
        if self.dev:
            self.start_display()


