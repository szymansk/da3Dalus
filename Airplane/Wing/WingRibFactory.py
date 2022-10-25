from __future__ import print_function
import enum
import math 
from turtle import Shape, distance
from unicodedata import mirrored, name


import tigl3.boolean_ops
import tigl3.configuration
import tigl3.configuration as TConfig
import tigl3.curve_factories
import tigl3.exports as exp
import tigl3.geometry
import tigl3.geometry as TGeo
import tigl3.surface_factories
import tigl3.tigl3wrapper as wr

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
from stl_exporter.Ausgabeservice import write_stl_file2
from _alt.abmasse import *
from Extra.mydisplay import myDisplay
from _alt.Wand_erstellen import *
import logging
import Extra.BooleanOperationsForLists as BooleanOperationsForLists
import Extra.tigl_extractor as tigl_extractor
import Extra.patterns as pat
import dimensions.ShapeDimensions as PDim

class WingRibFactory:
    def __init__(self,tigl_handle,wingNr):
        self.tigl_handle=tigl_handle
        self.config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration= self.config_manager.get_configuration(tigl_handle._handle.value)
        self.wing: TConfig.CCPACSWing= self.cpacs_configuration.get_wing(wingNr)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        self.wing_koordinates=PDim.ShapeDimensions(self.wing_shape)
        self.shape:OTopo.TopoDS_Shape=None
        self.shapes:list=[]
        self.m= myDisplay.instance()
        logging.info(f"{self.wing_koordinates=}")

    def create_ribs_option1(self,horizontal_rib_quantity=5,diagonal_rib_quantity=18, rib_width=0.0004):
        logging.info(f"Creating ribs option1")
        ribs=[]
        logging.info(f" segment Count: {self.wing.get_segment_count()}")
        for index in range(1,self.wing.get_segment_count()+1):
            logging.info(f"{index=}")
            segment:TConfig.CCPACSWingSegment=self.wing.get_segment(index)
            inner:OTopo.TopoDS_Shape=segment.get_inner_closure()
            outer:OTopo.TopoDS_Shape=segment.get_outer_closure()
            
            inner_dimensions= PDim.ShapeDimensions(inner)
            outer_dimensions= PDim.ShapeDimensions(outer)
            inner_x_list=inner_dimensions.get_koordinates_on_achs(horizontal_rib_quantity)
            outer_x_list=outer_dimensions.get_koordinates_on_achs(horizontal_rib_quantity)


            lenght=inner_dimensions.get_length()
            height=inner_dimensions.get_height()
            logging.info(f"{lenght=} {height=}")
            
            x_dif=abs(inner_dimensions.get_xmin()-outer_dimensions.get_xmin())
            y_dif=abs(inner_dimensions.get_ymin()-outer_dimensions.get_ymin())
            width=math.hypot(x_dif,y_dif)
            #horitzontal_ribs
            ribs.append(self._make_oriented_horizontal_ribs(inner_x_list,outer_x_list,inner_dimensions.get_ymin(),inner_dimensions.get_zmin(), lenght, width, height, rib_width))
        
        logging.info(f"ribs list lenght: {len(ribs)}")
        if len(ribs)>1:
            ribs.append(BooleanOperationsForLists.fuse_list_of_shapes(ribs))

        #diagonaleribs
        front_sweep_angle=math.degrees(math.atan(x_dif/y_dif))
        rib_angle=60-front_sweep_angle
        rib_distance=0.05
        rib_quantity=y_dif/0.05
        ribs.append(self._create_diagonal_ribs(rib_width, rib_angle,rib_quantity))
        
        #fused ribs
        ribs.append(OAlgo.BRepAlgoAPI_Fuse(ribs[-1],ribs[-2]).Shape())
        self.m.display_fuse(ribs[-1],ribs[-2],ribs[-3], "complete_ribs")
        
        #trim ribs to wing Shape
        ribs.append(OAlgo.BRepAlgoAPI_Common(self.wing_shape,ribs[-1]).Shape())
        self.m.display_common(ribs[-1], self.wing_shape, ribs[-2])
        self.shapes=ribs
        self.shape=ribs[-1]
    
    def get_shape(self):
        return self.shape
        
    def _get_wire_x_koordinates_of_segment(self, shape, quantity:int, position="inner"):
        wire_dimensions=PDim.ShapeDimensions(shape)
        logging.info(f"{wire_dimensions}")
        x_diff=wire_dimensions.get_length()/(quantity+1)
        x_list=[]
        for i in range(1,quantity+1):
            new_x=wire_dimensions.get_xmin()+(i*x_diff)
            logging.info(f"adding {new_x=:.4f}")
            x_list.append(new_x)
        y=wire_dimensions.get_ymin()
        z=wire_dimensions.get_zmin()
        logging.info(f"{y=:.3f} {z=:.3f}")
        return x_list,y,z

    def _make_oriented_horizontal_ribs(self,root_x_list,tip_x_list,root_y,root_z,lenght, width, height, rib_width):
        logging.info(f"Creating horizontal ribs with {len(root_x_list)} ribs and {rib_width=}")
        ribs=[]

        for i,x in enumerate(root_x_list):
            ribs.append(self._make_single_box_rib(root_x_list[i],tip_x_list[i],root_y,root_z, lenght, width, height, rib_width))
        fused_ribs=BooleanOperationsForLists.fuse_list_of_shapes(ribs)
        return fused_ribs
        
    def _make_single_box_rib(self,x_inner,x_outer,y_pos,z_pos, seg_lenght, seg_width, seg_height, rib_width=0.0004):
        corner_points=[]
        #point1
        x=x_inner+(rib_width/2)
        logging.info(f"test {x_inner=:.6f} {x=:.6f}")
        y=y_pos
        z=z_pos
        corner_points.append(gp_Pnt(x,y,z))
        
        #point2
        x=x_outer+(rib_width/2)
        y=y_pos+seg_width
        z=z_pos
        corner_points.append(gp_Pnt(x,y,z))
        
        #point3
        x=x_outer-(rib_width/2)
        y=y
        z=z_pos
        corner_points.append(gp_Pnt(x,y,z))
        
        #point4
        x=x_inner-(rib_width/2)
        y=y_pos
        z=z_pos
        corner_points.append(gp_Pnt(x,y,z))
        
        mkw = BRepBuilderAPI_MakeWire()
        for i,point in enumerate(corner_points):
            logging.info(f"Creating Edge {i} from {len(corner_points)}")
            if point!= corner_points[-1]:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[i+1]).Edge())
            else:
                mkw.Add(BRepBuilderAPI_MakeEdge(corner_points[i], corner_points[0]).Edge())
            
        logging.info(f"Creating Prism out of Edges")
        prism= BRepPrimAPI_MakePrism(
                BRepBuilderAPI_MakeFace(mkw.Wire()).Face(),
                gp_Vec(gp_Pnt(0.0, 0.0, 0.0), gp_Pnt(0.0, 0.0, seg_height)),
            ).Shape()
        #m.display_in_origin(prism)
        return prism
    
    def _create_diagonal_ribs(self,rib_width,angle,ribs_quantity=None):
        logging.info(f"Creating diagonal ribs: {rib_width=} {angle=} {ribs_quantity=}")
        prim=[]
        xmin,ymin,zmin,xmax,ymax,zmax= get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height= get_dimensions_from_Shape(self.wing_shape)
        prim.append(OPrim.BRepPrimAPI_MakeBox(wing_lenght*2, rib_width, wing_height).Shape())
        prim.append(OExs.rotate_shape(prim[-1],gp_OZ(),angle))
        prim.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(xmin,-rib_width,zmin)))
        self.m.display_this_shape(prim[-1])
        if ribs_quantity==None:
            ribs_distance=0.1
            ribs_quantity=round((wing_width/ribs_distance)*2)
            logging.debug(f"{ribs_quantity=} {wing_width}")
        else:
            ribs_distance=wing_width/ribs_quantity
            ribs_quantity=ribs_quantity*2
        prim.append(pat.create_linear_pattern(prim[-1],ribs_quantity,ribs_distance,"y"))
        prim.append(OExs.translate_shp(prim[-1],Ogp.gp_Vec(0,-wing_width/2,0)))
        self.m.display_this_shape(prim[-1])
        return prim[-1]
    
    def _create_trailing_edge(self):
        wing1=self.wing
        compseg:TConfig.CCPACSWingComponentSegment=wing1.get_component_segment(1)
        control_surface:TConfig.CCPACSControlSurfaces=compseg.get_control_surfaces()
        trailing_edge_devices:TConfig.CCPACSTrailingEdgeDevices=control_surface.get_trailing_edge_devices()
        count=trailing_edge_devices.get_trailing_edge_device_count()
        logging.info(f"{count=}")
        logging.info(trailing_edge_devices)
        trailing_edge_device:TConfig.CCPACSTrailingEdgeDevice=trailing_edge_devices.get_trailing_edge_device(1)
        logging.info(trailing_edge_device)
        loft:TGeo.CNamedShape=trailing_edge_device.get_loft()
        #logging.info(f"{type(loft)}")
        shape=loft.shape()
        self.m.display_in_origin(shape)
        self.m.display_in_origin(self.wing_shape,True)
        

if __name__ == "__main__":
    #tigl_handle= tigl_extractor.get_tigl_handler("aircombat_v7")
    tigl_handle= tigl_extractor.get_tigl_handler("simple_aircraft_v2")
    m=myDisplay.instance(True,6)
    a=WingRibFactory(tigl_handle,1)
    a.create_ribs_option1()
    m.display_in_origin(a.get_shape())
    m.display_in_origin(a.wing_shape)
    #a._create_trailing_edge()
    a.m.start()
    
