import logging
import os
import threading
from typing import Callable

import requests

from cadquery import Workplane
from cad_designer.decorators.general_decorators import conditional_execute

from ocp_vscode import *

ocp_vscode_host = os.getenv("OCP_VSCODE_HOST", "127.0.0.1")
ocp_vscode_port = os.getenv("OCP_VSCODE_PORT", 3939)
set_port(ocp_vscode_port, host=ocp_vscode_host)

# Pluggable callback for streaming display output to a custom receiver
# (e.g., SSE endpoint) instead of the OCP Viewer WebSocket.
_display_callback: Callable[[str, dict], None] | None = None
_display_callback_lock = threading.Lock()


def set_display_callback(callback: Callable[[str, dict], None] | None) -> None:
    """Register a callback to receive tessellated display data.

    When set, `display()` tessellates locally and calls
    `callback(name, tessellation_dict)` instead of sending to OCP Viewer.
    Pass None to restore default OCP Viewer behavior.
    """
    global _display_callback
    with _display_callback_lock:
        _display_callback = callback


def _tessellate_for_callback(workplane: Workplane, name: str,
                              colors=None, alphas=None) -> dict | None:
    """Tessellate a workplane and return three-cad-viewer compatible dict."""
    try:
        from ocp_tessellate.convert import to_ocpgroup, tessellate_group, combined_bb
        color_list = [colors] if isinstance(colors, str) else (colors or ["#FF8400"])
        alpha_list = [alphas] if isinstance(alphas, (int, float)) else (alphas or [1.0])
        part_group, instances = to_ocpgroup(
            workplane, names=[name], colors=color_list, alphas=alpha_list,
        )
        instances, shapes, _ = tessellate_group(
            part_group, instances,
            {"deviation": 0.1, "angular_tolerance": 0.2},
        )
        bb = combined_bb(shapes)
        if bb is not None:
            shapes["bb"] = bb.to_dict()
        return {
            "data": {"instances": instances, "shapes": shapes},
            "type": "data",
            "config": {"theme": "dark", "control": "orbit"},
            "count": part_group.count_shapes(),
        }
    except Exception as exc:
        logging.warning("Tessellation for display callback failed for '%s': %s", name, exc)
        return None


@conditional_execute("DISPLAY_CONSTRUCTION_STEP")
def display(self: Workplane, name: str = "NN", severity: int = logging.DEBUG,
            colors=None, alphas=None, **kwargs) -> Workplane:

    if severity >= logging.root.level:
        with _display_callback_lock:
            callback = _display_callback

        if callback is not None:
            # Stream to registered callback (e.g., SSE endpoint)
            tess = _tessellate_for_callback(self, name, colors, alphas)
            if tess is not None:
                try:
                    callback(name, tess)
                except Exception as exc:
                    logging.warning("Display callback error for '%s': %s", name, exc)
        else:
            # Default: send to OCP Viewer via WebSocket
            try:
                push_object(self, name=name, color=colors, alpha=alphas, **kwargs)
                show_objects()
            except requests.exceptions.ConnectionError:
                logging.error(f"could not render '{name}'")
    return self
