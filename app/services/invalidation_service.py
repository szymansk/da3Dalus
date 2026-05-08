"""Invalidation service — subscribes to domain events and marks dependent OPs as DIRTY."""

from __future__ import annotations

import logging

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.events import AssumptionChanged, GeometryChanged, event_bus
from app.models.analysismodels import OperatingPointModel

logger = logging.getLogger(__name__)

# Assumption parameters that affect operating points
_OP_AFFECTING_PARAMS = {"mass", "cg_x"}


def _on_geometry_changed(event: GeometryChanged) -> None:
    """Log GeometryChanged events. Actual DB work is done in SQLAlchemy listeners."""
    logger.info(
        "GeometryChanged for aeroplane %d (source: %s) — OPs will be marked DIRTY",
        event.aeroplane_id,
        event.source_model,
    )


def _on_assumption_changed(event: AssumptionChanged) -> None:
    """Log AssumptionChanged events when the parameter affects trim."""
    if event.parameter_name in _OP_AFFECTING_PARAMS:
        logger.info(
            "AssumptionChanged(%s) for aeroplane %d — OPs will be marked DIRTY",
            event.parameter_name,
            event.aeroplane_id,
        )


def mark_ops_dirty(session: Session, aeroplane_id: int) -> int:
    """Mark all operating points for an aeroplane as DIRTY. Returns count updated."""
    result = session.execute(
        update(OperatingPointModel)
        .where(
            OperatingPointModel.aircraft_id == aeroplane_id,
            OperatingPointModel.status.notin_(["DIRTY", "COMPUTING"]),
        )
        .values(status="DIRTY")
    )
    return result.rowcount


def register_handlers() -> None:
    """Register event handlers on the global event bus."""
    event_bus.subscribe(GeometryChanged, _on_geometry_changed)
    event_bus.subscribe(AssumptionChanged, _on_assumption_changed)
