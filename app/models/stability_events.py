"""SQLAlchemy event listeners that mark stability results as dirty
when the airplane's wing or fuselage geometry changes."""

from __future__ import annotations

import logging

from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.core.events import GeometryChanged, event_bus
from app.models.aeroplanemodel import FuselageModel, WingModel, WingXSecModel
from app.models.stability_result import StabilityResultModel
from app.services.invalidation_service import mark_ops_dirty

logger = logging.getLogger(__name__)

_GEOMETRY_MODELS = (WingModel, WingXSecModel, FuselageModel)


def _mark_stability_dirty(session: Session, aeroplane_id: int | None) -> None:
    if aeroplane_id is None:
        return
    session.execute(
        update(StabilityResultModel)
        .where(StabilityResultModel.aeroplane_id == aeroplane_id)
        .values(status="DIRTY")
    )


def _resolve_aeroplane_id(target) -> int | None:
    if isinstance(target, (WingModel, FuselageModel)):
        return target.aeroplane_id
    if isinstance(target, WingXSecModel):
        if target.wing is not None:
            return target.wing.aeroplane_id
        session = Session.object_session(target)
        if session is not None and target.wing_id is not None:
            wing = session.get(WingModel, target.wing_id)
            if wing is not None:
                return wing.aeroplane_id
    return None


def _on_geometry_change(mapper, connection, target):
    session = Session.object_session(target)
    if session is None:
        return
    aeroplane_id = _resolve_aeroplane_id(target)
    _mark_stability_dirty(session, aeroplane_id)
    if aeroplane_id is not None:
        mark_ops_dirty(session, aeroplane_id)
        event_bus.publish(
            GeometryChanged(aeroplane_id=aeroplane_id, source_model=type(target).__name__)
        )


for _model in _GEOMETRY_MODELS:
    for _event_name in ("after_insert", "after_update", "after_delete"):
        event.listen(_model, _event_name, _on_geometry_change)
