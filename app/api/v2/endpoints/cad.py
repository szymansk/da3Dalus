import http
import logging
import os

from typing import Optional

from fastapi import APIRouter, Query, Body, Path, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.AeroplaneRequest import CreatorUrlType, ExporterUrlType, AeroplaneSettings
from app.services import cad_service

router = APIRouter()

AeroPlaneID = UUID4

logger = logging.getLogger(__name__)


@router.post("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}",
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
                           db: Session = Depends(get_db)):
    """Create a wing loft export. Business logic delegated to cad_service."""
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
    
    return JSONResponse(
        status_code=http.HTTPStatus.ACCEPTED,
        content={"aeroplane_id": aeroplane_id_str, "href": f"/aeroplanes/{aeroplane_id_str}"}
    )


@router.get("/aeroplanes/{aeroplane_id}/status",
         operation_id="get_aeroplane_task_status")
async def get_aeroplane_task_status(aeroplane_id: str):
    """Get the status of an aeroplane export task."""
    logger.info(f"Getting task status for aeroplane_id: {aeroplane_id}")
    
    task_result = cad_service.get_task_result(aeroplane_id)
    
    content = {
        "aeroplane_id": aeroplane_id,
        "href": f"/aeroplanes/{aeroplane_id}",
        "status": task_result['status'],
    }
    
    if task_result['status'] == 'PENDING':
        content["message"] = "Task is pending."
    elif task_result['status'] == 'FAILURE':
        content["message"] = task_result.get('error', 'An error occurred')
    elif task_result['status'] == 'SUCCESS':
        content["result"] = task_result.get('result')
    else:
        content["message"] = "Task is processing."
    
    return JSONResponse(status_code=http.HTTPStatus.OK, content=content)


@router.get("/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip",
         operation_id="download_export_zip")
async def download_aeroplane_zip(aeroplane_id: str):
    """Download the completed export zip file."""
    logger.info(f"Download request for aeroplane_id: {aeroplane_id}")
    
    file_path = cad_service.get_export_file_path(aeroplane_id)
    
    return FileResponse(
        path=file_path,
        media_type='application/zip',
        filename=os.path.basename(file_path)
    )
