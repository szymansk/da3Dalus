"""Tests for the gh-1006 brushless_motor rm_ohm schema field + additive patch.

Covers:
- The seeded brushless_motor ComponentType carries the rm_ohm field.
- _patch_schema_fields additively rolls rm_ohm onto a legacy (pre-gh-1006)
  brushless_motor schema, is idempotent, and never removes existing fields.
- Re-running seed_default_types on an existing DB patches in rm_ohm.
"""

from __future__ import annotations

import pytest

from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import (
    _patch_schema_fields,
    seed_default_types,
)

pytestmark = pytest.mark.integration


def _motor_type(db):
    return db.query(ComponentTypeModel).filter(ComponentTypeModel.name == "brushless_motor").first()


def _field_names(row) -> set:
    return {p["name"] for p in row.schema_def if isinstance(p, dict)}


def test_brushless_motor_type_has_rm_ohm(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = _motor_type(db)
        assert row is not None
        assert "rm_ohm" in _field_names(row)
        rm = next(p for p in row.schema_def if p.get("name") == "rm_ohm")
        assert rm["type"] == "number"
        assert rm["unit"] == "Ω"
    finally:
        db.close()


def test_patch_adds_rm_ohm_to_legacy_motor_type(client_and_db):
    """Simulate a pre-gh-1006 DB whose brushless_motor type lacks rm_ohm."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = _motor_type(db)
        full_schema = list(row.schema_def)
        legacy = [p for p in full_schema if not (isinstance(p, dict) and p.get("name") == "rm_ohm")]
        row.schema_def = legacy
        db.flush()
        assert "rm_ohm" not in _field_names(row)

        _patch_schema_fields(db, "brushless_motor", full_schema)
        db.commit()

        assert "rm_ohm" in _field_names(_motor_type(db))
    finally:
        db.close()


def test_patch_is_idempotent_and_preserves_fields(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = _motor_type(db)
        before = list(_field_names(row))
        full_schema = list(row.schema_def)

        _patch_schema_fields(db, "brushless_motor", full_schema)
        db.commit()

        after = _field_names(_motor_type(db))
        # No duplicates, no removed fields.
        assert set(before) == after
    finally:
        db.close()


def test_reseed_default_types_patches_existing_motor_type(client_and_db):
    """Re-running seed_default_types must patch rm_ohm onto an existing type."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = _motor_type(db)
        row.schema_def = [
            p for p in row.schema_def if not (isinstance(p, dict) and p.get("name") == "rm_ohm")
        ]
        db.flush()
        assert "rm_ohm" not in _field_names(_motor_type(db))

        seed_default_types(db)
        db.commit()

        assert "rm_ohm" in _field_names(_motor_type(db))
    finally:
        db.close()
