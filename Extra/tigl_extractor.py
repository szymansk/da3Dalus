import logging
from tigl3 import tigl3wrapper
from tixi3 import tixi3wrapper
import os


def get_tigl_handler(name, base_dir=r'test_cpacs'):
    tixi_handle = tixi3wrapper.Tixi3()
    tigl_handle = tigl3wrapper.Tigl3()
    if name is not None or name != "":
        name = name + ".xml"
        path = os.path.join(base_dir, name)
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            path = os.path.join(os.pardir, path)
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                logging.error("File not found! Extracting tigl was not possible")
        tixi_handle.open(abs_path)
    else:
        logging.error("Extracting tigl was not possible")
    tigl_handle.open(tixi_handle, "")
    return tigl_handle


def get_tixi_handler(name, base_dir=r'test_cpacs'):
    tixi_handle = tixi3wrapper.Tixi3()
    if name is not None or name != "":
        name = name + ".xml"
        path = os.path.join(base_dir, name)
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            path = os.path.join(os.pardir, path)
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                logging.error("File not found! Extracting tigl was not possible")
        tixi_handle.open(abs_path)
    else:
        logging.error("Extracting tixi was not possible")
    return tixi_handle
