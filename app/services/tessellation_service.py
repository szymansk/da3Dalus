"""
Tessellation Service — converts CadQuery geometry to three-cad-viewer JSON.

Uses the same ocp_tessellate pipeline that powers the OCP CAD Viewer
VS Code extension, ensuring identical rendering quality.
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


def _run_tessellation_worker(
    aeroplane_id: str,
    wing_schema_pickle: bytes,
    wing_name: str,
    wing_scale: float,
) -> Dict[str, Any]:
    """Worker function for tessellation in a subprocess.

    Builds the wing geometry from the ASB schema, then tessellates
    it using ocp_tessellate — the same pipeline as OCP CAD Viewer.
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

        # Rebuild WingConfiguration in the worker (CadQuery types not picklable)
        wing_schema = pickle.loads(wing_schema_pickle)
        wing_config = asbWingSchemaToWingConfig(wing_schema, scale=wing_scale)

        # Create the wing loft geometry
        creator = WingLoftCreator(
            creator_id="tessellation",
            wing_index=wing_name,
            wing_side="BOTH",
        )
        shape = creator.create(wing_config={wing_name: wing_config})

        _logger.info("Wing geometry created, starting tessellation")

        # Tessellate using ocp_vscode's _convert function
        from ocp_vscode.show import _convert
        result, _mapping = _convert(
            shape,
            names=[wing_name],
            deviation=0.1,
            angular_tolerance=0.2,
            default_color="#FF8400",
            theme="dark",
            control="orbit",
        )

        _logger.info("Tessellation complete for %s / %s", aeroplane_id, wing_name)

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
