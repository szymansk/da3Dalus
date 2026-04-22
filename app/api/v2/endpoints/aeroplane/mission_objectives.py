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
from app.schemas.mission_objectives import MissionObjectivesRead, MissionObjectivesWrite
from app.services import mission_objectives_service as svc

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
    "/aeroplanes/{aeroplane_id}/mission-objectives",
    status_code=status.HTTP_200_OK,
    tags=["mission-objectives"],
    operation_id="get_mission_objectives"
)
async def get_mission_objectives(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> MissionObjectivesRead:
    """Get the mission objectives for the aeroplane."""
    return _call(svc.get_mission_objectives, db, aeroplane_id)


@router.put(
    "/aeroplanes/{aeroplane_id}/mission-objectives",
    status_code=status.HTTP_200_OK,
    tags=["mission-objectives"],
    operation_id="upsert_mission_objectives"
)
async def upsert_mission_objectives(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[MissionObjectivesWrite, Body(..., description="Mission objectives data")],
    db: Annotated[Session, Depends(get_db)],
) -> MissionObjectivesRead:
    """Create or update the mission objectives for the aeroplane."""
    return _call(svc.upsert_mission_objectives, db, aeroplane_id, body)


@router.delete(
    "/aeroplanes/{aeroplane_id}/mission-objectives",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["mission-objectives"],
    operation_id="delete_mission_objectives",
)
async def delete_mission_objectives(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete the mission objectives for the aeroplane."""
    _call(svc.delete_mission_objectives, db, aeroplane_id)
