import random
import uuid

import cadquery as cq
import logging

from OCP.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape

from cadq_server.cadq_server_connector import CQServerConnector

def _display(self: cq.Workplane, name: str = "", color: cq.Color = cq.Color("gold"), severity: int = logging.NOTSET, url: str = "http://cq-server:5000/json") -> cq.Workplane:
    if severity >= logging.root.level:
        _display._connector = _display._connector if _display._connector is not  None else CQServerConnector(url=url)
        _display._connector.render(name=name, cq_model=self)
    return self
_display._connector = None

cq.Workplane.display = _display

def offset3D(self: cq.Workplane, offset: float) -> cq.Workplane:
    solid = self.findSolid()
    maker = BRepOffsetAPI_MakeOffsetShape()
    maker.PerformBySimple(solid.wrapped, offset)
    of_shape = maker.Shape()
    new_solid = cq.Solid(of_shape)
    return self.newObject([new_solid])

cq.Workplane.offset3D = offset3D