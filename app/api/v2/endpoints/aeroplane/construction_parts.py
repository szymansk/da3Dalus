"""Endpoints for the per-aeroplane Construction-Parts domain (gh#57-g4h + gh#57-9uk)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Path, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.construction_part import (
    ConstructionPartList,
    ConstructionPartRead,
    ConstructionPartUpdate,
)
from app.services import construction_part_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/aeroplanes/{aeroplane_id}/construction-parts",
    tags=["construction-parts"],
)


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
        # File-too-large is signalled via ConflictError with a marker in details
        # so the upload endpoint can map it to HTTP 413 rather than 409.
        if exc.details and exc.details.get("reason") == "file_too_large":
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=exc.message,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ConstructionPartList,
    operation_id="list_construction_parts",
)
async def list_construction_parts(
    aeroplane_id: str = Path(...),
    db: Session = Depends(get_db),
) -> ConstructionPartList:
    """List all construction parts owned by the given aeroplane."""
    return _call(svc.list_parts, db, aeroplane_id)


@router.get(
    "/{part_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConstructionPartRead,
    operation_id="get_construction_part",
)
async def get_construction_part(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ConstructionPartRead:
    """Fetch a single construction part scoped to the given aeroplane."""
    return _call(svc.get_part, db, aeroplane_id, part_id)


@router.put(
    "/{part_id}/lock",
    status_code=status.HTTP_200_OK,
    response_model=ConstructionPartRead,
    operation_id="lock_construction_part",
)
async def lock_construction_part(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ConstructionPartRead:
    """Mark the part as locked. Idempotent."""
    return _call(svc.lock_part, db, aeroplane_id, part_id)


@router.put(
    "/{part_id}/unlock",
    status_code=status.HTTP_200_OK,
    response_model=ConstructionPartRead,
    operation_id="unlock_construction_part",
)
async def unlock_construction_part(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ConstructionPartRead:
    """Mark the part as unlocked. Idempotent."""
    return _call(svc.unlock_part, db, aeroplane_id, part_id)


# ── D2 (gh#57-9uk): file upload / download / metadata CRUD ──────────────────


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ConstructionPartRead,
    operation_id="upload_construction_part",
)
async def upload_construction_part(
    aeroplane_id: str = Path(...),
    file: UploadFile = File(..., description="STEP (.step/.stp) or STL (.stl) file"),
    name: str = Form(..., min_length=1, description="Display name"),
    material_component_id: Optional[int] = Form(None, description="FK to components (material)"),
    thumbnail_url: Optional[str] = Form(None, description="Optional preview image URL"),
    db: Session = Depends(get_db),
) -> ConstructionPartRead:
    """Upload a CAD file and create a new construction-part for this aeroplane.

    The file is stored under ``tmp/construction_parts/{aeroplane_id}/``.
    Geometry (volume / area / bounding-box) is extracted at upload time via
    CadQuery; on platforms without CadQuery the row is still created with
    NULL geometry fields.
    """
    content = await file.read()
    return _call(
        svc.create_part,
        db,
        aeroplane_id,
        filename=file.filename,
        content=content,
        name=name,
        material_component_id=material_component_id,
        thumbnail_url=thumbnail_url,
    )


@router.get(
    "/{part_id}/file",
    status_code=status.HTTP_200_OK,
    operation_id="download_construction_part_file",
)
async def download_construction_part_file(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    format: str = Query("stl", description="Output format: 'step' or 'stl'"),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Download the construction-part file in the requested format.

    If the source is STEP and the requested format is STL, the STL is
    regenerated on the fly via CadQuery. Requesting STEP for an STL source
    returns 422 (the conversion is not lossless).
    """
    path, mime = _call(svc.get_part_file, db, aeroplane_id, part_id, format)
    return FileResponse(
        path=str(path),
        media_type=mime,
        filename=f"construction_part_{part_id}.{format}",
    )


@router.put(
    "/{part_id}",
    status_code=status.HTTP_200_OK,
    response_model=ConstructionPartRead,
    operation_id="update_construction_part",
)
async def update_construction_part(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    body: ConstructionPartUpdate = Body(...),
    db: Session = Depends(get_db),
) -> ConstructionPartRead:
    """Update name / material / thumbnail. File and geometry stay untouched."""
    return _call(svc.update_part, db, aeroplane_id, part_id, body)


@router.delete(
    "/{part_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_construction_part",
)
async def delete_construction_part(
    aeroplane_id: str = Path(...),
    part_id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    """Delete a part and remove its file. Returns 409 if the part is locked."""
    _call(svc.delete_part, db, aeroplane_id, part_id)
