import logging
import requests

from cadquery import Workplane
from cad_designer.decorators.general_decorators import conditional_execute


@conditional_execute("DISPLAY_CONSTRUCTION_STEP")
def display(self: Workplane, name: str = "NN", severity: int = logging.DEBUG,
             url: str = "http://cq-server:5000/json", names=None, colors=None, alphas=None, **kwargs) -> Workplane:
    from cad_designer.cq_plugins.display.cadq_server_connector import CQServerConnector
    if severity >= logging.root.level:
        display._connector = display._connector if display._connector is not None else CQServerConnector(url=url)
        try:
            display._connector.render(name=name, cq_model=self, names=names, colors=colors, alphas=alphas, **kwargs)
        except requests.exceptions.ConnectionError as e:
            logging.error(f"could not render '{name}'")
            pass
    return self







