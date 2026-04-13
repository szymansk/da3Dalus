import http
import logging
import os
import shutil
from pathlib import Path as FilePath

from typing import Optional

from fastapi import APIRouter, Query, Body, Path, Depends, Request, HTTPException
from fastapi import status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.schemas.AeroplaneRequest import CreatorUrlType, ExporterUrlType, AeroplaneSettings
from app.schemas.api_responses import (
    CadTaskAcceptedResponse,
    CadTaskStatusResponse,
    ZipAssetResponse,
)
from app.services import cad_service
from app.services import tessellation_cache_service
from app.services import tessellation_service
from app.settings import Settings, get_settings

router = APIRouter()

AeroPlaneID = UUID4

logger = logging.getLogger(__name__)


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _ensure_file_under_tmp(file_path: str, aeroplane_id: str) -> FilePath:
    source_path = FilePath(file_path)
    if not source_path.is_absolute():
        source_path = (FilePath.cwd() / source_path).resolve()
    else:
        source_path = source_path.resolve()

    tmp_root = (FilePath.cwd() / "tmp").resolve()
    tmp_root.mkdir(parents=True, exist_ok=True)

    if tmp_root in source_path.parents:
        return source_path

    target_dir = tmp_root / str(aeroplane_id) / "zip"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / source_path.name).resolve()
    shutil.copy2(source_path, target_path)
    return target_path


@router.post(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/tessellation",
    response_model=CadTaskAcceptedResponse,
    status_code=http.HTTPStatus.ACCEPTED,
    tags=["cad"],
    operation_id="start_wing_tessellation",
)
async def start_wing_tessellation(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    wing_name: str = Path(..., description="The name of the wing"),
    db: Session = Depends(get_db),
) -> CadTaskAcceptedResponse:
    """Start async tessellation of a wing for 3D viewer rendering.

    The tessellation result can be retrieved via GET /status once complete.
    The result is in three-cad-viewer JSON format (instances + shapes).
    """
    try:
        import pickle
        aeroplane_id_str = str(aeroplane_id)
        aeroplane = cad_service.get_aeroplane_with_wings(db, aeroplane_id)
        wing = cad_service.get_wing_from_aeroplane(aeroplane, wing_name)

        from app.converters.model_schema_converters import wingModelToAsbWingSchema
        wing_schema = wingModelToAsbWingSchema(wing)
        wing_schema_pickle = pickle.dumps(wing_schema)

        tessellation_service.start_tessellation_task(
            aeroplane_id=aeroplane_id_str,
            wing_name=wing_name,
            wing_schema_pickle=wing_schema_pickle,
        )

        return CadTaskAcceptedResponse(
            aeroplane_id=aeroplane_id_str,
            href=f"/aeroplanes/{aeroplane_id_str}",
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/tessellation",
    tags=["cad"],
    operation_id="get_aeroplane_tessellation",
)
async def get_aeroplane_tessellation(
    aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
):
    """Assemble all cached wing/fuselage tessellations into a single three-cad-viewer scene.

    Returns a combined scene with all cached component tessellations.
    The ``is_stale`` flag indicates whether any component's cache is
    outdated and a re-tessellation is pending.
    """
    try:
        aeroplane = cad_service.get_aeroplane_with_wings(db, aeroplane_id)

        cached_entries = tessellation_cache_service.get_all_cached(db, aeroplane.id)
        if not cached_entries:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cached tessellations for aeroplane {aeroplane_id}",
            )

        # Collect parts and instances from each cached entry.
        # Instance refs ({ref: N}) are local to each component's instance
        # array, so we offset them when merging into the combined array.
        parts = []
        combined_instances = []
        total_count = 0
        bb_min = [float("inf")] * 3
        bb_max = [float("-inf")] * 3

        def _offset_refs(node, offset):
            """Recursively offset {ref: N} values in shapes by offset."""
            if isinstance(node, dict):
                if "ref" in node and isinstance(node["ref"], (int, float)):
                    node["ref"] = int(node["ref"]) + offset
                for v in node.values():
                    _offset_refs(v, offset)
            elif isinstance(node, list):
                for item in node:
                    _offset_refs(item, offset)

        for entry in cached_entries:
            tess = entry.tessellation_json
            data = tess.get("data", {})

            instances = data.get("instances", [])
            instance_offset = len(combined_instances)

            # Accumulate shapes with color per component type
            shapes = data.get("shapes")
            if shapes:
                import copy
                shapes_copy = copy.deepcopy(shapes)
                shapes_copy["color"] = "#FF8400" if entry.component_type == "wing" else "#888888"
                if instance_offset > 0:
                    _offset_refs(shapes_copy, instance_offset)
                parts.append(shapes_copy)

            # Accumulate instances
            combined_instances.extend(instances)

            # Accumulate count
            total_count += tess.get("count", 0)

            # Expand bounding box from the shapes bb
            if shapes and "bb" in shapes:
                entry_bb = shapes["bb"]
                if "min" in entry_bb and "max" in entry_bb:
                    for i in range(3):
                        bb_min[i] = min(bb_min[i], entry_bb["min"][i])
                        bb_max[i] = max(bb_max[i], entry_bb["max"][i])

        # Build combined bounding box (fall back to zeroes if no valid bb found)
        if any(v == float("inf") for v in bb_min):
            combined_bb = {"min": [0, 0, 0], "max": [0, 0, 0]}
        else:
            combined_bb = {"min": bb_min, "max": bb_max}

        return {
            "data": {
                "shapes": {
                    "version": 3,
                    "name": aeroplane.name,
                    "id": f"/{aeroplane.name}",
                    "parts": parts,
                    "loc": [[0, 0, 0], [0, 0, 0, 1]],
                    "bb": combined_bb,
                },
                "instances": combined_instances,
            },
            "type": "data",
            "config": {"theme": "dark"},
            "count": total_count,
            "is_stale": any(e.is_stale for e in cached_entries),
        }
    except HTTPException:
        raise
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}",
         response_model=CadTaskAcceptedResponse,
         status_code=http.HTTPStatus.ACCEPTED,
         operation_id="create_wing_loft_export")
async def create_wing_loft(aeroplane_id: AeroPlaneID = Path(..., description="The ID of the aeroplane"),
                           wing_name: str = Path(..., description="The ID of the wing"),
                           creator_url_type: CreatorUrlType = CreatorUrlType.WING_LOFT,
                           exporter_url_type: ExporterUrlType = ExporterUrlType.STL,
                           leading_edge_offset_factor: float = Query(0.1, description="only need for vase mode wing"),
                           trailing_edge_offset_factor: float = Query(0.15, description="only need for vase mode wing"),
                           aeroplane_settings: Optional[AeroplaneSettings] =
                           Body(None,
                                description="General settings for the construction, not needed for a simple loft"),
                           db: Session = Depends(get_db)) -> CadTaskAcceptedResponse:
    """Create a wing loft export. Business logic delegated to cad_service."""
    try:
        aeroplane_id_str = str(aeroplane_id)

        # Load aeroplane and wing via service
        aeroplane = cad_service.get_aeroplane_with_wings(db, aeroplane_id)
        wing = cad_service.get_wing_from_aeroplane(aeroplane, wing_name)

        # Start export task
        cad_service.start_wing_export_task(
            aeroplane_id=aeroplane_id_str,
            wing=wing,
            wing_name=wing_name,
            creator_url_type=creator_url_type,
            exporter_url_type=exporter_url_type,
            leading_edge_offset_factor=leading_edge_offset_factor,
            trailing_edge_offset_factor=trailing_edge_offset_factor,
            aeroplane_settings=aeroplane_settings,
        )

        return CadTaskAcceptedResponse(
            aeroplane_id=aeroplane_id_str,
            href=f"/aeroplanes/{aeroplane_id_str}",
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.get("/aeroplanes/{aeroplane_id}/status",
         response_model=CadTaskStatusResponse,
         response_model_exclude_none=True,
         operation_id="get_aeroplane_task_status")
async def get_aeroplane_task_status(
    aeroplane_id: str,
    task_type: Optional[str] = Query(None, description="Task type: 'tessellation' or None for CAD export"),
    wing_name: Optional[str] = Query(None, description="Wing name (required for tessellation tasks)"),
) -> CadTaskStatusResponse:
    """Get the status of an aeroplane export or tessellation task."""
    try:
        if task_type == "tessellation" and wing_name:
            task_key = f"{aeroplane_id}:tessellation:{wing_name}"
        elif task_type:
            task_key = f"{aeroplane_id}:{task_type}"
        else:
            task_key = aeroplane_id
        logger.info(f"Getting task status for: {task_key}")
        task_result = cad_service.get_task_result(task_key)

        message: str | None = None
        result: dict | None = None

        if task_result['status'] == 'PENDING':
            message = "Task is pending."
        elif task_result['status'] == 'FAILURE':
            message = task_result.get('error', 'An error occurred')
        elif task_result['status'] == 'SUCCESS':
            result = task_result.get('result')
        else:
            message = "Task is processing."

        return CadTaskStatusResponse(
            aeroplane_id=aeroplane_id,
            href=f"/aeroplanes/{aeroplane_id}",
            status=task_result['status'],
            message=message,
            result=result,
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip",
         response_model=ZipAssetResponse,
         operation_id="download_export_zip")
async def download_aeroplane_zip(
    aeroplane_id: str,
    request: Request = None,
    settings: Settings = Depends(get_settings),
) -> ZipAssetResponse:
    """Return the static URL for the completed export zip file."""
    try:
        logger.info(f"Download request for aeroplane_id: {aeroplane_id}")

        file_path = cad_service.get_export_file_path(aeroplane_id)
        static_file_path = _ensure_file_under_tmp(file_path, aeroplane_id)
        tmp_root = (FilePath.cwd() / "tmp").resolve()
        static_relative = static_file_path.relative_to(tmp_root).as_posix()

        base_url = str(request.base_url).rstrip("/") if request else settings.base_url.rstrip("/")
        base_url = base_url if base_url != "apiserver" else settings.base_url.rstrip("/")

        return ZipAssetResponse(
            url=f"{base_url}/static/{static_relative}",
            filename=os.path.basename(static_file_path),
            mime_type="application/zip",
        )
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Unexpected error: {exc}") from exc
