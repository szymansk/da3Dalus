"""Endpoints for the per-aeroplane Construction-Parts domain (gh#57-g4h)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    ServiceException,
    ValidationDomainError,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.construction_part import ConstructionPartList, ConstructionPartRead
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
