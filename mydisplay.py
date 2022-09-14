from cgitb import text
import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display
from  OCC.Display.SimpleGui import *
import OCC.Extend.ShapeFactory as OExs
import OCC.Core.gp as Ogp
import logging

from abmasse import get_dimensions, get_koordinates

class myDisplay:
    my_instance: 'myDisplay'= None
    
    def __init__(self, distance=5, dev=False) -> None:
        if dev:
            self.display, self.start_display, add_menu, add_function_to_menu = init_display()
            self.id=0
            self.position=0
            self.distance=distance
            self.dev=dev
        else:
            self.dev=False
    
    @staticmethod
    def instance():
        if myDisplay.my_instance is None:
            myDisplay.my_instance= myDisplay(0.5, True)
        return myDisplay.my_instance

    def display_this_shape(self,shape,msg="",trans=False):
        try:
            if self.dev:           
                self.id+=1
                self.position=self.new_position(shape)
                shape=OExs.translate_shp(shape,Ogp.gp_Vec(0.0,self.position,0.0))
                if trans:
                    self.display.DisplayShape(shape, transparency=0.8)    
                else:
                    self.display.DisplayShape(shape)
                self.display.DisplayMessage(point=Ogp.gp_Pnt(0.0,self.position-0.2,0.0), text_to_write=msg)
                self.display.FitAll()
        except:
            logging.warning("Display this Shape: Shape can not be displayed: posible Null")
            self.start()
            
    def new_position(self, shape):
        xmin, ymin, zmin,xmax,ymax,zmax= get_koordinates(shape)
        xdiff,zdiff,ydiff=get_dimensions(xmin, ymin, zmin,xmax,ymax,zmax)
        pos= self.position+ ydiff + self.distance
        #print("ydiff:", ydiff, "pos:", pos)
        return pos
          
    def get_display(self):
        return self.display
    
    def display_in_origin(self,shape,trans=False):
        shape=OExs.translate_shp(shape,Ogp.gp_Vec(0,0.0,0.0))
        if trans:
            self.display.DisplayShape(shape, transparency=0.8) 
        else:
            self.display.DisplayShape(shape)
        
        
    def display_this_shape2(shape):
        display, start_display, add_menu, add_function_to_menu = init_display()
        display.DisplayShape(shape) 
        display.FitAll()
        start_display()
    
    def start(self):
        if self.dev:
            self.start_display()


