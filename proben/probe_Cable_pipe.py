from OCC.Core.ChFi2d import * #ChFi2d_AnaFilletAlgo
import logging

import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo
from Airplane.Wing.CablePipe import CabelPipe
from OCC.Core.ChFi2d import *  # ChFi2d_AnaFilletAlgo

from Extra.ConstructionStepsViewer import ConstructionStepsViewer
from _alt.Wand_erstellen import *
from _alt.abmasse import *


def filletEdges(ed1, ed2):
    radius = 0.003
    f = ChFi2d_AnaFilletAlgo()
    f.Init(ed1,ed2,Ogp.gp_Pln())
    f.Perform(radius)
    return f.Result(ed1, ed2)

def pipe():
    # the points
    p1 = gp_Pnt(0,0,0)
    p2 = gp_Pnt(0,1,0)
    p3 = gp_Pnt(1,2,0)
    p4 = gp_Pnt(2,2,0)

    '''
    p1 = gp_Pnt(0.0,0.0,0.0)#-0.022)
    p2 = gp_Pnt(0.0,0.285,0.0)#-0.055)
    p3 = gp_Pnt(0.0,0.35,0.258)#-0.055)
    p4 = gp_Pnt(0.0,0.5,0.258)#-0.055)
    '''
    # the edges
    ed1 = BRepBuilderAPI_MakeEdge(p1,p2).Edge()
    ed2 = BRepBuilderAPI_MakeEdge(p2,p3).Edge()
    ed3 = BRepBuilderAPI_MakeEdge(p3,p4).Edge()
    # inbetween
    fillet12 = filletEdges(ed1, ed2)
    fillet23 = filletEdges(ed2, ed3) 
    # the wire
    makeWire = BRepBuilderAPI_MakeWire()
    makeWire.Add(ed1)
    makeWire.Add(fillet12)
    makeWire.Add(ed2)
    makeWire.Add(fillet23)
    makeWire.Add(ed3)
    makeWire.Build()
    wire = makeWire.Wire()
    # the pipe
    dir = gp_Dir(1,0,0)
    circle = Ogp.gp_Circ(gp_Ax2(p1,dir), 0.002)
    profile_edge = BRepBuilderAPI_MakeEdge(circle).Edge()
    profile_wire = BRepBuilderAPI_MakeWire(profile_edge).Wire()
    profile_face = BRepBuilderAPI_MakeFace(profile_wire).Face()
    pipe = OBrepOffset.BRepOffsetAPI_MakePipe(wire, profile_face).Shape()
    m.display_in_origin(pipe, logging.NOTSET)

def list_for_pipe1(servo_y_pos, zmax, zmin):
    points=[]
    y_pos=0.00
    points.append(Ogp.gp_Pnt(zmax,y_pos,0.0))
    logging.debug(f"{y_pos=} {zmax=}")
    z=zmin+0.005
    points.append(Ogp.gp_Pnt(z,y_pos,0.0))
    logging.debug(f"{y_pos=} {z=}")
    points.append(Ogp.gp_Pnt(z,servo_y_pos,0.0))
    logging.debug(f"{servo_y_pos=} {z=}")
    return points, z,y_pos

def list_for_pipe2():
    points=[]
    y_pos=0.02
    x_pos=0.02
    points.append(Ogp.gp_Pnt(x_pos,y_pos,0.0))
    points.append(Ogp.gp_Pnt(0.0,y_pos,0.0))
    points.append(Ogp.gp_Pnt(0.0,0.0,0.0))
    return points

def create_pipe(wing_shape):
    xmin,ymin,zmin,xmax,ymax,zmax= get_koordinates(wing_shape)
    wing_lenght, wing_width, wing_height= get_dimensions_from_Shape(wing_shape)
    servo_pos=wing_width*0.45
    points, x,y=list_for_pipe1(servo_pos,zmax,zmin)
    mcp=CabelPipe(points,0.003)
    L_pipe=[]
    L_pipe.append(mcp.get_pipe())
    m.display_in_origin(L_pipe[-1], logging.NOTSET)
    
    points2=list_for_pipe2()
    mcp=CabelPipe(points2,0.003)
    zL_pipe=[]
    zL_pipe.append(mcp.get_pipe())
    zL_pipe.append(OExs.rotate_shape(zL_pipe[-1],gp_OY(),90))
    zL_pipe.append(OExs.translate_shp(zL_pipe[-1],Ogp.gp_Vec(x,servo_pos,0.0)))
    
    L_pipe.append(OAlgo.BRepAlgoAPI_Fuse(L_pipe[-1],zL_pipe[-1]).Shape())
    L_pipe.append(OExs.rotate_shape(L_pipe[-1],gp_OY(),-90))
    x_pos=((2/3)*wing_lenght)+xmin
    z_pos=0.005
    y_pos=0.015
    L_pipe.append(OExs.translate_shp(L_pipe[-1],Ogp.gp_Vec(x_pos,y_pos,z_pos)))
    return L_pipe[-1]

if __name__ == '__main__':
    m=ConstructionStepsViewer.instance(True)
    #pipe()
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    tixi_handle.open(r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
    tigl_handle.open(tixi_handle, "")
    config_manager: TConfig.CCPACSConfigurationManager  = TConfig.CCPACSConfigurationManager_get_instance()
   
    cpacs_configuration: TConfig.CCPACSConfiguration= config_manager.get_configuration(tigl_handle._handle.value)
    wing: TConfig.CCPACSFuselage= cpacs_configuration.get_wing(1)
    name2= wing.get_name()
    wing_loft: TGeo.CNamedShape= wing.get_loft()
    wing_shape: OTopo.TopoDS_Shape=wing_loft.shape()
    m.display_in_origin(wing_shape, logging.NOTSET, True)
    pipe_complete=create_pipe(wing_shape)
    m.display_in_origin(pipe_complete, logging.NOTSET)
    
    m.start()
   