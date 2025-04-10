import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

import cadquery as cq
from cad_designer.cq_plugins import CQServerConnector
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox

if __name__ == "__main__":
    display = CQServerConnector("http://cq-server:5000/json")

    model = cq.Workplane().box(1, 10, 1)

    box = BRepPrimAPI_MakeBox(1,1,1)

    display.render("test_model", model)
