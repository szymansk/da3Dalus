import OCC.Core.BRepAlgoAPI as OAlgo
from mydisplay import *

def fuse_list_of_shapes(list, msg=""):
    fused=[]
    shape=None
    md= myDisplay.instance()
    for shape in list:
        if not fused:
            fused.append(shape)
        else:
            fused.append(OAlgo.BRepAlgoAPI_Fuse(fused[-1],shape).Shape())
    md.display_fuse(fused[-1],fused[-2], shape,msg)
    return fused[-1]