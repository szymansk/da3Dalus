from typing import Annotated
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.weight_item import WeightItemRead, WeightItemWrite, WeightSummary
from app.services import weight_items_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/weight-items",
    status_code=status.HTTP_200_OK,
    tags=["weight-items"],
    operation_id="list_weight_items",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def list_weight_items(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> WeightSummary:
    """List all weight items with a total mass summary."""
    return _call(svc.list_weight_items, db, aeroplane_id)


@router.post(
    "/aeroplanes/{aeroplane_id}/weight-items",
    status_code=status.HTTP_201_CREATED,
    tags=["weight-items"],
    operation_id="create_weight_item",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def create_weight_item(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[WeightItemWrite, Body(..., description="Weight item data")],
    db: Annotated[Session, Depends(get_db)],
) -> WeightItemRead:
    """Add a new weight item to the aeroplane."""
    return _call(svc.create_weight_item, db, aeroplane_id, body)


@router.get(
    "/aeroplanes/{aeroplane_id}/weight-items/{item_id}",
    status_code=status.HTTP_200_OK,
    tags=["weight-items"],
    operation_id="get_weight_item",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def get_weight_item(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    item_id: Annotated[int, Path(..., description="The ID of the weight item")],
    db: Annotated[Session, Depends(get_db)],
) -> WeightItemRead:
    """Get a single weight item by ID."""
    return _call(svc.get_weight_item, db, aeroplane_id, item_id)


@router.put(
    "/aeroplanes/{aeroplane_id}/weight-items/{item_id}",
    status_code=status.HTTP_200_OK,
    tags=["weight-items"],
    operation_id="update_weight_item",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def update_weight_item(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    item_id: Annotated[int, Path(..., description="The ID of the weight item")],
    body: Annotated[WeightItemWrite, Body(..., description="Weight item data")],
    db: Annotated[Session, Depends(get_db)],
) -> WeightItemRead:
    """Update an existing weight item."""
    return _call(svc.update_weight_item, db, aeroplane_id, item_id, body)


@router.delete(
    "/aeroplanes/{aeroplane_id}/weight-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["weight-items"],
    operation_id="delete_weight_item",
    responses={
        404: {"description": "Resource not found"},
        409: {"description": "Conflict"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"},
    },
)
async def delete_weight_item(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    item_id: Annotated[int, Path(..., description="The ID of the weight item")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a weight item."""
    _call(svc.delete_weight_item, db, aeroplane_id, item_id)
