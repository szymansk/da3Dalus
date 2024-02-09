import cadquery as cq
import logging

from cadquery import Workplane

from cadq_server.cadq_server_connector import CQServerConnector
from cq_plugins.sew_fix_shape.sew_fix_shape import sewAndFixShape


def _display(self: Workplane, name: str = "", color: cq.Color = cq.Color("gold"), severity: int = logging.NOTSET,
             url: str = "http://cq-server:5000/json") -> Workplane:
    if severity >= logging.root.level:
        _display._connector = _display._connector if _display._connector is not None else CQServerConnector(url=url)
        _display._connector.render(name=name, cq_model=self)
    return self

_display._connector = None
Workplane.display = _display






