"""Tests for the canonical ESC registry schema (gh-1009).

Verifies:
- DEFAULT_SEED_TYPES['esc'] has exactly the 19 canonical English-label fields.
- Removed fields (cells, bec_voltage_v, bec_output) are absent from the schema.
- validate_specs accepts new fields and rejects wrong types.
- English-only labels (no German words).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import (
    DEFAULT_SEED_TYPES,
    seed_default_types,
    validate_specs,
)
from app.core.exceptions import ValidationError


# ──────────────────────────────────────────────────────────────────────────────
# In-memory DB fixture seeded with the current DEFAULT_SEED_TYPES
# ──────────────────────────────────────────────────────────────────────────────

CANONICAL_ESC_FIELDS = [
    "continuous_current_a",
    "max_current_a",
    "cells_lipo_min",
    "cells_lipo_max",
    "cells_nixx_min",
    "cells_nixx_max",
    "cells_liion_min",
    "cells_liion_max",
    "bec_voltage_5v",
    "bec_voltage_5_5v",
    "bec_voltage_6v",
    "bec_voltage_6_5v",
    "bec_voltage_7_4v",
    "bec_voltage_8_4v",
    "bec_voltage_9v",
    "bec_voltage_12v",
    "bec_current_a",
    "protocol",
    "art_no",
]

REMOVED_FIELDS = ["cells", "bec_voltage_v", "bec_output"]

GERMAN_WORDS = [
    "Zellen",
    "Spannung",
    "Strom",
    "Ausgang",
    "Protokoll",
    "Dauerstrom",
    "Strom",
    "kurz",
    "Nr.",
]


@pytest.fixture()
def seeded_db() -> Session:
    """Fresh in-memory SQLite session seeded with DEFAULT_SEED_TYPES."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SM = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    db = SM()
    seed_default_types(db)
    db.commit()
    yield db
    db.close()


def _esc_seed() -> dict:
    """Return the 'esc' entry from DEFAULT_SEED_TYPES."""
    return next(s for s in DEFAULT_SEED_TYPES if s["name"] == "esc")


def _esc_field_names() -> list[str]:
    return [f["name"] for f in _esc_seed()["schema"]]


class TestEscRegistrySchema:
    def test_esc_seed_has_canonical_field_list(self):
        """DEFAULT_SEED_TYPES['esc'] must have exactly the 19 canonical fields."""
        names = _esc_field_names()
        assert set(names) == set(CANONICAL_ESC_FIELDS), (
            f"Missing: {set(CANONICAL_ESC_FIELDS) - set(names)}, "
            f"Extra: {set(names) - set(CANONICAL_ESC_FIELDS)}"
        )
        assert len(names) == 19, f"Expected 19 fields, got {len(names)}"

    def test_esc_seed_does_not_contain_removed_fields(self):
        """cells, bec_voltage_v, bec_output must be absent from the schema."""
        names = set(_esc_field_names())
        for removed in REMOVED_FIELDS:
            assert removed not in names, f"Removed field '{removed}' still in schema"

    def test_esc_seed_max_current_a_is_required(self):
        """max_current_a must carry required=True."""
        fields = {f["name"]: f for f in _esc_seed()["schema"]}
        assert fields["max_current_a"].get("required") is True

    def test_esc_seed_protocol_options_unchanged(self):
        """Protocol options must remain exactly the five DShot / PWM variants."""
        fields = {f["name"]: f for f in _esc_seed()["schema"]}
        assert fields["protocol"]["options"] == [
            "pwm",
            "oneshot",
            "dshot150",
            "dshot300",
            "dshot600",
        ]

    def test_esc_seed_bec_voltage_fields_are_boolean_type(self):
        """All eight bec_voltage_* fields must declare type='boolean'."""
        bec_fields = [f for f in _esc_seed()["schema"] if f["name"].startswith("bec_voltage_")]
        assert len(bec_fields) == 8, f"Expected 8 bec_voltage_* fields, got {len(bec_fields)}"
        for f in bec_fields:
            assert f["type"] == "boolean", f"{f['name']} has type={f['type']!r}, expected 'boolean'"

    def test_validate_specs_accepts_new_esc_fields(self, seeded_db):
        """validate_specs must accept the new canonical fields without raising."""
        validate_specs(
            seeded_db,
            "esc",
            {
                "max_current_a": 30,
                "bec_voltage_5v": True,
                "cells_nixx_min": 5,
                "cells_nixx_max": 12,
            },
        )
        # If no exception is raised, the test passes.

    def test_validate_specs_rejects_boolean_as_number(self, seeded_db):
        """bec_voltage_5v must be rejected when passed as integer 1 (not bool)."""
        with pytest.raises(ValidationError):
            validate_specs(
                seeded_db,
                "esc",
                {"max_current_a": 30, "bec_voltage_5v": 1},
            )

    def test_validate_specs_requires_max_current_a(self, seeded_db):
        """validate_specs must raise ValidationError when max_current_a is missing."""
        with pytest.raises(ValidationError):
            validate_specs(seeded_db, "esc", {})

    def test_validate_specs_old_bec_output_field_not_in_schema(self, seeded_db):
        """bec_output is an unknown key — unknown keys are tolerated (not in schema list)."""
        # Confirm it is NOT in the schema definition
        row = seeded_db.query(ComponentTypeModel).filter_by(name="esc").first()
        field_names = [f["name"] for f in row.schema_def]
        assert "bec_output" not in field_names

    def test_validate_specs_old_cells_field_not_in_schema(self, seeded_db):
        """cells is an unknown key — confirm it is NOT in the schema definition."""
        row = seeded_db.query(ComponentTypeModel).filter_by(name="esc").first()
        field_names = [f["name"] for f in row.schema_def]
        assert "cells" not in field_names

    def test_esc_labels_are_english(self):
        """All field .label values must contain no German words."""
        fields = _esc_seed()["schema"]
        for f in fields:
            label = f.get("label", "")
            for german in GERMAN_WORDS:
                assert german not in label, (
                    f"Field '{f['name']}' label '{label}' contains German word '{german}'"
                )
