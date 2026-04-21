import logging
import shutil
from pathlib import Path as FilePath
from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, UploadFile, File, status
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
from app.schemas.component import (
    ComponentList,
    ComponentRead,
    ComponentTypesResponse,
    ComponentWrite,
)
from app.services import component_service as svc
from app.services import component_type_service as type_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/components", tags=["components"])


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="list_components"
)
async def list_components(
    db: Annotated[Session, Depends(get_db)],
    component_type: Annotated[Optional[str], Query(description="Filter by component type")] = None,
    q: Annotated[Optional[str], Query(description="Search by name")] = None,
) -> ComponentList:
    """List all components, optionally filtered by type or name search."""
    return _call(svc.list_components, db, component_type, q)


@router.get(
    "/types",
    status_code=status.HTTP_200_OK,
    operation_id="list_component_types"
)
async def list_component_types(
    db: Annotated[Session, Depends(get_db)],
) -> ComponentTypesResponse:
    """List the *names* of all registered component types.

    Backward-compatible shape. Prefer GET /component-types for full metadata
    (schema, reference_count, etc.).
    """
    return ComponentTypesResponse(types=type_svc.list_type_names(db))


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_component"
)
async def create_component(
    body: Annotated[ComponentWrite, Body(..., description="Component data")],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentRead:
    """Create a new component in the library."""
    return _call(svc.create_component, db, body)


@router.get(
    "/{component_id}",
    status_code=status.HTTP_200_OK,
    operation_id="get_component"
)
async def get_component(
    component_id: Annotated[int, Path(..., description="The component ID")],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentRead:
    """Get a single component by ID."""
    return _call(svc.get_component, db, component_id)


@router.put(
    "/{component_id}",
    status_code=status.HTTP_200_OK,
    operation_id="update_component"
)
async def update_component(
    component_id: Annotated[int, Path(..., description="The component ID")],
    body: Annotated[ComponentWrite, Body(..., description="Component data")],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentRead:
    """Update an existing component."""
    return _call(svc.update_component, db, component_id, body)


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_component",
)
async def delete_component(
    component_id: Annotated[int, Path(..., description="The component ID")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a component from the library."""
    _call(svc.delete_component, db, component_id)


# ── 3D Model Upload / Download ──────────────────────────────────

MODELS_DIR = FilePath("tmp") / "component_models"


@router.post(
    "/{component_id}/model",
    status_code=status.HTTP_200_OK,
    operation_id="upload_component_model"
)
async def upload_component_model(
    component_id: Annotated[int, Path(..., description="The component ID")],
    file: Annotated[UploadFile, File(..., description="STEP or STL file")],
    db: Annotated[Session, Depends(get_db)],
) -> ComponentRead:
    """Upload a STEP or STL 3D model file for a component."""
    comp = _call(svc.get_component, db, component_id)

    suffix = FilePath(file.filename or "model.step").suffix.lower()
    if suffix not in (".step", ".stp", ".stl"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {suffix}. Must be .step, .stp, or .stl",
        )

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / f"{component_id}_{uuid4().hex[:8]}{suffix}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    return _call(svc.update_component, db, component_id, ComponentWrite(
        name=comp.name,
        component_type=comp.component_type,
        manufacturer=comp.manufacturer,
        description=comp.description,
        mass_g=comp.mass_g,
        bbox_x_mm=comp.bbox_x_mm,
        bbox_y_mm=comp.bbox_y_mm,
        bbox_z_mm=comp.bbox_z_mm,
        model_ref=str(dest),
        specs=comp.specs,
    ))


@router.get(
    "/{component_id}/model",
    status_code=status.HTTP_200_OK,
    operation_id="download_component_model",
)
async def download_component_model(
    component_id: Annotated[int, Path(..., description="The component ID")],
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    """Download the 3D model file (STEP/STL) for a component."""
    comp = _call(svc.get_component, db, component_id)
    if not comp.model_ref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {component_id} has no 3D model uploaded",
        )
    path = FilePath(comp.model_ref)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model file not found on disk: {path.name}",
        )
    media_type = "application/sla" if path.suffix.lower() == ".stl" else "application/step"
    return FileResponse(path, media_type=media_type, filename=path.name)
