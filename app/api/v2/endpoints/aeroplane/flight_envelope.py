"""Flight envelope endpoints — V-n diagram retrieval and computation."""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ServiceException
from app.db.session import get_db
from app.schemas.flight_envelope import FlightEnvelopeRead
from app.services import flight_envelope_service

router = APIRouter()


def _raise_http_from_domain(exc: ServiceException) -> NoReturn:
    """Map domain exceptions to HTTP status codes."""
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
        ) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get(
    "/aeroplanes/{aeroplane_id}/flight-envelope",
    operation_id="get_flight_envelope",
    tags=["flight-envelope"],
    responses={
        404: {"description": "No cached flight envelope found"},
    },
)
async def get_flight_envelope(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> FlightEnvelopeRead:
    """Return the cached flight envelope for an aeroplane, or 404 if none."""
    try:
        result = flight_envelope_service.get_flight_envelope(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No flight envelope computed yet for this aeroplane.",
        )
    return result


@router.post(
    "/aeroplanes/{aeroplane_id}/flight-envelope/compute",
    operation_id="compute_flight_envelope",
    tags=["flight-envelope"],
    responses={
        404: {"description": "Aeroplane not found"},
        500: {"description": "Computation error"},
    },
)
async def compute_flight_envelope_endpoint(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> FlightEnvelopeRead:
    """Compute (or recompute) the flight envelope for an aeroplane."""
    try:
        return flight_envelope_service.compute_flight_envelope(db, aeroplane_id)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
