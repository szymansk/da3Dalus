"""Tests for the gh-1008 structural-material seeding and material-type
schema patching in component_type_service.

Covers:
- seed_structural_materials: Pine + Carbon Fiber seeded with the expected
  structural specs, and idempotency (no duplicates on re-seed).
- _patch_material_structural_fields: adds the structural fields to an
  existing 'material' type that predates gh-1008, is idempotent, and is a
  no-op when no 'material' type exists.
"""

from __future__ import annotations

import pytest

from app.models.component import ComponentModel
from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import (
    _patch_material_structural_fields,
    seed_default_types,
    seed_structural_materials,
)

pytestmark = pytest.mark.integration

_STRUCTURAL_FIELDS = {"allowable_bending_stress_mpa", "youngs_modulus_gpa"}


def _materials(db):
    return (
        db.query(ComponentModel)
        .filter(ComponentModel.component_type == "material")
        .all()
    )


def test_structural_materials_seeded_with_specs(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        names = {m.name for m in _materials(db)}
        assert "Pine (structural)" in names
        assert "Carbon Fiber (structural)" in names

        cf = next(m for m in _materials(db) if m.name == "Carbon Fiber (structural)")
        assert cf.specs["allowable_bending_stress_mpa"] == 500.0
        assert cf.specs["youngs_modulus_gpa"] == 120.0
        assert cf.specs["density_kg_m3"] == 1600.0
    finally:
        db.close()


def test_seed_structural_materials_is_idempotent(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        before = len(_materials(db))
        # conftest already seeded once; seeding again must not duplicate.
        seed_structural_materials(db)
        db.commit()
        assert len(_materials(db)) == before
    finally:
        db.close()


def test_material_type_has_structural_fields(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = (
            db.query(ComponentTypeModel)
            .filter(ComponentTypeModel.name == "material")
            .first()
        )
        names = {p["name"] for p in row.schema_def if isinstance(p, dict)}
        assert _STRUCTURAL_FIELDS.issubset(names)
    finally:
        db.close()


def test_patch_adds_missing_structural_fields_to_legacy_material_type(client_and_db):
    """Simulate a pre-gh-1008 DB whose material type lacks the new fields."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = (
            db.query(ComponentTypeModel)
            .filter(ComponentTypeModel.name == "material")
            .first()
        )
        full_schema = list(row.schema_def)
        # Strip the gh-1008 fields to mimic a legacy schema.
        legacy = [
            p
            for p in full_schema
            if not (isinstance(p, dict) and p.get("name") in _STRUCTURAL_FIELDS)
        ]
        row.schema_def = legacy
        db.flush()
        assert not _STRUCTURAL_FIELDS.issubset(
            {p["name"] for p in row.schema_def if isinstance(p, dict)}
        )

        # Patch should re-add them (changed=True branch).
        _patch_material_structural_fields(db, full_schema)
        db.commit()

        row2 = (
            db.query(ComponentTypeModel)
            .filter(ComponentTypeModel.name == "material")
            .first()
        )
        names = {p["name"] for p in row2.schema_def if isinstance(p, dict)}
        assert _STRUCTURAL_FIELDS.issubset(names)
    finally:
        db.close()


def test_reseed_default_types_patches_existing_material_type(client_and_db):
    """Re-running seed_default_types on a DB that already has the types must
    hit the 'already exists' branch and keep the material structural fields."""
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        type_count_before = db.query(ComponentTypeModel).count()
        seed_default_types(db)  # second call → exercises the patch-on-existing path
        db.commit()
        # No duplicate types created.
        assert db.query(ComponentTypeModel).count() == type_count_before
        row = (
            db.query(ComponentTypeModel)
            .filter(ComponentTypeModel.name == "material")
            .first()
        )
        names = {p["name"] for p in row.schema_def if isinstance(p, dict)}
        assert _STRUCTURAL_FIELDS.issubset(names)
    finally:
        db.close()


def test_patch_is_noop_when_no_material_type(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        db.query(ComponentTypeModel).filter(
            ComponentTypeModel.name == "material"
        ).delete()
        db.flush()
        # Must return cleanly without raising when there is no material type.
        _patch_material_structural_fields(db, [{"name": "youngs_modulus_gpa"}])
    finally:
        db.close()
