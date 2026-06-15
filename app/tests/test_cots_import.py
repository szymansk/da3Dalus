"""Tests for app.services.cots_import (gh-986).

All tests run against in-memory SQLite — no network, no real DB required.
The snapshot is provided as inline Python dicts (no PDFs needed in CI).
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.services.cots_import import ImportResult, _validate_record, import_snapshot


# ──────────────────────────────────────────────────────────────────────────────
# In-memory DB fixture
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def session() -> Session:
    """Fresh in-memory SQLite session per test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SM = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    db = SM()
    yield db
    db.close()


# ──────────────────────────────────────────────────────────────────────────────
# Fixture records
# ──────────────────────────────────────────────────────────────────────────────

MOTOR_RECORD = {
    "manufacturer": "D-Power",
    "name": "AL 42-06",
    "component_type": "brushless_motor",
    "mass_g": 199,
    "bbox_x_mm": 42,
    "bbox_y_mm": 42,
    "bbox_z_mm": 40,
    "model_ref": "dpower/al-42-06",
    "source_url": "https://www.d-power-modellbau.com/brushless-motor-al-serie",
    "source_version": "AL manual V3",
    "specs": {
        "kv_rpm_per_volt": 540,
        "io_no_load_a": 1.5,
        "continuous_current_a": 40.0,
        "max_current_a": 45.0,
        "cells_lipo_min": 3,
        "cells_lipo_max": 6,
        "shaft_diameter_mm": 5.0,
        "static_thrust_g": 3500,
        "art_no": "AL4206",
    },
}

ESC_RECORD = {
    "manufacturer": "D-Power",
    "name": "AVICON 60A",
    "component_type": "esc",
    "mass_g": 50,
    "bbox_x_mm": 70,
    "bbox_y_mm": 34,
    "bbox_z_mm": 10,
    "model_ref": "dpower/avicon-60a",
    "source_url": "https://www.d-power-modellbau.com/avicon-regler",
    "source_version": "Avicon manual",
    "specs": {
        "continuous_current_a": 60.0,
        "max_current_a": 80.0,
        "cells_lipo_min": 2,
        "cells_lipo_max": 6,
        "bec_output": "5V/6V 8A",
        "art_no": "DPAC060",
    },
}

INVALID_RECORD_NO_TYPE = {
    "manufacturer": "D-Power",
    "name": "Ghost Motor",
    "specs": {"kv_rpm_per_volt": 100},
}

INVALID_RECORD_BAD_TYPE = {
    "manufacturer": "D-Power",
    "name": "Ghost Motor",
    "component_type": "unknown_type",
    "specs": {},
}


# ──────────────────────────────────────────────────────────────────────────────
# _validate_record
# ──────────────────────────────────────────────────────────────────────────────


class TestValidateRecord:
    def test_valid_motor_returns_none(self):
        assert _validate_record(MOTOR_RECORD) is None

    def test_valid_esc_returns_none(self):
        assert _validate_record(ESC_RECORD) is None

    def test_missing_component_type_returns_error(self):
        assert _validate_record(INVALID_RECORD_NO_TYPE) is not None

    def test_unknown_component_type_returns_error(self):
        err = _validate_record(INVALID_RECORD_BAD_TYPE)
        assert err is not None
        assert "unknown_type" in err

    def test_missing_name_returns_error(self):
        r = {**MOTOR_RECORD, "name": ""}
        assert _validate_record(r) is not None

    def test_missing_manufacturer_returns_error(self):
        r = {**MOTOR_RECORD, "manufacturer": None}
        assert _validate_record(r) is not None


# ──────────────────────────────────────────────────────────────────────────────
# Happy path
# ──────────────────────────────────────────────────────────────────────────────


class TestImportSnapshotHappyPath:
    def test_single_motor_imported(self, session):
        result = import_snapshot(session, [MOTOR_RECORD])
        session.commit()

        assert result.imported == 1
        assert result.updated == 0
        assert result.skipped == 0
        assert result.errors == []

        row = session.query(ComponentModel).filter_by(name="AL 42-06").first()
        assert row is not None
        assert row.manufacturer == "D-Power"
        assert row.component_type == "brushless_motor"
        assert row.mass_g == 199
        assert row.specs["kv_rpm_per_volt"] == 540
        assert row.specs["io_no_load_a"] == 1.5
        assert row.specs["max_current_a"] == 45.0
        assert row.specs["art_no"] == "AL4206"

    def test_single_esc_imported(self, session):
        result = import_snapshot(session, [ESC_RECORD])
        session.commit()

        assert result.imported == 1
        row = session.query(ComponentModel).filter_by(name="AVICON 60A").first()
        assert row is not None
        assert row.mass_g == 50
        assert row.specs["continuous_current_a"] == 60.0
        assert row.specs["max_current_a"] == 80.0
        assert row.specs["bec_output"] == "5V/6V 8A"

    def test_motor_and_esc_imported_together(self, session):
        result = import_snapshot(session, [MOTOR_RECORD, ESC_RECORD])
        session.commit()

        assert result.imported == 2
        assert session.query(ComponentModel).count() == 2


# ──────────────────────────────────────────────────────────────────────────────
# Idempotency
# ──────────────────────────────────────────────────────────────────────────────


class TestImportSnapshotIdempotency:
    def test_run_twice_produces_no_duplicates(self, session):
        """Running the importer twice on the same snapshot must not duplicate rows."""
        import_snapshot(session, [MOTOR_RECORD, ESC_RECORD])
        session.commit()

        result2 = import_snapshot(session, [MOTOR_RECORD, ESC_RECORD])
        session.commit()

        assert result2.imported == 0
        assert result2.skipped == 2
        assert result2.errors == []
        assert session.query(ComponentModel).count() == 2

    def test_run_three_times_stays_idempotent(self, session):
        for _ in range(3):
            import_snapshot(session, [MOTOR_RECORD])
            session.commit()
        assert session.query(ComponentModel).count() == 1


# ──────────────────────────────────────────────────────────────────────────────
# Force update
# ──────────────────────────────────────────────────────────────────────────────


class TestImportSnapshotForceUpdate:
    def test_force_updates_existing_row(self, session):
        import_snapshot(session, [MOTOR_RECORD])
        session.commit()

        updated_record = {
            **MOTOR_RECORD,
            "mass_g": 210,  # changed
            "specs": {**MOTOR_RECORD["specs"], "kv_rpm_per_volt": 560},
        }
        result = import_snapshot(session, [updated_record], force=True)
        session.commit()

        assert result.updated == 1
        assert result.imported == 0
        row = session.query(ComponentModel).filter_by(name="AL 42-06").first()
        assert row.mass_g == 210
        assert row.specs["kv_rpm_per_volt"] == 560

    def test_without_force_does_not_update_unchanged(self, session):
        import_snapshot(session, [MOTOR_RECORD])
        session.commit()

        # Same data, no force → skipped
        result = import_snapshot(session, [MOTOR_RECORD], force=False)
        assert result.skipped == 1
        assert result.updated == 0

    def test_without_force_updates_changed_data(self, session):
        import_snapshot(session, [MOTOR_RECORD])
        session.commit()

        changed = {**MOTOR_RECORD, "mass_g": 999}
        result = import_snapshot(session, [changed], force=False)
        session.commit()

        assert result.updated == 1
        row = session.query(ComponentModel).filter_by(name="AL 42-06").first()
        assert row.mass_g == 999


# ──────────────────────────────────────────────────────────────────────────────
# Validation failures
# ──────────────────────────────────────────────────────────────────────────────


class TestImportSnapshotValidationFailure:
    def test_invalid_record_goes_to_errors(self, session):
        result = import_snapshot(session, [INVALID_RECORD_NO_TYPE])
        assert result.errors == ["Record 'Ghost Motor': Missing required field 'component_type'"]
        assert result.imported == 0

    def test_valid_records_committed_even_when_some_are_invalid(self, session):
        """Valid records should be imported; invalid ones collected into errors."""
        records = [MOTOR_RECORD, INVALID_RECORD_BAD_TYPE, ESC_RECORD]
        result = import_snapshot(session, records)
        session.commit()

        assert result.imported == 2
        assert len(result.errors) == 1
        assert session.query(ComponentModel).count() == 2

    def test_unknown_type_produces_error_string(self, session):
        result = import_snapshot(session, [INVALID_RECORD_BAD_TYPE])
        assert len(result.errors) == 1
        assert "unknown_type" in result.errors[0]


# ──────────────────────────────────────────────────────────────────────────────
# ImportResult __str__
# ──────────────────────────────────────────────────────────────────────────────


class TestImportResult:
    def test_str_format(self):
        r = ImportResult(imported=3, updated=1, skipped=5)
        s = str(r)
        assert "imported=3" in s
        assert "updated=1" in s
        assert "skipped=5" in s
        assert "errors=0" in s
