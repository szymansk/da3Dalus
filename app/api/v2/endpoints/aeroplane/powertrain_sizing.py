import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    ServiceException,
    ValidationError,
)
from app.db.session import get_db
from app.schemas.powertrain_sizing import PowertrainSizingRequest, PowertrainSizingResponse
from app.services import powertrain_sizing_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post(
    "/aeroplanes/{aeroplane_id}/powertrain/sizing",
    status_code=status.HTTP_200_OK,
    response_model=PowertrainSizingResponse,
    tags=["powertrain"],
    operation_id="size_powertrain",
)
async def size_powertrain(
    aeroplane_id: UUID4 = Path(..., description="The ID of the aeroplane"),
    body: PowertrainSizingRequest = Body(..., description="Mission parameters for sizing"),
    db: Session = Depends(get_db),
) -> PowertrainSizingResponse:
    """Recommend motor+ESC+battery combos that fit the given mission parameters."""
    return _call(svc.size_powertrain, db, aeroplane_id, body)
