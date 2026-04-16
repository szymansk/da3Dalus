"""Construction Parts service (gh#57-g4h).

MVP: list, get, lock, unlock. File upload/download and general CRUD
arrive in gh#57-9uk.
"""
from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.construction_part import ConstructionPartModel
from app.schemas.construction_part import ConstructionPartList, ConstructionPartRead

logger = logging.getLogger(__name__)


def _get_part_or_404(
    db: Session, aeroplane_id: str, part_id: int
) -> ConstructionPartModel:
    """Fetch a part by (aeroplane_id, id). Raises NotFoundError if either check fails.

    Aeroplane scoping is enforced here so that callers cannot cross-access a
    part that belongs to a different aeroplane by guessing its ID.
    """
    part = (
        db.query(ConstructionPartModel)
        .filter(
            ConstructionPartModel.id == part_id,
            ConstructionPartModel.aeroplane_id == aeroplane_id,
        )
        .first()
    )
    if part is None:
        raise NotFoundError(entity="ConstructionPart", resource_id=part_id)
    return part


def list_parts(db: Session, aeroplane_id: str) -> ConstructionPartList:
    rows = (
        db.query(ConstructionPartModel)
        .filter(ConstructionPartModel.aeroplane_id == aeroplane_id)
        .order_by(ConstructionPartModel.name)
        .all()
    )
    return ConstructionPartList(
        aeroplane_id=aeroplane_id,
        items=[ConstructionPartRead.model_validate(r) for r in rows],
        total=len(rows),
    )


def get_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    part = _get_part_or_404(db, aeroplane_id, part_id)
    return ConstructionPartRead.model_validate(part)


def _set_locked(
    db: Session, aeroplane_id: str, part_id: int, locked: bool
) -> ConstructionPartRead:
    try:
        part = _get_part_or_404(db, aeroplane_id, part_id)
        part.locked = locked
        db.commit()
        db.refresh(part)
        return ConstructionPartRead.model_validate(part)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error while toggling lock on part %s: %s", part_id, exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def lock_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    """Set locked=True. Idempotent when the part is already locked."""
    return _set_locked(db, aeroplane_id, part_id, True)


def unlock_part(db: Session, aeroplane_id: str, part_id: int) -> ConstructionPartRead:
    """Set locked=False. Idempotent when the part is already unlocked."""
    return _set_locked(db, aeroplane_id, part_id, False)
