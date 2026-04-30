"""SQLAlchemy event listeners that mark AVL geometry files as dirty
when the airplane's wing or fuselage geometry changes."""

from __future__ import annotations

import logging

from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import FuselageModel, WingModel, WingXSecModel
from app.models.avl_geometry_file import AvlGeometryFileModel

logger = logging.getLogger(__name__)

_GEOMETRY_MODELS = (WingModel, WingXSecModel, FuselageModel)


def _mark_dirty(session: Session, aeroplane_id: int | None) -> None:
    if aeroplane_id is None:
        return
    session.execute(
        update(AvlGeometryFileModel)
        .where(AvlGeometryFileModel.aeroplane_id == aeroplane_id)
        .values(is_dirty=True)
    )


def _resolve_aeroplane_id(target) -> int | None:
    if isinstance(target, (WingModel, FuselageModel)):
        return target.aeroplane_id
    if isinstance(target, WingXSecModel) and target.wing is not None:
        return target.wing.aeroplane_id
    return None


def _on_geometry_change(mapper, connection, target):
    session = Session.object_session(target)
    if session is None:
        return
    aeroplane_id = _resolve_aeroplane_id(target)
    _mark_dirty(session, aeroplane_id)


for _model in _GEOMETRY_MODELS:
    for _event_name in ("after_insert", "after_update", "after_delete"):
        event.listen(_model, _event_name, _on_geometry_change)
