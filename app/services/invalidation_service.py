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

# Assumption parameters that are inputs to the geometry-driven recompute
# (changing them must re-derive cl_max/cd0/cg_x). cg_x itself is excluded
# to prevent the recompute → AssumptionChanged(cg_x) → recompute loop.
_RECOMPUTE_TRIGGERING_PARAMS = {"target_static_margin"}


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


def _on_geometry_changed(event: GeometryChanged) -> None:
    """Log GeometryChanged events and schedule background retrim."""
    logger.info(
        "GeometryChanged for aeroplane %d (source: %s) — OPs marked DIRTY",
        event.aeroplane_id,
        event.source_model,
    )
    from app.core.background_jobs import job_tracker

    job_tracker.schedule_retrim(event.aeroplane_id)


def _on_geometry_changed_recompute_assumptions(event: GeometryChanged) -> None:
    """Handler that schedules a debounced assumption recompute."""
    logger.info(
        "GeometryChanged for aeroplane %d (source: %s) — scheduling assumption recompute",
        event.aeroplane_id,
        event.source_model,
    )
    from app.core.background_jobs import job_tracker

    job_tracker.schedule_recompute_assumptions(event.aeroplane_id)


def _on_assumption_changed(event: AssumptionChanged) -> None:
    """Schedule retrim when an OP-affecting assumption changes."""
    if event.parameter_name in _OP_AFFECTING_PARAMS:
        logger.info(
            "AssumptionChanged(%s) for aeroplane %d — OPs marked DIRTY, retrim scheduled",
            event.parameter_name,
            event.aeroplane_id,
        )
        from app.core.background_jobs import job_tracker

        job_tracker.schedule_retrim(event.aeroplane_id)


def _on_assumption_changed_recompute(event: AssumptionChanged) -> None:
    """Schedule recompute when a recompute-input assumption changes.

    Currently only target_static_margin — it is a factor in the cg_x
    formula (cg_x = x_np - SM × MAC), so changing it must re-derive cg_x.
    """
    if event.parameter_name in _RECOMPUTE_TRIGGERING_PARAMS:
        logger.info(
            "AssumptionChanged(%s) for aeroplane %d — scheduling assumption recompute",
            event.parameter_name,
            event.aeroplane_id,
        )
        from app.core.background_jobs import job_tracker

        job_tracker.schedule_recompute_assumptions(event.aeroplane_id)


def register_handlers() -> None:
    """Register event handlers on the global event bus."""
    event_bus.subscribe(GeometryChanged, _on_geometry_changed)
    event_bus.subscribe(GeometryChanged, _on_geometry_changed_recompute_assumptions)
    event_bus.subscribe(AssumptionChanged, _on_assumption_changed)
    event_bus.subscribe(AssumptionChanged, _on_assumption_changed_recompute)
