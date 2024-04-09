from datetime import datetime
import json
import logging
import sys
import time
import uuid

import requests

from jupyter_cadquery import PartGroup
from jupyter_cadquery.base import _tessellate_group
from jupyter_cadquery.cad_objects import to_assembly
from jupyter_cadquery.utils import numpy_to_json
from jupyter_cadquery.defaults import get_default, get_defaults
from cadquery import Assembly


class Progress:
    def update(self):
        print(".", end="", flush=True)

def get_json_model(*cad_objs, names=None, colors=None, alphas=None, **kwargs) -> list:
    part_group = to_assembly(
        *cad_objs,
        names=names,
        colors=colors,
        alphas=alphas,
        render_mates=kwargs.get("render_mates", False),
        mate_scale=kwargs.get("mate_scale", 1),
        default_color=kwargs.get("default_color", get_default("default_color")),
        show_parent=kwargs.get("show_parent", get_default("show_parent")),
    )

    if len(part_group.objects) == 1 and isinstance(part_group.objects[0], PartGroup):
        part_group = part_group.objects[0]

    # Do not send defaults for postion, rotation and zoom unless they are set in kwargs
    config = {
        k: v
        for k, v in get_defaults().items()
        if not k in ("position", "rotation", "zoom", "cad_width", "tree_width", "height", "glass")
    }

    for k, v in kwargs.items():
        if v is not None:
            config[k] = v
    try:
        shapes = _tessellate_group(part_group, kwargs, Progress(), config.get("timeit"))
        assembly_json = numpy_to_json(shapes)
    except Exception as error:
        raise CQServerConnectorError('An error occured when tesselating the assembly.') from error

    return json.loads(assembly_json)

def get_data(module_name, json_model) -> dict:
    """Return the data to send to the client, that includes the tesselated model."""

    data = {}

    try:
        data = {
            'module_name': module_name,
            'model': json_model,
            'source': ''
        }
    except CQServerConnectorError as error:
        raise (error)

    return data


class CQServerConnector:
    assembly: Assembly

    def __init__(self, url):
        self.url = url
        CQServerConnector.assembly = Assembly(name="root")

    def render(self, name, cq_model, names=None, colors=None, alphas=None, **kwargs):
        CQServerConnector.assembly.add(cq_model, name=f"{name}_{datetime.now()}")
        json_model = get_json_model(CQServerConnector.assembly, names=names, colors=colors, alphas=alphas, **kwargs)
        json_data = get_data(name, json_model)
        self.post_data(json_data)

    def post_data(self, data):
        # sending post request and saving response as response object
        r = requests.post(url=self.url, json=data, timeout=5)
        # extracting response text 
        #resp = r.text
        #logging.debug(f"Render Response:{resp}")
        return r


class CQServerConnectorError(Exception):
    """Error class used to define ModuleManager errors."""

    def __init__(self, message: str, stacktrace: str = ''):
        self.message = message
        self.stacktrace = stacktrace

        print('Module manager error: ' + message, file=sys.stderr)
        if stacktrace:
            print(stacktrace, file=sys.stderr)

        super().__init__(self.message)
