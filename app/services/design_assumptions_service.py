"""Design Assumptions Service — CRUD for per-aeroplane design assumptions."""

from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.schemas.design_assumption import (
    DESIGN_CHOICE_PARAMS,
    PARAMETER_DEFAULTS,
    PARAMETER_UNITS,
    AssumptionRead,
    AssumptionSourceSwitch,
    AssumptionWrite,
    AssumptionsSummary,
    compute_divergence_pct,
    divergence_level,
)

logger = logging.getLogger(__name__)


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    """Resolve an aeroplane by UUID, raising NotFoundError when missing."""
    aeroplane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _assumption_to_read(model: DesignAssumptionModel) -> AssumptionRead:
    """Convert an ORM model instance to an AssumptionRead schema."""
    if model.active_source == "CALCULATED" and model.calculated_value is not None:
        effective_value = model.calculated_value
    else:
        effective_value = model.estimate_value

    div_level = divergence_level(model.divergence_pct)
    unit = PARAMETER_UNITS.get(model.parameter_name, "")
    is_design_choice = model.parameter_name in DESIGN_CHOICE_PARAMS

    return AssumptionRead(
        id=model.id,
        parameter_name=model.parameter_name,
        estimate_value=model.estimate_value,
        calculated_value=model.calculated_value,
        calculated_source=model.calculated_source,
        active_source=model.active_source,
        effective_value=effective_value,
        divergence_pct=model.divergence_pct,
        divergence_level=div_level,
        unit=unit,
        is_design_choice=is_design_choice,
        updated_at=model.updated_at,
    )


def seed_defaults(db: Session, aeroplane_uuid) -> AssumptionsSummary:
    """Create default assumptions for an aeroplane if they don't exist yet."""
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        existing = (
            db.query(DesignAssumptionModel.parameter_name)
            .filter(DesignAssumptionModel.aeroplane_id == aeroplane.id)
            .all()
        )
        existing_names = {row[0] for row in existing}

        for param_name, default_value in PARAMETER_DEFAULTS.items():
            if param_name not in existing_names:
                row = DesignAssumptionModel(
                    aeroplane_id=aeroplane.id,
                    parameter_name=param_name,
                    estimate_value=default_value,
                    active_source="ESTIMATE",
                )
                db.add(row)

        db.flush()
        return list_assumptions(db, aeroplane_uuid)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in seed_defaults: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def list_assumptions(db: Session, aeroplane_uuid) -> AssumptionsSummary:
    """List all design assumptions for an aeroplane."""
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    rows = (
        db.query(DesignAssumptionModel)
        .filter(DesignAssumptionModel.aeroplane_id == aeroplane.id)
        .all()
    )
    assumptions = [_assumption_to_read(r) for r in rows]
    warnings_count = sum(1 for a in assumptions if a.divergence_level in ("warning", "alert"))
    return AssumptionsSummary(assumptions=assumptions, warnings_count=warnings_count)


def update_assumption(
    db: Session, aeroplane_uuid, param_name: str, data: AssumptionWrite
) -> AssumptionRead:
    """Update the estimate value of a design assumption."""
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        row = (
            db.query(DesignAssumptionModel)
            .filter(
                DesignAssumptionModel.aeroplane_id == aeroplane.id,
                DesignAssumptionModel.parameter_name == param_name,
            )
            .first()
        )
        if row is None:
            raise NotFoundError(entity="DesignAssumption", resource_id=param_name)

        row.estimate_value = data.estimate_value
        row.divergence_pct = compute_divergence_pct(data.estimate_value, row.calculated_value)
        db.flush()
        db.refresh(row)
        return _assumption_to_read(row)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in update_assumption: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def switch_source(
    db: Session, aeroplane_uuid, param_name: str, data: AssumptionSourceSwitch
) -> AssumptionRead:
    """Switch the active source for a design assumption."""
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        row = (
            db.query(DesignAssumptionModel)
            .filter(
                DesignAssumptionModel.aeroplane_id == aeroplane.id,
                DesignAssumptionModel.parameter_name == param_name,
            )
            .first()
        )
        if row is None:
            raise NotFoundError(entity="DesignAssumption", resource_id=param_name)

        if data.active_source == "CALCULATED":
            if param_name in DESIGN_CHOICE_PARAMS:
                raise ValidationError(
                    message=f"Parameter '{param_name}' is a design choice and cannot use CALCULATED source"
                )
            if row.calculated_value is None:
                raise ValidationError(message=f"No calculated value available for '{param_name}'")

        row.active_source = data.active_source
        db.flush()
        db.refresh(row)
        return _assumption_to_read(row)
    except (NotFoundError, ValidationError):
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in switch_source: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc
