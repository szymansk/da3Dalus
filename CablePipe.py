import OCC.Core.gp as Ogp
from mydisplay import myDisplay
from Wand_erstellen import *
from OCC.Core.ChFi2d import * #ChFi2d_AnaFilletAlgo
import logging

class CabelPipe:
    def __init__(self, points:list, radius) -> None:
        self.m= myDisplay.instance(True)
        self.points=points
        self.radius=radius
        self.fillet_radius=self.radius*1.5
        print("init complete")
        self.pipe=self.makepipe(points)
        
        
    def get_pipe(self):
        return self.pipe
    
    def filletEdges(self,ed1:OTopo.TopoDS_Edge, ed2):
        radius = 0.003
        if ed1.IsNull:
            logging.info("---Probelem")
        logging.info(f"-----{ed1=} {ed2=}")
        f = ChFi2d_AnaFilletAlgo()
        f.Init(ed1,ed2,Ogp.gp_Pln())
        f.Perform(radius)
        return f.Result(ed1, ed2)

    def makepipe(self,points):
        edges=[]
        fillets=[]
        makeWire = BRepBuilderAPI_MakeWire()
        for i,point in enumerate(points):
            if point!=points[-1]:
                edgex=BRepBuilderAPI_MakeEdge(points[i],points[i+1]).Edge()
                edges.append(edgex)
                logging.info(f"append {edgex}")
                
        for i,edge in enumerate(edges):
            logging.info(f"Making Cabelpipe edge {i}")
            if edge!=edges[-1]:
                fillet=self.filletEdges(edges[i],edges[i+1])
                fillets.append(fillet)
                logging.info(f"---------append {fillet}")
                
        for i,edge in enumerate(edges):
            if edge!=edges[-1]:
                makeWire.Add(edge)
                makeWire.Add(fillets[i])
            else:
                makeWire.Add(edge)
                                
        makeWire.Build()
        wire = makeWire.Wire()
        # the pipe
        dir = gp_Dir(1,0,0)
        circle = Ogp.gp_Circ(gp_Ax2(points[0],dir), self.radius)
        profile_edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        profile_wire = BRepBuilderAPI_MakeWire(profile_edge).Wire()
        profile_face = BRepBuilderAPI_MakeFace(profile_wire).Face()
        pipe = OBrepOffset.BRepOffsetAPI_MakePipe(wire, profile_face).Shape()
        #self.m.display_in_origin(pipe)
        return pipe

'''

if __name__ == '__main__':
    m= myDisplay.instance(True)
    points=[]
    p1 = gp_Pnt(0,0,0)
    p2 = gp_Pnt(0,1,0)
    p3 = gp_Pnt(1,2,0)
    p4 = gp_Pnt(2,2,0)
    points.extend([p1,p2,p3,p4])
    pipe(points)
    m.start()
    
def pipe(point1, point2):
    makeWire = BRepBuilderAPI_MakeWire()
    edge = BRepBuilderAPI_MakeEdge(point1, point2).Edge()
    makeWire.Add(edge)
    makeWire.Build()
    wire = makeWire.Wire()

    dir = gp_Dir(point2.X() - point1.X(), point2.Y() - point1.Y(), point2.Z() - point1.Z())
    circle = Ogp.gp_Circ(gp_Ax2(point1,dir), 0.2)
    profile_edge = BRepBuilderAPI_MakeEdge(circle).Edge()
    profile_wire = BRepBuilderAPI_MakeWire(profile_edge).Wire()
    profile_face = BRepBuilderAPI_MakeFace(profile_wire).Face()
    pipe = OBrepOffset.BRepOffsetAPI_MakePipe(wire, profile_face).Shape()
    m.display_in_origin(pipe)

if __name__ == '__main__':
    m= myDisplay.instance(True)
    pipe(gp_Pnt(0,0,0), gp_Pnt(0,0,1))
    pipe(gp_Pnt(0,0,1), gp_Pnt(0,1,2))     
    pipe(gp_Pnt(0,1,2), gp_Pnt(0,2,2))
    m.start()
'''
'''
m= myDisplay.instance(True)
points=[]
Ogp.gp_Lin()
points.append(gp_Pnt(0.0, 0.0, 0.0))
points.append(gp_Pnt(0.1, 0.0, 0.0))
points.append(gp_Pnt(0.1, 0.3, 0.0))
points.append(gp_Pnt(0.3, 0.3, 0.0))

l=Ogp.gp_Lin(points[0],gp_Dir(0.0,0.0,-1))

wire = BRepBuilderAPI_MakeWire()

for i,point in enumerate(points):
    if i==0:
        pass
    else:
        wire.Add(BRepBuilderAPI_MakeEdge(prev_point, point).Edge())
    prev_point=point

m.start()

'''