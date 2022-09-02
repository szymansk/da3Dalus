


import OCC.Core.TopoDS as OTopo
from OCC.Display.SimpleGui import init_display

def display_this_shape(shape):
    display, start_display, add_menu, add_function_to_menu = init_display()
    display.DisplayShape(shape) 
    display.FitAll()
    start_display()

