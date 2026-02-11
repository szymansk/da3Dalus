import logging
import os
import requests

from cadquery import Workplane
from cad_designer.decorators.general_decorators import conditional_execute

from ocp_vscode import *

ocp_vscode_host = os.getenv("OCP_VSCODE_HOST", "127.0.0.1")
ocp_vscode_port = os.getenv("OCP_VSCODE_PORT", 3939)
set_port(ocp_vscode_port, host=ocp_vscode_host)

@conditional_execute("DISPLAY_CONSTRUCTION_STEP")
def display(self: Workplane, name: str = "NN", severity: int = logging.DEBUG,
            colors=None, alphas=None, **kwargs) -> Workplane:

    if severity >= logging.root.level:
        try:
            push_object(self, name=name, color=colors, alpha=alphas, **kwargs)
            show_objects()
        except requests.exceptions.ConnectionError as e:
            logging.error(f"could not render '{name}'")
            pass
    return self
