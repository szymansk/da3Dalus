from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pydantic import UUID4
from sqlalchemy.orm import Session

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


@router.post(
    "/flight-profiles",
    response_model=RCFlightProfileRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_flight_profile",
    tags=["flight-profiles"],
)
async def create_flight_profile(
    payload: RCFlightProfileCreate,
    db: Session = Depends(get_db),
) -> RCFlightProfileRead:
    """Erstellt ein neues RC Flight Profile. Dieses Profil beschreibt gewünschte Flugeigenschaften, nicht eine konkrete Flugbahn."""
    return flight_profile_service.create_profile(db, payload)


@router.get(
    "/flight-profiles",
    response_model=list[RCFlightProfileRead],
    status_code=status.HTTP_200_OK,
    operation_id="list_flight_profiles",
    tags=["flight-profiles"],
)
async def list_flight_profiles(
    profile_type: Optional[FlightProfileType] = Query(
        default=None,
        alias="type",
        description="Optionaler Typfilter, z.B. trainer oder glider.",
    ),
    skip: int = Query(default=0, ge=0, description="Wie viele Einträge am Anfang übersprungen werden sollen."),
    limit: int = Query(default=100, ge=1, le=500, description="Maximale Anzahl zurückgegebener Profile."),
    db: Session = Depends(get_db),
) -> list[RCFlightProfileRead]:
    """Listet alle Profile auf. Optional kann nach Typ gefiltert und mit skip/limit paginiert werden."""
    return flight_profile_service.list_profiles(db, profile_type=profile_type, skip=skip, limit=limit)


@router.get(
    "/flight-profiles/{profile_id}",
    response_model=RCFlightProfileRead,
    status_code=status.HTTP_200_OK,
    operation_id="get_flight_profile",
    tags=["flight-profiles"],
)
async def get_flight_profile(
    profile_id: int = Path(..., ge=1, description="Interne numerische Profil-ID."),
    db: Session = Depends(get_db),
) -> RCFlightProfileRead:
    """Gibt ein einzelnes RC Flight Profile zurück."""
    return flight_profile_service.get_profile(db, profile_id)


@router.patch(
    "/flight-profiles/{profile_id}",
    response_model=RCFlightProfileRead,
    status_code=status.HTTP_200_OK,
    operation_id="update_flight_profile",
    tags=["flight-profiles"],
)
async def update_flight_profile(
    payload: RCFlightProfileUpdate,
    profile_id: int = Path(..., ge=1, description="Interne numerische Profil-ID."),
    db: Session = Depends(get_db),
) -> RCFlightProfileRead:
    """Teil-Update eines Profils. Nur übergebene Felder werden geändert; alle Validierungsregeln gelten weiterhin."""
    return flight_profile_service.update_profile(db, profile_id, payload)


@router.delete(
    "/flight-profiles/{profile_id}",
    response_class=Response,
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_flight_profile",
    tags=["flight-profiles"],
)
async def delete_flight_profile(
    profile_id: int = Path(..., ge=1, description="Interne numerische Profil-ID."),
    db: Session = Depends(get_db),
) -> Response:
    """Löscht ein Profil. Policy: 409 Conflict, solange das Profil noch Aircraft zugewiesen ist."""
    flight_profile_service.delete_profile(db, profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/aircraft/{aircraft_id}/flight-profile/{profile_id}",
    response_model=AircraftFlightProfileAssignmentRead,
    status_code=status.HTTP_200_OK,
    operation_id="assign_flight_profile_to_aircraft",
    tags=["flight-profiles"],
)
async def assign_flight_profile_to_aircraft(
    aircraft_id: AircraftID = Path(..., description="UUID des Aircrafts."),
    profile_id: int = Path(..., ge=1, description="ID des RC Flight Profiles."),
    db: Session = Depends(get_db),
) -> AircraftFlightProfileAssignmentRead:
    """Weist einem Aircraft ein RC Flight Profile zu und überschreibt eine bestehende Zuweisung."""
    return flight_profile_service.assign_profile_to_aircraft(db, aircraft_id, profile_id)


@router.delete(
    "/aircraft/{aircraft_id}/flight-profile",
    response_model=AircraftFlightProfileAssignmentRead,
    status_code=status.HTTP_200_OK,
    operation_id="detach_flight_profile_from_aircraft",
    tags=["flight-profiles"],
)
async def detach_flight_profile_from_aircraft(
    aircraft_id: AircraftID = Path(..., description="UUID des Aircrafts."),
    db: Session = Depends(get_db),
) -> AircraftFlightProfileAssignmentRead:
    """Entfernt die Profilzuweisung eines Aircrafts und setzt flight_profile_id auf NULL."""
    return flight_profile_service.detach_profile_from_aircraft(db, aircraft_id)
