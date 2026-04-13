"""
Tessellation Service — converts CadQuery geometry to three-cad-viewer JSON.

Uses the same ocp_tessellate pipeline that powers the OCP CAD Viewer
VS Code extension, ensuring identical rendering quality.

The result is a plain JSON object (no base64 buffers) that can be
sent directly to the three-cad-viewer Viewer.render() method.
"""

import logging
import pickle
import threading
import traceback
from concurrent.futures import Future
from typing import Any, Callable, Dict, Optional

from app.services.cad_service import (
    _get_executor,
    get_aeroplane_with_wings,
    register_pending_task,
    tasks,
    tasks_lock,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background re-tessellation state — debounce timers & cancellable futures
# ---------------------------------------------------------------------------
_pending_timers: dict[str, threading.Timer] = {}
_pending_futures: dict[str, Future] = {}
_timer_lock = threading.Lock()


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
        _logger.error("Full traceback:\n%s", traceback.format_exc())
        return {
            "status": "FAILURE",
            "error": f"Tessellation failed: {type(err).__name__}",
        }


def start_tessellation_task(
    aeroplane_id: str,
    wing_name: str,
    wing_schema_pickle: bytes,
    geometry_hash: str = "",
    wing_scale: float = 1000.0,
) -> None:
    """Submit a tessellation task to the process pool.

    On success, the result is also persisted in the DB cache
    so that GET /tessellation can serve it immediately.
    """
    register_pending_task(f"{aeroplane_id}:tessellation:{wing_name}")

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
            tasks[f"{aeroplane_id}:tessellation:{wing_name}"] = worker_result

        # Persist to DB cache on success
        if worker_result.get("status") == "SUCCESS":
            try:
                from app.db.session import SessionLocal
                from app.models.aeroplanemodel import AeroplaneModel
                from app.services import tessellation_cache_service as cache_svc

                db = SessionLocal()
                try:
                    aeroplane = db.query(AeroplaneModel).filter(
                        AeroplaneModel.uuid == aeroplane_id
                    ).first()
                    if aeroplane:
                        cache_svc.cache_tessellation(
                            db, aeroplane.id, "wing", wing_name,
                            geometry_hash or "manual",
                            worker_result["result"],
                        )
                        logger.info("Cached tessellation for %s/%s", aeroplane_id, wing_name)
                finally:
                    db.close()
            except Exception:
                logger.exception("Failed to cache tessellation result")

    future.add_done_callback(_on_done)


# ---------------------------------------------------------------------------
# Background re-tessellation with debounce + cancellation
# ---------------------------------------------------------------------------

_DEBOUNCE_SECONDS = 2.0


def trigger_background_tessellation(
    aeroplane_id: str,
    wing_name: str,
    wing_schema_pickle: bytes,
    db_session_factory: Callable[[], Any],
    geometry_hash: str,
    wing_scale: float = 1000.0,
) -> None:
    """Trigger a debounced background tessellation for a wing.

    If a tessellation for the same (aeroplane, wing) is already pending
    or running, it is cancelled first. The actual work starts after a
    2-second debounce window — rapid successive calls (e.g. while the
    user drags a slider) only produce one tessellation.

    Args:
        aeroplane_id: UUID string of the aeroplane.
        wing_name: Name of the wing being tessellated.
        wing_schema_pickle: Pickled ASB wing schema for the worker.
        db_session_factory: Callable that returns a new SQLAlchemy Session
            (typically ``SessionLocal`` from ``app.db.session``).
        geometry_hash: Hash of the current geometry, used to detect
            staleness when the worker finishes.
        wing_scale: Scale factor passed to the tessellation worker.
    """
    key = f"{aeroplane_id}:{wing_name}"

    with _timer_lock:
        # Cancel any pending debounce timer for this key
        existing_timer = _pending_timers.pop(key, None)
        if existing_timer is not None:
            existing_timer.cancel()
            logger.debug("Cancelled pending debounce timer for %s", key)

        # Cancel any running future for this key
        existing_future = _pending_futures.pop(key, None)
        if existing_future is not None:
            existing_future.cancel()
            logger.debug("Cancelled running future for %s", key)

        # Start a new debounce timer
        timer = threading.Timer(
            _DEBOUNCE_SECONDS,
            _start_tessellation_and_cache,
            args=(
                aeroplane_id,
                wing_name,
                wing_schema_pickle,
                db_session_factory,
                geometry_hash,
                wing_scale,
            ),
        )
        timer.daemon = True
        _pending_timers[key] = timer
        timer.start()
        logger.info(
            "Scheduled background tessellation for %s (debounce %.1fs)",
            key,
            _DEBOUNCE_SECONDS,
        )


def _start_tessellation_and_cache(
    aeroplane_id: str,
    wing_name: str,
    wing_schema_pickle: bytes,
    db_session_factory: Callable[[], Any],
    geometry_hash: str,
    wing_scale: float,
) -> None:
    """Submit the tessellation to the process pool and cache on completion.

    Called by the debounce timer — runs on a daemon thread, not the
    main thread.
    """
    from app.services import tessellation_cache_service as cache_svc

    key = f"{aeroplane_id}:{wing_name}"

    # Clean up the timer reference (it has already fired)
    with _timer_lock:
        _pending_timers.pop(key, None)

    # Submit to the process pool
    future = _get_executor().submit(
        _run_tessellation_worker,
        aeroplane_id,
        wing_schema_pickle,
        wing_name,
        wing_scale,
    )

    with _timer_lock:
        _pending_futures[key] = future

    def _on_background_done(f: Future) -> None:
        # Remove from pending futures
        with _timer_lock:
            _pending_futures.pop(key, None)

        try:
            worker_result = f.result()
        except Exception as exc:
            logger.error("Background tessellation failed for %s: %s", key, exc)
            return

        if worker_result.get("status") != "SUCCESS":
            logger.warning(
                "Background tessellation returned non-SUCCESS for %s: %s",
                key,
                worker_result.get("error", "unknown"),
            )
            return

        # Resolve the integer aeroplane_id from the UUID for DB operations
        db = db_session_factory()
        try:
            from app.models.aeroplanemodel import AeroplaneModel

            aeroplane = (
                db.query(AeroplaneModel)
                .filter(AeroplaneModel.uuid == aeroplane_id)
                .first()
            )
            if aeroplane is None:
                logger.warning(
                    "Aeroplane %s not found when caching tessellation", aeroplane_id
                )
                return

            # Check that the geometry hasn't changed while we were running
            if not cache_svc.is_hash_current(
                db, aeroplane.id, "wing", wing_name, geometry_hash
            ):
                logger.info(
                    "Geometry changed while tessellating %s — discarding result", key
                )
                return

            cache_svc.cache_tessellation(
                db,
                aeroplane.id,
                "wing",
                wing_name,
                geometry_hash,
                worker_result["result"],
            )
            logger.info("Cached background tessellation for %s", key)
        except Exception:
            logger.exception("Error caching tessellation for %s", key)
        finally:
            db.close()

    future.add_done_callback(_on_background_done)
