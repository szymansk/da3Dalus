"""
CAD Service - Business logic for CAD export operations.

This module contains the core logic for CAD model creation and export,
separated from HTTP concerns for better testability and reusability.

Execution model
---------------
CAD tasks run in a ProcessPoolExecutor, NOT a ThreadPoolExecutor. OCCT
(the C++ backend behind CadQuery) is not thread-safe: the same
`.intersect().clean()` call that completes in ~100ms in the main thread
hangs indefinitely when invoked from a worker thread because OCCT holds
global state (BRepCheck messaging, memory pools, interrupt handlers)
that gets into a blocking state under thread concurrency.

Process isolation fixes this: each worker has its own Python interpreter,
its own main thread, and its own fresh OCCT state. `spawn` context is
used for platform-consistent behaviour (macOS defaults to spawn; Linux
would default to fork which is unsafe with already-loaded OCCT
bindings).
"""

import json
import logging
import multiprocessing
import os
import pickle
import traceback
from concurrent.futures import Future, ProcessPoolExecutor
from threading import Lock
from typing import Any, Dict, Optional, Union
from zipfile import ZipFile

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.converters.model_schema_converters import (
    asb_wing_schema_to_wing_config,
    wing_model_to_asb_wing_schema,
)
from app.core.exceptions import NotFoundError, ValidationError, ConflictError, InternalError
from app.models import AeroplaneModel, WingModel, WingXSecModel
from app.models.aeroplanemodel import (
    FuselageModel,
    WingXSecDetailModel,
    WingXSecTrailingEdgeDeviceModel,
)
from app.schemas import FuselageSchema
from app.schemas.AeroplaneRequest import CreatorUrlType, ExporterUrlType, AeroplaneSettings
from app.services.create_wing_configuration import create_servo
from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration


logger = logging.getLogger(__name__)

# --- Shared literal constant (S1192) ---
_TYPE_KEY = "$TYPE"

# In-memory task management (parent-process state only)
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = Lock()

# Lazy-initialised process pool. Created on first CAD submit; torn down
# on FastAPI lifespan shutdown and between tests (see conftest fixture).
_mp_context = multiprocessing.get_context("spawn")
_executor: Optional[ProcessPoolExecutor] = None
_executor_lock = Lock()


def _get_executor() -> ProcessPoolExecutor:
    """Return the CAD process pool, creating it on first use."""
    global _executor
    with _executor_lock:
        if _executor is None:
            _executor = ProcessPoolExecutor(max_workers=4, mp_context=_mp_context)
    return _executor


def shutdown_executor() -> None:
    """Tear down the CAD process pool.

    Called from the FastAPI lifespan shutdown hook and from the
    `clean_cad_task_state` test fixture so that worker processes do not
    leak between tests.
    """
    global _executor
    with _executor_lock:
        if _executor is not None:
            try:
                _executor.shutdown(wait=False, cancel_futures=True)
            except Exception as exc:
                logger.warning("Error shutting down cad executor: %s", exc)
            _executor = None


def get_aeroplane_with_wings(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """
    Load an aeroplane with all related wings and fuselages.
    
    Raises:
        NotFoundError: If the aeroplane does not exist.
        InternalError: If a database error occurs.
    """
    try:
        plane = (db.query(AeroplaneModel)
                 .options(joinedload(AeroplaneModel.wings)
                          .joinedload(WingModel.x_secs)
                          .joinedload(WingXSecModel.detail)
                          .joinedload(WingXSecDetailModel.spares))
                 .options(joinedload(AeroplaneModel.wings)
                          .joinedload(WingModel.x_secs)
                          .joinedload(WingXSecModel.detail)
                          .joinedload(WingXSecDetailModel.trailing_edge_device)
                          .joinedload(WingXSecTrailingEdgeDeviceModel.servo_data))
                 .options(joinedload(AeroplaneModel.fuselages)
                          .joinedload(FuselageModel.x_secs))
                 .filter(AeroplaneModel.uuid == aeroplane_uuid).first())
        
        if not plane:
            raise NotFoundError(
                message="Aeroplane not found",
                details={"aeroplane_id": str(aeroplane_uuid)}
            )
        return plane
    except SQLAlchemyError as e:
        logger.error(f"Database error when getting aeroplane: {e}")
        raise InternalError(message=f"Database error: {e}")


def get_wing_from_aeroplane(aeroplane: AeroplaneModel, wing_name: str) -> WingModel:
    """
    Get a specific wing from an aeroplane.
    
    Raises:
        NotFoundError: If the wing does not exist.
    """
    wing = next((w for w in aeroplane.wings if w.name == wing_name), None)
    if not wing:
        raise NotFoundError(
            message="Wing not found",
            details={"wing_name": wing_name, "aeroplane_id": str(aeroplane.uuid)}
        )
    return wing


def get_task_status(aeroplane_id: str) -> Optional[Dict[str, Any]]:
    """Get the current status of a task."""
    with tasks_lock:
        return tasks.get(aeroplane_id)


def check_task_available(aeroplane_id: str) -> None:
    """
    Check if a new task can be started for this aeroplane.
    
    Raises:
        ConflictError: If another task is already running.
    """
    task = get_task_status(aeroplane_id)
    if task is not None:
        if task.get('future') and (task['future'].running() or task['status'] == 'PENDING'):
            raise ConflictError(
                message="Another task is already running",
                details={"aeroplane_id": aeroplane_id, "status": task['status']}
            )
        else:
            # Remove completed task
            with tasks_lock:
                del tasks[aeroplane_id]


def register_pending_task(aeroplane_id: str) -> None:
    """Register a new pending task."""
    with tasks_lock:
        tasks[aeroplane_id] = {'status': 'PENDING'}


def map_exporter_type(exporter_url_type: ExporterUrlType) -> str:
    """
    Map exporter URL type to exporter class name.
    
    Raises:
        ValidationError: If the exporter type is not supported.
    """
    mapping = {
        ExporterUrlType.STL: 'ExportToStlCreator',
        ExporterUrlType.STEP: 'ExportToStepCreator',
        ExporterUrlType.IGES: 'ExportToIgesCreator',
        ExporterUrlType.THREEMF: 'ExportTo3MFCreator',
    }
    exporter_class = mapping.get(exporter_url_type)
    if not exporter_class:
        raise ValidationError(
            message="Unsupported exporter type",
            details={"exporter_type": str(exporter_url_type)}
        )
    return exporter_class


def build_wing_blueprint(
    wing_name: str,
    creator_url_type: CreatorUrlType,
    exporter_class: str,
    leading_edge_offset_factor: float = 0.1,
    trailing_edge_offset_factor: float = 0.15,
) -> Dict[str, Any]:
    """Build the blueprint dict for wing construction."""
    blueprint = {
        _TYPE_KEY: 'ConstructionRootNode',
        'creator_id': 'eHawk-wing.root.root',
        'loglevel': 50,
        'successors': {}
    }
    
    # Add wing node
    wing_node = {
        _TYPE_KEY: 'ConstructionStepNode',
        'creator': {
            _TYPE_KEY: "",
            'creator_id': wing_name,
            'loglevel': 10,
            'offset': 0,
            'wing_index': wing_name,
            'wing_side': 'BOTH'
        },
        'creator_id': wing_name,
        'loglevel': 50,
        'successors': {}
    }
    
    if creator_url_type == CreatorUrlType.WING_LOFT:
        wing_node['creator'][_TYPE_KEY] = 'WingLoftCreator'
    else:  # VASE_MODE_WING
        wing_node['creator'][_TYPE_KEY] = 'VaseModeWingCreator'
        wing_node['creator']['leading_edge_offset_factor'] = leading_edge_offset_factor
        wing_node['creator']['trailing_edge_offset_factor'] = trailing_edge_offset_factor
    
    blueprint['successors'][wing_name] = wing_node
    
    # Add exporter node
    blueprint['successors']['output-wing'] = {
        _TYPE_KEY: 'ConstructionStepNode',
        'creator': {
            _TYPE_KEY: exporter_class,
            'angular_tolerance': 0.1,
            'creator_id': 'output-wing',
            'file_path': './tmp/exports',
            'loglevel': 20,
            'tolerance': 0.1
        },
        'creator_id': 'output-wing',
        'loglevel': 50,
        'successors': {}
    }
    
    return blueprint


def _run_construction_worker(
    aeroplane_id: str,
    blueprint_dict: Dict[str, Any],
    wing_schemas_pickle: bytes,
    wing_scale: float,
    fuselages_pickle: Optional[bytes],
    servo_settings_dumps: Dict[int, Dict[str, Any]],
    printer_settings_pickle: Optional[bytes],
) -> Dict[str, Any]:
    """Top-level worker function executed inside a ProcessPoolExecutor.

    This function MUST NOT touch the parent-process ``tasks`` dict — it
    cannot see it. Instead it returns a result dict which the parent
    stores via a ``future.add_done_callback``.

    All arguments are picklable. The parent is responsible for building
    the real ``ServoInformation`` / ``Printer3dSettings`` / ``WingConfiguration``
    objects and pickling them, so the worker only has to deserialize and
    hand them to the ``GeneralJSONDecoder``.
    """
    # Reconfigure logging in the worker — spawn does not inherit the
    # parent's logging setup.
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] [worker] %(message)s",
    )
    _logger = _logging.getLogger(__name__)

    try:
        _logger.info("Starting aeroplane construction: %s", aeroplane_id)

        # Re-hydrate all the pickled dependency objects. Wings cross the
        # process boundary as AsbWingSchema (Pydantic, picklable) and
        # are rebuilt into WingConfiguration here in the worker because
        # WingConfiguration holds cq.Vector / OCCT gp_Vec instances that
        # cannot be pickled.
        wing_schemas: Dict[str, Any] = pickle.loads(wing_schemas_pickle)
        wing_config: Dict[str, WingConfiguration] = {
            name: asb_wing_schema_to_wing_config(schema, scale=wing_scale)
            for name, schema in wing_schemas.items()
        }
        fuselages: Optional[Dict[str, FuselageSchema]] = (
            pickle.loads(fuselages_pickle) if fuselages_pickle else None
        )
        printer_settings = (
            pickle.loads(printer_settings_pickle) if printer_settings_pickle else None
        )

        # Re-hydrate servo_information in the worker. The cad_designer
        # ServoInformation class internally holds cq.Vector / gp_Vec
        # instances that are not picklable, so we cannot build it in
        # the parent and ship it over. Instead we ship the raw dict
        # (from ServoSettings.model_dump()) and reconstruct both the
        # Servo pydantic schema and the ServoInformation here.
        from app.schemas.Servo import Servo as _ServoSchema
        servo_information: Dict[int, ServoInformation] = {}
        for key, value in (servo_settings_dumps or {}).items():
            servo_dict = value.get("servo")
            if isinstance(servo_dict, dict):
                servo_schema: Any = _ServoSchema(**servo_dict)
            else:
                servo_schema = servo_dict  # None or already int
            servo_information[int(key)] = ServoInformation(
                height=value.get("height", 0),
                width=value.get("width", 0),
                length=value.get("length", 0),
                lever_length=value.get("lever_length", 0),
                rot_x=value.get("rot_x", 0.0),
                rot_y=value.get("rot_y", 0.0),
                rot_z=value.get("rot_z", 0.0),
                trans_x=value.get("trans_x", 0.0),
                trans_y=value.get("trans_y", 0.0),
                trans_z=value.get("trans_z", 0.0),
                servo=create_servo(servo_schema),
            )

        # Parse blueprint into a live ConstructionStepNode tree, with
        # wing_config / servo_information / fuselages / printer_settings
        # passed through the decoder kwargs (same pattern as
        # test/Construction_eHawk_wing.py).
        decoder_kwargs: Dict[str, Any] = {
            "wing_config": wing_config,
            "fuselage_config": fuselages,
            "servo_information": servo_information,
        }
        if printer_settings is not None:
            decoder_kwargs["printer_settings"] = printer_settings

        blue_print: ConstructionStepNode = json.loads(
            json.dumps(blueprint_dict),
            cls=GeneralJSONDecoder,
            **decoder_kwargs,
        )

        # Execute construction. This is the call that used to hang in
        # a ThreadPoolExecutor worker because of OCCT thread-unsafety.
        blue_print.create_shape()
        _logger.info("Finished aeroplane construction: %s", aeroplane_id)

        # Create the result zip file
        zipfile_path = f"./tmp/{aeroplane_id}.zip"
        exports_dir = "./tmp/exports"

        with ZipFile(zipfile_path, "w") as zipf:
            _logger.info("Zipping files for: %s", aeroplane_id)
            for file in os.scandir(exports_dir):
                zipf.write(file.path)

        for file in os.scandir(exports_dir):
            os.unlink(file.path)

        return {
            "status": "SUCCESS",
            "result": {"zipfile": zipfile_path},
        }

    except Exception as err:
        _logger.error("Construction failed for %s: %s", aeroplane_id, err, exc_info=True)
        return {
            "status": "FAILURE",
            "error": f"{type(err).__name__}: {err}",
            "traceback": traceback.format_exc(),
        }


def _convert_wing_to_pickle(wing: WingModel, wing_name: str, aeroplane_id_str: str) -> bytes:
    """Convert WingModel to pickled AsbWingSchema dict.

    Must run in the parent process because it needs live SQLAlchemy relationships.
    """
    try:
        wing_schemas: Dict[str, Any] = {
            wing_name: wing_model_to_asb_wing_schema(wing),
        }
    except Exception as exc:
        logger.error("Failed to convert wing to schema: %s", type(exc).__name__)
        raise InternalError(
            message=f"Wing data conversion failed: {type(exc).__name__}",
        )
    try:
        return pickle.dumps(wing_schemas)
    except Exception as exc:
        logger.error(
            "Failed to pickle wing schema for %s: %s; keys=%s",
            aeroplane_id_str, exc,
            list(wing_schemas[wing_name].model_dump().keys()) if wing_schemas.get(wing_name) else [],
        )
        raise InternalError(
            message=f"Failed to prepare wing data for '{wing_name}': {exc}",
        )


def _extract_aeroplane_settings(
    aeroplane_settings: Optional[AeroplaneSettings],
) -> tuple[Dict[int, Dict[str, Any]], Optional[bytes]]:
    """Extract picklable servo settings and printer settings from AeroplaneSettings."""
    servo_settings_dumps: Dict[int, Dict[str, Any]] = {}
    printer_settings_obj = None

    if aeroplane_settings is not None:
        for key, value in (aeroplane_settings.servo_information or {}).items():
            if hasattr(value, "model_dump"):
                servo_settings_dumps[int(key)] = value.model_dump()
            else:
                servo_settings_dumps[int(key)] = dict(value)
        printer_settings_obj = aeroplane_settings.printer_settings

    printer_pickle = pickle.dumps(printer_settings_obj) if printer_settings_obj is not None else None
    return servo_settings_dumps, printer_pickle


def _make_task_done_callback(aeroplane_id_str: str):
    """Create the parent-side done callback for a worker future."""
    def _on_task_done(fut: "Future[Dict[str, Any]]") -> None:
        try:
            result = fut.result()
        except Exception as exc:
            logger.error(
                "Worker process crashed for %s: %s", aeroplane_id_str, exc, exc_info=True,
            )
            with tasks_lock:
                if aeroplane_id_str in tasks:
                    tasks[aeroplane_id_str]["status"] = "FAILURE"
                    tasks[aeroplane_id_str]["error"] = (
                        f"Worker crashed: {type(exc).__name__}: {exc}"
                    )
            return

        with tasks_lock:
            if aeroplane_id_str in tasks:
                task = tasks[aeroplane_id_str]
                task["status"] = result.get("status", "FAILURE")
                if "result" in result:
                    task["result"] = result["result"]
                if "error" in result:
                    task["error"] = result["error"]
                if "traceback" in result:
                    task["traceback"] = result["traceback"]
    return _on_task_done


def start_wing_export_task(
    aeroplane_id: str,
    wing: WingModel,
    wing_name: str,
    creator_url_type: CreatorUrlType,
    exporter_url_type: ExporterUrlType,
    leading_edge_offset_factor: float,
    trailing_edge_offset_factor: float,
    aeroplane_settings: Optional[AeroplaneSettings],
) -> None:
    """Start a background CAD task in a dedicated worker process.

    Raises:
        ConflictError: If another task is already running for this aeroplane.
        ValidationError: If the exporter type is not supported.
    """
    aeroplane_id_str = str(aeroplane_id)
    check_task_available(aeroplane_id_str)
    register_pending_task(aeroplane_id_str)

    blueprint = build_wing_blueprint(
        wing_name=wing_name,
        creator_url_type=creator_url_type,
        exporter_class=map_exporter_type(exporter_url_type),
        leading_edge_offset_factor=leading_edge_offset_factor,
        trailing_edge_offset_factor=trailing_edge_offset_factor,
    )

    wing_schemas_pickle = _convert_wing_to_pickle(wing, wing_name, aeroplane_id_str)
    servo_settings_dumps, printer_settings_pickle = _extract_aeroplane_settings(aeroplane_settings)

    future = _get_executor().submit(
        _run_construction_worker,
        aeroplane_id_str,
        blueprint,
        wing_schemas_pickle,
        1000.0,  # wing_scale: metres → millimetres
        None,    # fuselages — not yet routed through the REST path
        servo_settings_dumps,
        printer_settings_pickle,
    )
    future.add_done_callback(_make_task_done_callback(aeroplane_id_str))

    with tasks_lock:
        tasks[aeroplane_id_str]["future"] = future


def get_task_result(aeroplane_id: str) -> Dict[str, Any]:
    """
    Get the current task status and result.
    
    Raises:
        NotFoundError: If no task exists for this aeroplane.
    """
    with tasks_lock:
        task = tasks.get(aeroplane_id)
    
    if not task:
        raise NotFoundError(
            message="Task not found",
            details={"aeroplane_id": aeroplane_id}
        )
    
    # Update status if running
    if task.get('future') and task['future'].running():
        task['status'] = 'RUNNING'
    
    return {
        'status': task['status'],
        'result': task.get('result'),
        'error': task.get('error'),
    }


def get_export_file_path(aeroplane_id: str) -> str:
    """
    Get the path to the completed export file.
    
    Raises:
        NotFoundError: If no task or file exists.
        ValidationError: If the task is not completed.
    """
    task = get_task_status(aeroplane_id)
    
    if not task:
        raise NotFoundError(
            message="Task not found",
            details={"aeroplane_id": aeroplane_id}
        )
    
    if task['status'] != 'SUCCESS':
        raise ValidationError(
            message="Task not completed yet or failed",
            details={"aeroplane_id": aeroplane_id, "status": task['status']}
        )
    
    file_info = task.get('result')
    if not file_info or 'zipfile' not in file_info:
        raise InternalError(
            message="File not available",
            details={"aeroplane_id": aeroplane_id}
        )
    
    file_path = file_info['zipfile']
    if not os.path.exists(file_path):
        raise NotFoundError(
            message="File not found",
            details={"aeroplane_id": aeroplane_id, "file_path": file_path}
        )
    
    return file_path
