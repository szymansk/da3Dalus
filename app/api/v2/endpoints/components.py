import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.component import ComponentList, ComponentRead, ComponentWrite
from app.services import component_service as svc

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
    response_model=ComponentList,
    operation_id="list_components",
)
async def list_components(
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    q: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
) -> ComponentList:
    """List all components, optionally filtered by type or name search."""
    return _call(svc.list_components, db, component_type, q)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ComponentRead,
    operation_id="create_component",
)
async def create_component(
    body: ComponentWrite = Body(..., description="Component data"),
    db: Session = Depends(get_db),
) -> ComponentRead:
    """Create a new component in the library."""
    return _call(svc.create_component, db, body)


@router.get(
    "/{component_id}",
    status_code=status.HTTP_200_OK,
    response_model=ComponentRead,
    operation_id="get_component",
)
async def get_component(
    component_id: int = Path(..., description="The component ID"),
    db: Session = Depends(get_db),
) -> ComponentRead:
    """Get a single component by ID."""
    return _call(svc.get_component, db, component_id)


@router.put(
    "/{component_id}",
    status_code=status.HTTP_200_OK,
    response_model=ComponentRead,
    operation_id="update_component",
)
async def update_component(
    component_id: int = Path(..., description="The component ID"),
    body: ComponentWrite = Body(..., description="Component data"),
    db: Session = Depends(get_db),
) -> ComponentRead:
    """Update an existing component."""
    return _call(svc.update_component, db, component_id, body)


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_component",
)
async def delete_component(
    component_id: int = Path(..., description="The component ID"),
    db: Session = Depends(get_db),
) -> None:
    """Delete a component from the library."""
    _call(svc.delete_component, db, component_id)
