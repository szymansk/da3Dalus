"""
CAD Service - Business logic for CAD export operations.

This module contains the core logic for CAD model creation and export,
separated from HTTP concerns for better testability and reusability.
"""

import json
import logging
import os
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional, Union
from zipfile import ZipFile

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.converters.model_schema_converters import wingModelToWingConfig
from app.core.exceptions import NotFoundError, ValidationError, ConflictError, InternalError
from app.models import AeroplaneModel, WingModel, WingXSecModel
from app.models.aeroplanemodel import FuselageModel
from app.schemas import FuselageSchema
from app.schemas.AeroplaneRequest import CreatorUrlType, ExporterUrlType, AeroplaneSettings
from app.services.create_wing_configuration import create_servo
from cad_designer.airplane import ConstructionStepNode, GeneralJSONDecoder
from cad_designer.airplane.aircraft_topology.components import ServoInformation
from cad_designer.airplane.aircraft_topology.wing import WingConfiguration


logger = logging.getLogger(__name__)

# In-Memory task management
tasks: Dict[str, Dict[str, Any]] = {}
tasks_lock = Lock()
executor = ThreadPoolExecutor(max_workers=4)


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
                          .joinedload(WingXSecModel.control_surface))
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
        '$TYPE': 'ConstructionRootNode',
        'creator_id': 'eHawk-wing.root.root',
        'loglevel': 50,
        'successors': {}
    }
    
    # Add wing node
    wing_node = {
        '$TYPE': 'ConstructionStepNode',
        'creator': {
            '$TYPE': "",
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
        wing_node['creator']['$TYPE'] = 'WingLoftCreator'
    else:  # VASE_MODE_WING
        wing_node['creator']['$TYPE'] = 'VaseModeWingCreator'
        wing_node['creator']['leading_edge_offset_factor'] = leading_edge_offset_factor
        wing_node['creator']['trailing_edge_offset_factor'] = trailing_edge_offset_factor
    
    blueprint['successors'][wing_name] = wing_node
    
    # Add exporter node
    blueprint['successors']['output-wing'] = {
        '$TYPE': 'ConstructionStepNode',
        'creator': {
            '$TYPE': exporter_class,
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


def execute_aeroplane_construction(
    aeroplane_id: str,
    blueprint: Union[Dict, str],
    wings: Optional[Dict[str, WingModel]] = None,
    fuselages: Optional[Dict[str, FuselageSchema]] = None,
    request_settings: Optional[AeroplaneSettings] = None,
) -> None:
    """
    Execute the CAD construction task in background.
    
    This function is run in a thread pool and updates task status.
    """
    try:
        logger.info(f"Starting aeroplane construction: {aeroplane_id}")
        
        settings = {}
        if request_settings is not None:
            settings = request_settings.__dict__.copy()
            settings['servo_information'] = {
                key: ServoInformation(
                    height=value.height,
                    width=value.width,
                    length=value.length,
                    lever_length=value.lever_length,
                    rot_x=value.rot_x,
                    rot_y=value.rot_y,
                    rot_z=value.rot_z,
                    trans_x=value.trans_x,
                    trans_y=value.trans_y,
                    trans_z=value.trans_z,
                    servo=create_servo(value.servo)
                ) for key, value in request_settings.servo_information.items()
            }
        
        wing_config: Dict[str, WingConfiguration] = {
            k: wingModelToWingConfig(w) for k, w in (wings or {}).items()
        }
        
        # Parse blueprint
        if isinstance(blueprint, dict):
            try:
                blue_print: ConstructionStepNode = json.loads(
                    json.dumps(blueprint),
                    cls=GeneralJSONDecoder,
                    wing_config=wing_config,
                    fuselage_config=fuselages,
                    **settings
                )
            except (TypeError, ValueError) as e:
                raise ValueError(f"Error processing the JSON object: {e}")
        elif isinstance(blueprint, str) and os.path.isfile(blueprint):
            try:
                with open(blueprint, "r") as json_file:
                    blue_print: ConstructionStepNode = json.load(
                        json_file,
                        cls=GeneralJSONDecoder,
                        wing_config=wing_config,
                        fuselage_config=fuselages,
                        **settings
                    )
            except FileNotFoundError:
                raise FileNotFoundError(f"Blueprint file not found: {blueprint}")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Error loading the blueprint file: {e}")
            except OSError as e:
                raise OSError(f"Error opening the blueprint file: {e}")
        else:
            raise TypeError("Blueprint must be either a JSON object (dict) or a valid file path.")
        
        # Execute construction
        blue_print.create_shape()
        
        logger.info(f"Finished aeroplane construction: {aeroplane_id}")
        
        # Create zip file
        zipfile_path = f"./tmp/{aeroplane_id}.zip"
        exports_dir = "./tmp/exports"
        
        with ZipFile(zipfile_path, 'w') as zipf:
            logger.info(f"Zipping files for: {aeroplane_id}")
            for file in os.scandir(exports_dir):
                zipf.write(file.path)
        
        # Cleanup export files
        for file in os.scandir(exports_dir):
            os.unlink(file.path)
        
        # Update task status
        with tasks_lock:
            tasks[aeroplane_id]['status'] = 'SUCCESS'
            tasks[aeroplane_id]['result'] = {"zipfile": zipfile_path}
            
    except Exception as err:
        logger.error(f"Construction failed for {aeroplane_id}: {err}")
        with tasks_lock:
            tasks[aeroplane_id]['status'] = 'FAILURE'
            tasks[aeroplane_id]['error'] = str(err)


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
    """
    Start a background task for wing export.
    
    Raises:
        ConflictError: If another task is already running.
        ValidationError: If the exporter type is not supported.
    """
    aeroplane_id_str = str(aeroplane_id)
    
    # Check if task slot is available
    check_task_available(aeroplane_id_str)
    
    # Register pending task
    register_pending_task(aeroplane_id_str)
    
    # Get exporter class
    exporter_class = map_exporter_type(exporter_url_type)
    
    # Build blueprint
    blueprint = build_wing_blueprint(
        wing_name=wing_name,
        creator_url_type=creator_url_type,
        exporter_class=exporter_class,
        leading_edge_offset_factor=leading_edge_offset_factor,
        trailing_edge_offset_factor=trailing_edge_offset_factor,
    )
    
    # Submit task
    future = executor.submit(
        execute_aeroplane_construction,
        aeroplane_id_str,
        blueprint,
        {wing_name: wing},
        None,  # fuselages
        aeroplane_settings,
    )
    
    with tasks_lock:
        tasks[aeroplane_id_str]['future'] = future


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
