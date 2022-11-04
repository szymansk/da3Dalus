import logging
from tigl3 import tigl3wrapper
# from tigl3.tigl3wrapper import Tigl3, TiglBoolean
from tixi3 import tixi3wrapper
# from tixi3.tixi3wrapper import Tixi3
import os


def get_tigl_handler(name):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    # base_dir= r'C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs'
    base_dir = r'.\test_cpacs'
    if name != None or name != "":
        name = name + ".xml"
        path = os.path.join(base_dir, name)
        tixi_handle.open(path)
    else:
        logging.error("Extracting tigl was not possible")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle
