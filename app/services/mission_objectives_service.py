"""Mission Objectives Service — CRUD for per-aeroplane mission objectives."""

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel, MissionObjectivesModel
from app.schemas.mission_objectives import MissionObjectivesRead, MissionObjectivesWrite

logger = logging.getLogger(__name__)


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def get_mission_objectives(db: Session, aeroplane_uuid) -> MissionObjectivesRead:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    obj = aeroplane.mission_objectives
    if obj is None:
        raise NotFoundError(entity="MissionObjectives", resource_id=aeroplane_uuid)
    return _model_to_schema(obj)


def upsert_mission_objectives(
    db: Session, aeroplane_uuid, data: MissionObjectivesWrite
) -> MissionObjectivesRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        obj = aeroplane.mission_objectives

        flat = _schema_to_columns(data)

        if obj is None:
            obj = MissionObjectivesModel(aeroplane_id=aeroplane.id, **flat)
            db.add(obj)
        else:
            for key, value in flat.items():
                setattr(obj, key, value)

        db.commit()
        db.refresh(obj)
        return _model_to_schema(obj)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in upsert_mission_objectives: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_mission_objectives(db: Session, aeroplane_uuid) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        obj = aeroplane.mission_objectives
        if obj is None:
            raise NotFoundError(entity="MissionObjectives", resource_id=aeroplane_uuid)
        db.delete(obj)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in delete_mission_objectives: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


# ── helpers ──────────────────────────────────────────────────────────

def _schema_to_columns(data: MissionObjectivesWrite) -> dict:
    d = data.model_dump()
    envelope = d.pop("size_envelope", None)
    if envelope:
        d["size_envelope_length_mm"] = envelope.get("length_mm")
        d["size_envelope_width_mm"] = envelope.get("width_mm")
        d["size_envelope_height_mm"] = envelope.get("height_mm")
    else:
        d["size_envelope_length_mm"] = None
        d["size_envelope_width_mm"] = None
        d["size_envelope_height_mm"] = None
    return d


def _model_to_schema(obj: MissionObjectivesModel) -> MissionObjectivesRead:
    from app.schemas.mission_objectives import SizeEnvelope

    envelope = None
    if any(v is not None for v in [
        obj.size_envelope_length_mm, obj.size_envelope_width_mm, obj.size_envelope_height_mm
    ]):
        envelope = SizeEnvelope(
            length_mm=obj.size_envelope_length_mm,
            width_mm=obj.size_envelope_width_mm,
            height_mm=obj.size_envelope_height_mm,
        )

    return MissionObjectivesRead(
        payload_kg=obj.payload_kg,
        target_flight_time_min=obj.target_flight_time_min,
        maneuverability_class=obj.maneuverability_class,
        size_envelope=envelope,
        engine_type=obj.engine_type,
        target_stall_speed_ms=obj.target_stall_speed_ms,
        target_cruise_speed_ms=obj.target_cruise_speed_ms,
        target_top_speed_ms=obj.target_top_speed_ms,
    )
