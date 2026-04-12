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
    aeroplane = db.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
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
    items = [_item_to_schema(i) for i in aeroplane.weight_items]
    total = sum(i.mass_kg for i in items)
    return WeightSummary(items=items, total_mass_kg=round(total, 6))


def create_weight_item(
    db: Session, aeroplane_uuid, data: WeightItemWrite
) -> WeightItemRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = WeightItemModel(aeroplane_id=aeroplane.id, **data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        return _item_to_schema(item)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in create_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_weight_item(db: Session, aeroplane_uuid, item_id: int) -> WeightItemRead:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    item = next((i for i in aeroplane.weight_items if i.id == item_id), None)
    if item is None:
        raise NotFoundError(entity="WeightItem", resource_id=item_id)
    return _item_to_schema(item)


def update_weight_item(
    db: Session, aeroplane_uuid, item_id: int, data: WeightItemWrite
) -> WeightItemRead:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = next((i for i in aeroplane.weight_items if i.id == item_id), None)
        if item is None:
            raise NotFoundError(entity="WeightItem", resource_id=item_id)
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        db.commit()
        db.refresh(item)
        return _item_to_schema(item)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in update_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_weight_item(db: Session, aeroplane_uuid, item_id: int) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        item = next((i for i in aeroplane.weight_items if i.id == item_id), None)
        if item is None:
            raise NotFoundError(entity="WeightItem", resource_id=item_id)
        db.delete(item)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in delete_weight_item: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
