"""Weight Items Service — CRUD for per-aeroplane weight inventory."""

import logging
from typing import List

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import AeroplaneModel, WeightItemModel
from app.schemas.weight_item import WeightItemRead, WeightItemWrite, WeightSummary

logger = logging.getLogger(__name__)


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _item_to_schema(item: WeightItemModel) -> WeightItemRead:
    return WeightItemRead(
        id=item.id,
        name=item.name,
        mass_kg=item.mass_kg,
        x_m=item.x_m,
        y_m=item.y_m,
        z_m=item.z_m,
        description=item.description,
        category=item.category,
    )


def list_weight_items(db: Session, aeroplane_uuid) -> WeightSummary:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    rows = db.query(WeightItemModel).filter(WeightItemModel.aeroplane_id == aeroplane.id).all()
    items = [_item_to_schema(i) for i in rows]
    total = sum(i.mass_kg for i in items)

    cg_x = cg_y = cg_z = None
    if total > 0:
        cg_x = round(sum(i.mass_kg * i.x_m for i in items) / total, 6)
        cg_y = round(sum(i.mass_kg * i.y_m for i in items) / total, 6)
        cg_z = round(sum(i.mass_kg * i.z_m for i in items) / total, 6)

    return WeightSummary(
        items=items,
        total_mass_kg=round(total, 6),
        cg_x_m=cg_x,
        cg_y_m=cg_y,
        cg_z_m=cg_z,
    )


def _try_sync_assumptions(db: Session, aeroplane_uuid) -> None:
    """Best-effort sync of weight items to design assumption calculated values."""
    try:
        from app.services.mass_cg_service import sync_weight_items_to_assumptions

        sync_weight_items_to_assumptions(db, aeroplane_uuid)
    except (NotFoundError, SQLAlchemyError) as exc:
        logger.warning("Skipped assumption sync: %s", exc)


def create_weight_item(db: Session, aeroplane_uuid, data: WeightItemWrite) -> WeightItemRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = WeightItemModel(aeroplane_id=aeroplane.id, **data.model_dump())
        db.add(item)
        db.flush()
        db.refresh(item)
        _try_sync_assumptions(db, aeroplane_uuid)
        return _item_to_schema(item)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in create_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_weight_item(db: Session, aeroplane_uuid, item_id: int) -> WeightItemRead:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    item = (
        db.query(WeightItemModel)
        .filter(WeightItemModel.aeroplane_id == aeroplane.id, WeightItemModel.id == item_id)
        .first()
    )
    if item is None:
        raise NotFoundError(entity="WeightItem", resource_id=item_id)
    return _item_to_schema(item)


def update_weight_item(
    db: Session, aeroplane_uuid, item_id: int, data: WeightItemWrite
) -> WeightItemRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = (
            db.query(WeightItemModel)
            .filter(WeightItemModel.aeroplane_id == aeroplane.id, WeightItemModel.id == item_id)
            .first()
        )
        if item is None:
            raise NotFoundError(entity="WeightItem", resource_id=item_id)
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        db.flush()
        db.refresh(item)
        _try_sync_assumptions(db, aeroplane_uuid)
        return _item_to_schema(item)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_weight_item(db: Session, aeroplane_uuid, item_id: int) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = (
            db.query(WeightItemModel)
            .filter(WeightItemModel.aeroplane_id == aeroplane.id, WeightItemModel.id == item_id)
            .first()
        )
        if item is None:
            raise NotFoundError(entity="WeightItem", resource_id=item_id)
        db.delete(item)
        db.flush()
        _try_sync_assumptions(db, aeroplane_uuid)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
