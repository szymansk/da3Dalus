from cadquery import Workplane

from .cadq_server_connector import CQServerConnector
from .display import display

display._connector = None
Workplane.display = display