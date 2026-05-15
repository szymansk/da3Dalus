"""REST endpoints for Mission Objectives + Mission Presets (gh-546)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_objective import MissionObjective, MissionPreset
from app.services.mission_objective_service import (
    get_mission_objective,
    list_mission_presets,
    upsert_mission_objective,
)

router = APIRouter()


def _resolve_aeroplane_id(db: Session, uuid: UUID4) -> int:
    row = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == uuid).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"aeroplane {uuid} not found")
    return row.id


@router.get(
    "/aeroplanes/{uuid}/mission-objectives",
    response_model=MissionObjective,
    summary="Read Mission Objectives for an aeroplane",
    tags=["mission"],
)
def get_objectives(uuid: UUID4, db: Session = Depends(get_db)) -> MissionObjective:
    aeroplane_id = _resolve_aeroplane_id(db, uuid)
    return get_mission_objective(db, aeroplane_id)


@router.put(
    "/aeroplanes/{uuid}/mission-objectives",
    response_model=MissionObjective,
    summary="Create or update Mission Objectives for an aeroplane",
    tags=["mission"],
)
def put_objectives(
    uuid: UUID4, payload: MissionObjective, db: Session = Depends(get_db)
) -> MissionObjective:
    aeroplane_id = _resolve_aeroplane_id(db, uuid)
    return upsert_mission_objective(db, aeroplane_id, payload)


@router.get(
    "/mission-presets",
    response_model=list[MissionPreset],
    summary="List all Mission Presets",
    tags=["mission"],
)
def get_presets(db: Session = Depends(get_db)) -> list[MissionPreset]:
    return list_mission_presets(db)
