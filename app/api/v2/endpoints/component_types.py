"""Endpoints for the Component Types registry (gh#83)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.component_type import ComponentTypeRead, ComponentTypeWrite
from app.services import component_type_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/component-types", tags=["component-types"])


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
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
    response_model=list[ComponentTypeRead],
    operation_id="list_component_types_v2",
)
async def list_component_types(
    db: Session = Depends(get_db),
) -> list[ComponentTypeRead]:
    """List all component types (seeded + user-created) sorted by label."""
    return _call(svc.list_types, db)


@router.get(
    "/{type_id}",
    status_code=status.HTTP_200_OK,
    response_model=ComponentTypeRead,
    operation_id="get_component_type",
)
async def get_component_type(
    type_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ComponentTypeRead:
    return _call(svc.get_type, db, type_id)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ComponentTypeRead,
    operation_id="create_component_type",
)
async def create_component_type(
    body: ComponentTypeWrite = Body(...),
    db: Session = Depends(get_db),
) -> ComponentTypeRead:
    """Create a user-defined type. `deletable` is forced to True regardless of request."""
    return _call(svc.create_type, db, body)


@router.put(
    "/{type_id}",
    status_code=status.HTTP_200_OK,
    response_model=ComponentTypeRead,
    operation_id="update_component_type",
)
async def update_component_type(
    type_id: int = Path(...),
    body: ComponentTypeWrite = Body(...),
    db: Session = Depends(get_db),
) -> ComponentTypeRead:
    """Update label / description / schema. Name and deletable are immutable."""
    return _call(svc.update_type, db, type_id, body)


@router.delete(
    "/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_component_type",
)
async def delete_component_type(
    type_id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    """Delete a type. 409 if seeded (deletable=False) or referenced by components."""
    _call(svc.delete_type, db, type_id)
