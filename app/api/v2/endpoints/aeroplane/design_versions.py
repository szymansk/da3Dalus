import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.design_version import (
    DesignVersionCreate,
    DesignVersionDiff,
    DesignVersionRead,
    DesignVersionSummary,
)
from app.services import design_version_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


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
    "/aeroplanes/{aeroplane_id}/design-versions",
    status_code=status.HTTP_200_OK,
    response_model=list[DesignVersionSummary],
    tags=["design-versions"],
    operation_id="list_design_versions",
)
async def list_design_versions(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    db: Session = Depends(get_db),
) -> list[DesignVersionSummary]:
    """List all design version snapshots for the aeroplane."""
    return _call(svc.list_versions, db, aeroplane_id)


@router.post(
    "/aeroplanes/{aeroplane_id}/design-versions",
    status_code=status.HTTP_201_CREATED,
    response_model=DesignVersionSummary,
    tags=["design-versions"],
    operation_id="create_design_version",
)
async def create_design_version(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    body: DesignVersionCreate = Body(..., description="Version metadata"),
    db: Session = Depends(get_db),
) -> DesignVersionSummary:
    """Snapshot the current aeroplane state as a new design version."""
    return _call(svc.create_version, db, aeroplane_id, body)


@router.get(
    "/aeroplanes/{aeroplane_id}/design-versions/{version_id}",
    status_code=status.HTTP_200_OK,
    response_model=DesignVersionRead,
    tags=["design-versions"],
    operation_id="get_design_version",
)
async def get_design_version(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    version_id: int = Path(..., description="The version ID"),
    db: Session = Depends(get_db),
) -> DesignVersionRead:
    """Read a specific design version including the full snapshot."""
    return _call(svc.get_version, db, aeroplane_id, version_id)


@router.delete(
    "/aeroplanes/{aeroplane_id}/design-versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["design-versions"],
    operation_id="delete_design_version",
)
async def delete_design_version(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    version_id: int = Path(..., description="The version ID"),
    db: Session = Depends(get_db),
) -> None:
    """Delete a design version snapshot."""
    _call(svc.delete_version, db, aeroplane_id, version_id)


@router.get(
    "/aeroplanes/{aeroplane_id}/design-versions/{version_a}/diff/{version_b}",
    status_code=status.HTTP_200_OK,
    response_model=DesignVersionDiff,
    tags=["design-versions"],
    operation_id="diff_design_versions",
)
async def diff_design_versions(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    version_a: int = Path(..., description="First version ID"),
    version_b: int = Path(..., description="Second version ID"),
    db: Session = Depends(get_db),
) -> DesignVersionDiff:
    """Compute a structural diff between two design versions."""
    return _call(svc.diff_versions, db, aeroplane_id, version_a, version_b)
