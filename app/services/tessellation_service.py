"""
Tessellation Service — converts CadQuery geometry to three-cad-viewer JSON.

Uses the same ocp_tessellate pipeline that powers the OCP CAD Viewer
VS Code extension, ensuring identical rendering quality.

The result is a plain JSON object (no base64 buffers) that can be
sent directly to the three-cad-viewer Viewer.render() method.
"""

import logging
import pickle
import traceback
from typing import Any, Dict, Optional

from app.services.cad_service import (
    _get_executor,
    get_aeroplane_with_wings,
    register_pending_task,
    tasks,
    tasks_lock,
)

logger = logging.getLogger(__name__)


def _numpy_to_list(obj):
    """Recursively convert NumPy arrays to Python lists for JSON serialization."""
    import numpy as np

    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _numpy_to_list(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_numpy_to_list(item) for item in obj]
    return obj


def _run_tessellation_worker(
    aeroplane_id: str,
    wing_schema_pickle: bytes,
    wing_name: str,
    wing_scale: float,
) -> Dict[str, Any]:
    """Worker function for tessellation in a subprocess.

    Builds the wing geometry from the ASB schema, then tessellates
    it using ocp_tessellate. Returns plain JSON (no base64 buffers)
    compatible with three-cad-viewer's Viewer.render() method.
    """
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s [%(levelname)s] [worker] %(message)s",
    )
    _logger = _logging.getLogger(__name__)

    try:
        _logger.info("Starting tessellation for %s / %s", aeroplane_id, wing_name)

        from app.converters.model_schema_converters import asbWingSchemaToWingConfig
        from cad_designer.airplane.creator.wing import WingLoftCreator
        from cadquery import Workplane

        # Rebuild WingConfiguration in the worker (CadQuery types not picklable)
        wing_schema = pickle.loads(wing_schema_pickle)
        wing_config = asbWingSchemaToWingConfig(wing_schema, scale=wing_scale)

        # Create the wing loft geometry via WingLoftCreator
        creator = WingLoftCreator(
            creator_id="tessellation",
            wing_index=wing_name,
            wing_side="BOTH",
            wing_config={wing_name: wing_config},
        )
        result_shapes = creator._create_shape(
            shapes_of_interest={},
            input_shapes={},
        )
        # Get the first result shape (the wing workplane)
        shape = next(iter(result_shapes.values())) if result_shapes else Workplane()

        _logger.info("Wing geometry created, starting tessellation")

        # Use ocp_tessellate directly (not ocp_vscode.show._tessellate
        # which requires a running OCP Viewer connection)
        from ocp_tessellate.convert import to_ocpgroup, tessellate_group, combined_bb

        # Wrap the CadQuery object for tessellation
        part_group, instances = to_ocpgroup(
            shape,
            names=[wing_name],
            colors=["#FF8400"],
            alphas=[1.0],
        )

        # Tessellate with quality parameters
        params = {"deviation": 0.1, "angular_tolerance": 0.2}
        instances, shapes, _mapping = tessellate_group(
            part_group, instances, params, progress=None,
        )

        # Add bounding box
        bb = combined_bb(shapes)
        if bb is not None:
            shapes["bb"] = bb.to_dict()
        else:
            shapes["bb"] = {"xmin": 0, "ymin": 0, "zmin": 0, "xmax": 1, "ymax": 1, "zmax": 1}

        count_shapes = part_group.count_shapes()
        config = {
            "theme": "dark",
            "control": "orbit",
        }

        _logger.info("Tessellation complete (%d shapes), serializing", count_shapes)

        # Convert NumPy arrays to plain Python lists for JSON serialization
        import numpy as np
        shapes_json = _numpy_to_list(shapes)
        instances_json = _numpy_to_list(instances)

        result = {
            "data": {
                "instances": instances_json,
                "shapes": shapes_json,
            },
            "type": "data",
            "config": _numpy_to_list(config),
            "count": int(count_shapes),
        }

        _logger.info("Serialization complete for %s / %s", aeroplane_id, wing_name)

        return {
            "status": "SUCCESS",
            "result": result,
        }

    except Exception as err:
        _logger.error("Tessellation failed: %s", err, exc_info=True)
        return {
            "status": "FAILURE",
            "error": f"{type(err).__name__}: {err}",
            "traceback": traceback.format_exc(),
        }


def start_tessellation_task(
    aeroplane_id: str,
    wing_name: str,
    wing_schema_pickle: bytes,
    wing_scale: float = 0.001,
) -> None:
    """Submit a tessellation task to the process pool."""
    register_pending_task(aeroplane_id)

    future = _get_executor().submit(
        _run_tessellation_worker,
        aeroplane_id,
        wing_schema_pickle,
        wing_name,
        wing_scale,
    )

    def _on_done(f):
        try:
            worker_result = f.result()
        except Exception as exc:
            worker_result = {
                "status": "FAILURE",
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        with tasks_lock:
            tasks[aeroplane_id] = worker_result

    future.add_done_callback(_on_done)
