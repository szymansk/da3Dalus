from __future__ import print_function
import enum
from math import radians
from turtle import Shape
from unicodedata import mirrored, name


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories

import OCC.Core.BRep as OBrep
import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import OCC.Core.BRepFeat as OFeat
import OCC.Core.BRepGProp  as OProp
import OCC.Core.BRepOffset as OOffset
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.BRepTools as OTools
import OCC.Core.gp as Ogp
import OCC.Core.TopoDS as OTopo
import OCC.Extend.ShapeFactory as OExs
import time
from OCC.Display.SimpleGui import init_display
import tigl3.boolean_ops as TBoo
from Ausgabeservice import write_stl_file2
from abmasse import *
from mydisplay import myDisplay
from Wand_erstellen import *
import logging
import BooleanOperationsForLists

def get_tigl_handler(i_cpacs):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    if i_cpacs==0:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v6.xml")
    if i_cpacs==1:
        tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
    #if i_cpacs==2:
        #tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle

def get_points_of_segment(amount:int, wing:TConfig.CCPACSWing,section= 0):
    #0= root 1=tip
    if section==1:
        wing_seg:TConfig.CCPACSWingSegment= wing.get_segment(wing.get_segment_count())
        seg_wire:OTopo.TopoDS_Wire=wing_seg.get_outer_wire()
        section_name="Tip_Section_wire"
    else:
        wing_seg:TConfig.CCPACSWingSegment= wing.get_segment(1)
        seg_wire:OTopo.TopoDS_Wire=wing_seg.get_inner_wire()
        section_name="Root_Section_wire"
    xmin,ymin,zmin,xmax,ymax,zmax=get_koordinates(seg_wire)
    logging.info(f"{section_name} {xmin=:.3f} {ymin=:.3f} {zmin=:.3f} {xmax=:.3f} {ymax=:.3f} {zmax=:.3f}")
    lenght, width, height= get_dimensions_from_Shape(seg_wire)
    logging.info(f"{section_name} {lenght=:.3f} {width=:.3f} {height=:.3f}")
    x_diff=lenght/(amount+1)
    x_list=[]
    for i in range(1,amount+1):
        new_x=xmin+(i*x_diff)
        logging.info(f"adding {new_x=:.3f}")
        x_list.append(new_x)
    y=ymax
    z=zmin
    logging.info(f"{y=:.3f} {z=:.3f}")
    return x_list,y,z

def make_oriented_horizontal_ribs(root_x_list,tip_x_list,w_ymin,w_zmin, lenght, width, height, rib_width):
    ribs=[]
    for i,x in enumerate(root_x_list):
        ribs.append(make_single_box_rib(root_x_list[i],tip_x_list[i],w_ymin,w_zmin, lenght, width, height, rib_width))
    fused_ribs=BooleanOperationsForLists.fuse_list_of_shapes(ribs)
    return fused_ribs
    
    
def make_single_box_rib(x_root,x_tip,y_pos,z_pos, lenght, width, height, rib_width=0.0004):
    corner_points=[]
    #point1
    x=x_root+(rib_width/2)
    logging.info(f"test {x_root=:.6f} {x=:.6f}")
    y=y_pos
    z=z_pos
    corner_points.append(gp_Pnt(x,y,z))
    #m.display_point_in_origin(corner_points[-1])
    
    #point2
    x=x_tip+(rib_width/2)
    y=y_pos+width
    z=z_pos
    corner_points.append(gp_Pnt(x,y,z))
    #m.display_point_in_origin(corner_points[-1])
    
    
    #point3
    x=x_tip-(rib_width/2)
    y=y
    z=z_pos
    corner_points.append(gp_Pnt(x,y,z))
    #m.display_point_in_origin(corner_points[-1])
    
    #point4
    x=x_root-(rib_width/2)
    y=y_pos
    z=z_pos
    corner_points.append(gp_Pnt(x,y,z))
    #m.display_point_in_origin(corner_points[-1])
    
    mkw = BRepBuilderAPI_MakeWire()
    for i,point in enumerate(corner_points):
        if point!= corner_points[-1]:
            mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[i+1]).Edge())
            logging.info(f"{i=}")
        else:
            mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[0]).Edge())
    
    box= BRepPrimAPI_MakePrism(
            BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
            gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, height)),
        ).Shape()
    #m.display_in_origin(box)
    return box
    
    
    
OTools.BRepTools_ReShape()

m= myDisplay.instance(True)


tigl_handle= get_tigl_handler(0)
config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)

wing: TConfig.CCPACSWing= cpacs_configuration.get_wing(1)   
wing_loft: TGeo.CNamedShape = wing.get_loft()
wing_shape: OTopo.TopoDS_Shape = wing_loft.shape()
w_xmin,w_ymin,w_zmin,w_xmax,w_ymax,w_zmax=get_koordinates(wing_shape)
lenght, width, height=get_dimensions_from_Shape(wing_shape)
print(f"Wing {w_xmin=:.3f} {w_ymin=:.3f} {w_zmin=:.3f} {w_xmax=:.3f} {w_ymax=:.3f} {w_zmax=:.3f}")
print(f"Wing diff {lenght=:.3f} {width=:.3f} {height=:.3f}")
m.display_in_origin(wing_shape,True)

root_x_list,wire_y,wire_z=get_points_of_segment(5,wing,0)
for wire_x in root_x_list:
    point:Ogp.gp_Pnt =Ogp.gp_Pnt(wire_x,wire_y,wire_z)
    sphere = OPrim.BRepPrimAPI_MakeSphere(point, 0.002).Shape()
    m.display_in_origin(sphere,True)
print(f"{root_x_list=}")

tip_x_list,wire_y,wire_z=get_points_of_segment(5,wing,1)
for wire_x in tip_x_list:
    point:Ogp.gp_Pnt =Ogp.gp_Pnt(wire_x,wire_y,wire_z)
    sphere = OPrim.BRepPrimAPI_MakeSphere(point, 0.002).Shape()
    m.display_in_origin(sphere)
print(f"{tip_x_list=}")

rib_width=0.0004
hor=make_oriented_horizontal_ribs(root_x_list,tip_x_list,w_ymin,w_zmin, lenght, width, height, rib_width)
m.display_in_origin(hor)


'''
wing_seg:TConfig.CCPACSWingSegment= wing.get_segment(4)
print("segment Count:" + str(wing.get_segment_count()))
seg_wire:OTopo.TopoDS_Wire=wing_seg.get_inner_wire()
seg_wire:OTopo.TopoDS_Wire=wing_seg.get_outer_wire()
print(type(seg_wire))
w_xmin,w_ymin,w_zmin,w_xmax,w_ymax,w_zmax=get_koordinates(seg_wire)
print("Wire", "x", w_xmin,"y",w_ymin,"z",w_zmin,"x",w_xmax,"y",w_ymax,"z",w_zmax )
point:Ogp.gp_Pnt =Ogp.gp_Pnt(w_xmax,w_ymax,w_zmax)
print(point.X(), point.Y(), point.Z())
sphere = OPrim.BRepPrimAPI_MakeSphere(point, 0.01).Shape()
m.display_in_origin(sphere)

wing_sec:TConfig.CCPACSWingSection= wing.get_section(5)
print("sektion Count:" + str(wing.get_section_count()))
wing_element:TConfig.CCPACSWingSectionElement=wing_sec.get_section_element(1)
airfoil=wing_element.get_airfoil_uid()
uid=wing_element.get_uid()
print(str(airfoil) + str(uid))
'''




#Set up the mirror
#wing1: TConfig.CCPaACSWing= cpacs_configuration.get_wing(3)   
#wing_loft1: TGeo.CNamedShape = wing1.get_loft()
#wing_shape1: OTopo.TopoDS_Shape = wing_loft1.shape()


print("Done")
    
m.start()


    
