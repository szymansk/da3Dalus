"""Component Types service: CRUD + specs validation (gh#83).

Seeded types are non-deletable. User-added types are deletable only when
``reference_count=0`` (no components point at them). Specs validation is
tolerant — unknown keys are accepted; known keys are checked against
type/required/min/max/options rules.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    InternalError,
    NotFoundError,
    ValidationError,
)
from app.models.component import ComponentModel
from app.models.component_type import ComponentTypeModel
from app.schemas.component_type import (
    ComponentTypeRead,
    ComponentTypeWrite,
    PropertyDefinition,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _reference_count(db: Session, type_name: str) -> int:
    return (
        db.query(ComponentModel)
        .filter(ComponentModel.component_type == type_name)
        .count()
    )


def _to_schema(db: Session, m: ComponentTypeModel) -> ComponentTypeRead:
    return ComponentTypeRead.model_validate(
        {
            "id": m.id,
            "name": m.name,
            "label": m.label,
            "description": m.description,
            "schema": m.schema_def or [],
            "deletable": m.deletable,
            "reference_count": _reference_count(db, m.name),
            "created_at": m.created_at,
            "updated_at": m.updated_at,
        }
    )


def _get_or_404(db: Session, type_id: int) -> ComponentTypeModel:
    row = db.query(ComponentTypeModel).filter(ComponentTypeModel.id == type_id).first()
    if row is None:
        raise NotFoundError(entity="ComponentType", resource_id=type_id)
    return row


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #


def list_types(db: Session) -> list[ComponentTypeRead]:
    rows = db.query(ComponentTypeModel).order_by(ComponentTypeModel.label).all()
    return [_to_schema(db, r) for r in rows]


def get_type(db: Session, type_id: int) -> ComponentTypeRead:
    return _to_schema(db, _get_or_404(db, type_id))


def create_type(db: Session, data: ComponentTypeWrite) -> ComponentTypeRead:
    # Uniqueness check (lets us return 409 instead of 500 on integrity error)
    if db.query(ComponentTypeModel).filter(ComponentTypeModel.name == data.name).first():
        raise ConflictError(
            message=f"Type with name '{data.name}' already exists.",
            details={"name": data.name},
        )
    try:
        row = ComponentTypeModel(
            name=data.name,
            label=data.label,
            description=data.description,
            schema_def=[p.model_dump() for p in data.schema],
            deletable=True,  # user-created types are always deletable
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _to_schema(db, row)
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(message=f"Name conflict: {exc}") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in create_type: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def update_type(
    db: Session, type_id: int, data: ComponentTypeWrite
) -> ComponentTypeRead:
    """Update label / description / schema. Name and deletable are immutable."""
    try:
        row = _get_or_404(db, type_id)
        row.label = data.label
        row.description = data.description
        row.schema_def = [p.model_dump() for p in data.schema]
        # name and deletable stay untouched
        db.commit()
        db.refresh(row)
        return _to_schema(db, row)
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in update_type: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def delete_type(db: Session, type_id: int) -> None:
    row = _get_or_404(db, type_id)
    if not row.deletable:
        raise ConflictError(
            message=f"Type '{row.name}' is seeded and cannot be deleted.",
            details={"name": row.name, "reason": "seeded"},
        )
    refs = _reference_count(db, row.name)
    if refs > 0:
        raise ConflictError(
            message=(
                f"Type '{row.name}' is referenced by {refs} component(s) — "
                "cannot delete. Remove those components first or change their type."
            ),
            details={"name": row.name, "reference_count": refs, "reason": "referenced"},
        )
    try:
        db.delete(row)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("DB error in delete_type: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


# --------------------------------------------------------------------------- #
# Specs validation (consumed by component_service)
# --------------------------------------------------------------------------- #


def validate_specs(
    db: Session, component_type_name: str, specs: dict[str, Any]
) -> None:
    """Raise ValidationError if specs don't match the type's schema.

    Tolerant mode: unknown keys are ignored. Known keys are checked for:
      - presence (required)
      - type (number → isinstance(float/int), enum → in options, boolean → bool)
      - range (number → min/max)
    """
    row = (
        db.query(ComponentTypeModel)
        .filter(ComponentTypeModel.name == component_type_name)
        .first()
    )
    if row is None:
        raise ValidationError(
            message=f"Unknown component_type '{component_type_name}'. "
                    "Use GET /component-types to discover available types.",
            details={"component_type": component_type_name},
        )

    for raw in row.schema_def or []:
        prop = PropertyDefinition.model_validate(raw)
        value = specs.get(prop.name, None)

        if value is None:
            if prop.required:
                raise ValidationError(
                    message=f"Required property '{prop.name}' is missing.",
                    details={"property": prop.name, "reason": "missing_required"},
                )
            continue

        if prop.type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValidationError(
                    message=f"Property '{prop.name}' must be a number.",
                    details={"property": prop.name, "type": "number", "value": value},
                )
            if prop.min is not None and value < prop.min:
                raise ValidationError(
                    message=(
                        f"Property '{prop.name}' is below the allowed minimum "
                        f"{prop.min} (got {value})."
                    ),
                    details={"property": prop.name, "min": prop.min, "value": value},
                )
            if prop.max is not None and value > prop.max:
                raise ValidationError(
                    message=(
                        f"Property '{prop.name}' exceeds the allowed maximum "
                        f"{prop.max} (got {value})."
                    ),
                    details={"property": prop.name, "max": prop.max, "value": value},
                )
        elif prop.type == "string":
            if not isinstance(value, str):
                raise ValidationError(
                    message=f"Property '{prop.name}' must be a string.",
                    details={"property": prop.name, "type": "string", "value": value},
                )
        elif prop.type == "boolean":
            if not isinstance(value, bool):
                raise ValidationError(
                    message=f"Property '{prop.name}' must be true or false.",
                    details={"property": prop.name, "type": "boolean", "value": value},
                )
        elif prop.type == "enum":
            if prop.options and value not in prop.options:
                raise ValidationError(
                    message=(
                        f"Property '{prop.name}' value '{value}' is not allowed. "
                        f"Options: {prop.options}."
                    ),
                    details={
                        "property": prop.name,
                        "allowed": prop.options,
                        "value": value,
                    },
                )


def list_type_names(db: Session) -> list[str]:
    """Return the names of all registered types (for legacy /components/types)."""
    return [
        row[0]
        for row in db.query(ComponentTypeModel.name).order_by(ComponentTypeModel.label).all()
    ]


# --------------------------------------------------------------------------- #
# Seed — used both by the Alembic migration and by the test-DB fixture.
# Keep this list in sync with alembic/versions/28a13fbeac90_add_component_types
# _table_and_seed.py (the migration duplicates the data intentionally so that
# replaying old migrations isn't tied to the current application code).
# --------------------------------------------------------------------------- #

DEFAULT_SEED_TYPES: list[dict[str, Any]] = [
    {
        "name": "material",
        "label": "Material (3D-Druck)",
        "description": "3D-print material with density and print type",
        "schema": [
            {"name": "density_kg_m3", "label": "Dichte", "type": "number",
             "unit": "kg/m³", "required": True, "min": 100, "max": 20000},
            {"name": "print_resolution_mm", "label": "Druckauflösung", "type": "number",
             "unit": "mm", "min": 0.05, "max": 2.0, "default": 0.4},
            {"name": "print_type", "label": "Drucktyp", "type": "enum",
             "options": ["volume", "surface"], "default": "volume"},
        ],
    },
    {
        "name": "servo", "label": "Servo", "description": None,
        "schema": [
            {"name": "torque_kg_cm", "label": "Drehmoment", "type": "number", "unit": "kg·cm"},
            {"name": "speed_s_per_60deg", "label": "Geschwindigkeit", "type": "number", "unit": "s/60°"},
            {"name": "voltage_v", "label": "Spannung", "type": "number", "unit": "V"},
            {"name": "connector", "label": "Anschluss", "type": "enum",
             "options": ["jr", "futaba", "universal"]},
        ],
    },
    {
        "name": "brushless_motor", "label": "Brushless Motor", "description": None,
        "schema": [
            {"name": "kv_rpm_per_volt", "label": "KV", "type": "number", "unit": "RPM/V",
             "required": True},
            {"name": "max_current_a", "label": "Max Strom", "type": "number", "unit": "A"},
            {"name": "shaft_diameter_mm", "label": "Wellen-Ø", "type": "number", "unit": "mm"},
        ],
    },
    {
        "name": "battery", "label": "Battery", "description": None,
        "schema": [
            {"name": "capacity_mah", "label": "Kapazität", "type": "number", "unit": "mAh",
             "required": True, "min": 0},
            {"name": "cells", "label": "Zellen (S)", "type": "number", "required": True, "min": 1},
            {"name": "c_rate", "label": "C-Rate", "type": "number"},
            {"name": "voltage_v", "label": "Spannung", "type": "number", "unit": "V"},
        ],
    },
    {
        "name": "esc", "label": "ESC", "description": None,
        "schema": [
            {"name": "max_current_a", "label": "Max Strom", "type": "number", "unit": "A",
             "required": True},
            {"name": "cells", "label": "Zellen (S)", "type": "number"},
            {"name": "bec_voltage_v", "label": "BEC Spannung", "type": "number", "unit": "V"},
            {"name": "bec_current_a", "label": "BEC Strom", "type": "number", "unit": "A"},
            {"name": "protocol", "label": "Protokoll", "type": "enum",
             "options": ["pwm", "oneshot", "dshot150", "dshot300", "dshot600"]},
        ],
    },
    {
        "name": "propeller", "label": "Propeller", "description": None,
        "schema": [
            {"name": "diameter_in", "label": "Durchmesser", "type": "number", "unit": "inch",
             "required": True},
            {"name": "pitch_in", "label": "Steigung", "type": "number", "unit": "inch",
             "required": True},
            {"name": "blades", "label": "Blätter", "type": "number", "required": True, "min": 2},
            {"name": "material", "label": "Material", "type": "string"},
        ],
    },
    {
        "name": "receiver", "label": "Receiver", "description": None,
        "schema": [
            {"name": "channels", "label": "Kanäle", "type": "number"},
            {"name": "protocol", "label": "Protokoll", "type": "string"},
        ],
    },
    {
        "name": "flight_controller", "label": "Flight Controller", "description": None,
        "schema": [
            {"name": "firmware", "label": "Firmware", "type": "string"},
            {"name": "mcu", "label": "MCU", "type": "string"},
        ],
    },
    {
        "name": "generic", "label": "Generic",
        "description": "Free-form type with no structured schema",
        "schema": [],
    },
]


def seed_default_types(db: Session) -> None:
    """Insert the 9 default types if they aren't already present.

    Idempotent — safe to call multiple times (used by the test DB fixture).
    Seeded types carry deletable=False so users cannot remove them.
    """
    existing = {row[0] for row in db.query(ComponentTypeModel.name).all()}
    for seed in DEFAULT_SEED_TYPES:
        if seed["name"] in existing:
            continue
        db.add(
            ComponentTypeModel(
                name=seed["name"],
                label=seed["label"],
                description=seed["description"],
                schema_def=seed["schema"],
                deletable=False,
            )
        )
    db.commit()
