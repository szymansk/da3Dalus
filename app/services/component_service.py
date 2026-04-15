"""Component Library Service — CRUD for hardware components."""

import logging
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.component import ComponentModel
from app.schemas.component import ComponentList, ComponentRead, ComponentWrite

logger = logging.getLogger(__name__)


def _to_schema(m: ComponentModel) -> ComponentRead:
    return ComponentRead(
        id=m.id,
        name=m.name,
        component_type=m.component_type,
        manufacturer=m.manufacturer,
        description=m.description,
        mass_g=m.mass_g,
        bbox_x_mm=m.bbox_x_mm,
        bbox_y_mm=m.bbox_y_mm,
        bbox_z_mm=m.bbox_z_mm,
        model_ref=m.model_ref,
        specs=m.specs or {},
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def list_components(
    db: Session,
    component_type: Optional[str] = None,
    q: Optional[str] = None,
) -> ComponentList:
    query = db.query(ComponentModel)
    if component_type:
        query = query.filter(ComponentModel.component_type == component_type)
    if q:
        query = query.filter(
            ComponentModel.name.ilike(f"%{q}%") | ComponentModel.manufacturer.ilike(f"%{q}%")
        )
    query = query.order_by(ComponentModel.component_type, ComponentModel.name)
    rows = query.all()
    return ComponentList(
        items=[_to_schema(r) for r in rows],
        total=len(rows),
    )


def create_component(db: Session, data: ComponentWrite) -> ComponentRead:
    try:
        comp = ComponentModel(**data.model_dump())
        db.add(comp)
        db.commit()
        db.refresh(comp)
        return _to_schema(comp)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in create_component: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_component(db: Session, component_id: int) -> ComponentRead:
    comp = db.query(ComponentModel).filter(ComponentModel.id == component_id).first()
    if comp is None:
        raise NotFoundError(entity="Component", resource_id=component_id)
    return _to_schema(comp)


def update_component(
    db: Session, component_id: int, data: ComponentWrite
) -> ComponentRead:
    try:
        comp = db.query(ComponentModel).filter(ComponentModel.id == component_id).first()
        if comp is None:
            raise NotFoundError(entity="Component", resource_id=component_id)
        for key, value in data.model_dump().items():
            setattr(comp, key, value)
        db.commit()
        db.refresh(comp)
        return _to_schema(comp)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in update_component: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_component(db: Session, component_id: int) -> None:
    try:
        comp = db.query(ComponentModel).filter(ComponentModel.id == component_id).first()
        if comp is None:
            raise NotFoundError(entity="Component", resource_id=component_id)
        db.delete(comp)
        db.commit()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in delete_component: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
