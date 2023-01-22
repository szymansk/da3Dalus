import cadquery as cq
import logging
from cadq_server.cadq_server_connector import CQServerConnector

_display_assembly: cq.Assembly = cq.Assembly()

def _display(self: cq.Workplane, name: str = "", severity: int = logging.NOTSET, url: str = "http://cq-server:5000/json") -> cq.Workplane:
    if severity >= logging.root.level:
        _display_assembly.add(self)
        connector = CQServerConnector(url=url)
        connector.render(name=name,cq_model=_display_assembly)
    return self

cq.Workplane.display = _display
