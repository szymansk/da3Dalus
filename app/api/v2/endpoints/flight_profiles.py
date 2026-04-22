from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ServiceException,
    NotFoundError,
    ValidationError,
    ValidationDomainError,
    ConflictError,
    InternalError,
)
from app.db.session import get_db
from app.schemas.flight_profile import (
    AircraftFlightProfileAssignmentRead,
    FlightProfileType,
    RCFlightProfileCreate,
    RCFlightProfileRead,
    RCFlightProfileUpdate,
)
from app.services import flight_profile_service

router = APIRouter()
AircraftID = UUID4


class OperationStatusResponse(BaseModel):
    status: str
    operation: str


def _raise_http_from_domain(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, (ValidationError, ValidationDomainError)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message) from exc
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


def _call_service(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except Exception as exc:  # pragma: no cover - defensive fallback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc


@router.post(
    "/flight-profiles",
    status_code=status.HTTP_201_CREATED,
    operation_id="create_flight_profile",
    tags=["flight-profiles"]
)
async def create_flight_profile(
    payload: RCFlightProfileCreate,
    db: Annotated[Session, Depends(get_db)],
) -> RCFlightProfileRead:
    """Erstellt ein neues RC Flight Profile. Dieses Profil beschreibt gewünschte Flugeigenschaften, nicht eine konkrete Flugbahn."""
    return _call_service(flight_profile_service.create_profile, db, payload)


@router.get(
    "/flight-profiles",
    status_code=status.HTTP_200_OK,
    operation_id="list_flight_profiles",
    tags=["flight-profiles"]
)
async def list_flight_profiles(
    db: Annotated[Session, Depends(get_db)],
    profile_type: Annotated[Optional[FlightProfileType], Query(
        alias="type",
        description="Optionaler Typfilter, z.B. trainer oder glider.",
    )] = None,
    skip: Annotated[int, Query(ge=0, description="Wie viele Einträge am Anfang übersprungen werden sollen.")] = 0,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximale Anzahl zurückgegebener Profile.")] = 100,
) -> list[RCFlightProfileRead]:
    """Listet alle Profile auf. Optional kann nach Typ gefiltert und mit skip/limit paginiert werden."""
    return _call_service(
        flight_profile_service.list_profiles,
        db,
        profile_type=profile_type,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/flight-profiles/{profile_id}",
    status_code=status.HTTP_200_OK,
    operation_id="get_flight_profile",
    tags=["flight-profiles"]
)
async def get_flight_profile(
    profile_id: Annotated[int, Path(..., ge=1, description="Interne numerische Profil-ID.")],
    db: Annotated[Session, Depends(get_db)],
) -> RCFlightProfileRead:
    """Gibt ein einzelnes RC Flight Profile zurück."""
    return _call_service(flight_profile_service.get_profile, db, profile_id)


@router.patch(
    "/flight-profiles/{profile_id}",
    status_code=status.HTTP_200_OK,
    operation_id="update_flight_profile",
    tags=["flight-profiles"]
)
async def update_flight_profile(
    payload: RCFlightProfileUpdate,
    profile_id: Annotated[int, Path(..., ge=1, description="Interne numerische Profil-ID.")],
    db: Annotated[Session, Depends(get_db)],
) -> RCFlightProfileRead:
    """Teil-Update eines Profils. Nur übergebene Felder werden geändert; alle Validierungsregeln gelten weiterhin."""
    return _call_service(flight_profile_service.update_profile, db, profile_id, payload)


@router.delete(
    "/flight-profiles/{profile_id}",
    status_code=status.HTTP_200_OK,
    operation_id="delete_flight_profile",
    tags=["flight-profiles"]
)
async def delete_flight_profile(
    profile_id: Annotated[int, Path(..., ge=1, description="Interne numerische Profil-ID.")],
    db: Annotated[Session, Depends(get_db)],
) -> OperationStatusResponse:
    """Löscht ein Profil. Policy: 409 Conflict, solange das Profil noch Aircraft zugewiesen ist."""
    _call_service(flight_profile_service.delete_profile, db, profile_id)
    return OperationStatusResponse(status="ok", operation="delete_flight_profile")


@router.put(
    "/aeroplanes/{aeroplane_id}/flight-profile/{profile_id}",
    status_code=status.HTTP_200_OK,
    operation_id="assign_flight_profile_to_aeroplane",
    tags=["flight-profiles"]
)
async def assign_flight_profile_to_aeroplane(
    aeroplane_id: Annotated[AircraftID, Path(..., description="UUID des Aeroplanes.")],
    profile_id: Annotated[int, Path(..., ge=1, description="ID des RC Flight Profiles.")],
    db: Annotated[Session, Depends(get_db)],
) -> AircraftFlightProfileAssignmentRead:
    """Weist einem Aeroplane ein RC Flight Profile zu und überschreibt eine bestehende Zuweisung."""
    return _call_service(flight_profile_service.assign_profile_to_aircraft, db, aeroplane_id, profile_id)


@router.delete(
    "/aeroplanes/{aeroplane_id}/flight-profile",
    status_code=status.HTTP_200_OK,
    operation_id="detach_flight_profile_from_aeroplane",
    tags=["flight-profiles"]
)
async def detach_flight_profile_from_aeroplane(
    aeroplane_id: Annotated[AircraftID, Path(..., description="UUID des Aeroplanes.")],
    db: Annotated[Session, Depends(get_db)],
) -> AircraftFlightProfileAssignmentRead:
    """Entfernt die Profilzuweisung eines Aeroplanes und setzt flight_profile_id auf NULL."""
    return _call_service(flight_profile_service.detach_profile_from_aircraft, db, aeroplane_id)
