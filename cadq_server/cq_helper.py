import logging
from cadquery import Workplane
from cadq_server.cadq_server_connector import CQServerConnector

def _display(self: Workplane, name: str = "", severity: int = logging.NOTSET,
             url: str = "http://cq-server:5000/json", names=None, colors=None, alphas=None, **kwargs) -> Workplane:
    if severity >= logging.root.level:
        _display._connector = _display._connector if _display._connector is not None else CQServerConnector(url=url)
        _display._connector.render(name=name, cq_model=self, names=names, colors=colors, alphas=alphas, **kwargs)
    return self

_display._connector = None
Workplane.display = _display






