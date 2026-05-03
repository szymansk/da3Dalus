import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel
from app.models.flightprofilemodel import RCFlightProfileModel
from app.schemas.flight_profile import (
    AircraftFlightProfileAssignmentRead,
    FlightProfileType,
    RCFlightProfileCreate,
    RCFlightProfileRead,
    RCFlightProfileUpdate,
)

logger = logging.getLogger(__name__)

# --- Shared error message (S1192) ---
_ERR_NAME_EXISTS = "name existiert bereits"


def _get_profile_or_raise(db: Session, profile_id: int) -> RCFlightProfileModel:
    profile = db.query(RCFlightProfileModel).filter(RCFlightProfileModel.id == profile_id).first()
    if not profile:
        raise NotFoundError(entity="RCFlightProfile", resource_id=profile_id)
    return profile


def _get_aircraft_or_raise(db: Session, aircraft_id) -> AeroplaneModel:
    aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_id).first()
    if not aircraft:
        raise NotFoundError(entity="Aircraft", resource_id=aircraft_id)
    return aircraft


def _merge_dict(base: dict, update: Optional[dict]) -> dict:
    if not update:
        return dict(base)
    merged = dict(base)
    for key, value in update.items():
        merged[key] = value
    return merged


def create_profile(db: Session, payload: RCFlightProfileCreate) -> RCFlightProfileRead:
    try:
        existing = db.query(RCFlightProfileModel).filter(RCFlightProfileModel.name == payload.name).first()
        if existing:
            raise ConflictError(_ERR_NAME_EXISTS)

        profile = RCFlightProfileModel(**payload.model_dump())
        db.add(profile)
        db.flush()
        db.refresh(profile)
        return RCFlightProfileRead.model_validate(profile, from_attributes=True)
    except ConflictError:
        raise
    except IntegrityError:
        raise ConflictError(_ERR_NAME_EXISTS)
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def list_profiles(
    db: Session,
    profile_type: Optional[FlightProfileType] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[RCFlightProfileRead]:
    try:
        query = db.query(RCFlightProfileModel).order_by(RCFlightProfileModel.name)
        if profile_type is not None:
            query = query.filter(RCFlightProfileModel.type == profile_type.value)
        rows = query.offset(skip).limit(limit).all()
        return [RCFlightProfileRead.model_validate(row, from_attributes=True) for row in rows]
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def get_profile(db: Session, profile_id: int) -> RCFlightProfileRead:
    try:
        profile = _get_profile_or_raise(db, profile_id)
        return RCFlightProfileRead.model_validate(profile, from_attributes=True)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def update_profile(db: Session, profile_id: int, payload: RCFlightProfileUpdate) -> RCFlightProfileRead:
    try:
        profile = _get_profile_or_raise(db, profile_id)

        update_data = payload.model_dump(exclude_unset=True)
        target_name = update_data.get("name")
        if target_name and target_name != profile.name:
            existing = db.query(RCFlightProfileModel).filter(RCFlightProfileModel.name == target_name).first()
            if existing:
                raise ConflictError(_ERR_NAME_EXISTS)

        merged_payload = {
            "name": update_data.get("name", profile.name),
            "type": update_data.get("type", profile.type),
            "environment": _merge_dict(profile.environment, update_data.get("environment")),
            "goals": _merge_dict(profile.goals, update_data.get("goals")),
            "handling": _merge_dict(profile.handling, update_data.get("handling")),
            "constraints": _merge_dict(profile.constraints, update_data.get("constraints")),
        }

        normalized = RCFlightProfileCreate.model_validate(merged_payload)

        profile.name = normalized.name
        profile.type = normalized.type.value
        profile.environment = normalized.environment.model_dump()
        profile.goals = normalized.goals.model_dump()
        profile.handling = normalized.handling.model_dump()
        profile.constraints = normalized.constraints.model_dump()
        profile.updated_at = datetime.now(timezone.utc)
        db.add(profile)
        db.flush()
        db.refresh(profile)

        return RCFlightProfileRead.model_validate(profile, from_attributes=True)
    except (NotFoundError, ConflictError):
        raise
    except IntegrityError:
        raise ConflictError(_ERR_NAME_EXISTS)
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def delete_profile(db: Session, profile_id: int) -> None:
    try:
        profile = _get_profile_or_raise(db, profile_id)
        assigned_count = (
            db.query(AeroplaneModel).filter(AeroplaneModel.flight_profile_id == profile_id).count()
        )
        if assigned_count > 0:
            raise ConflictError(
                "Das Profil ist noch Aircraft zugewiesen und kann nicht gelöscht werden. Entferne zuerst die Zuweisungen."
            )

        db.delete(profile)
        db.flush()
    except (NotFoundError, ConflictError):
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def assign_profile_to_aircraft(
    db: Session,
    aircraft_id,
    profile_id: int,
) -> AircraftFlightProfileAssignmentRead:
    try:
        aircraft = _get_aircraft_or_raise(db, aircraft_id)
        profile = _get_profile_or_raise(db, profile_id)

        aircraft.flight_profile_id = profile.id
        aircraft.updated_at = datetime.now(timezone.utc)
        db.add(aircraft)
        db.flush()

        return AircraftFlightProfileAssignmentRead(
            aircraft_id=str(aircraft.uuid),
            flight_profile_id=aircraft.flight_profile_id,
        )
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")


def detach_profile_from_aircraft(db: Session, aircraft_id) -> AircraftFlightProfileAssignmentRead:
    try:
        aircraft = _get_aircraft_or_raise(db, aircraft_id)

        aircraft.flight_profile_id = None
        aircraft.updated_at = datetime.now(timezone.utc)
        db.add(aircraft)
        db.flush()

        return AircraftFlightProfileAssignmentRead(
            aircraft_id=str(aircraft.uuid),
            flight_profile_id=aircraft.flight_profile_id,
        )
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        raise InternalError(f"Database error: {exc}")
