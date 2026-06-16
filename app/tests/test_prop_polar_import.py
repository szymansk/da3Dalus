"""Tests for app.services.prop_polar_import (gh-995, gh-999).

All tests run against in-memory SQLite — no network, no real DB required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.db.base import Base
from app.models.prop_polar import PropellerPolarModel, PropellerPolarSampleModel
from app.services.prop_polar_import import (
    ImportResult,
    _validate_prop_record,
    import_prop_polars,
    load_snapshot,
)


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
# Fixture records (inline — no file I/O in tests)
# ──────────────────────────────────────────────────────────────────────────────

SAMPLE_POLAR_RECORD = {
    "manufacturer": "APC",
    "name": "APC 9x6",
    "component_type": "propeller",
    "model_ref": "apc/9x6",
    "source_url": "https://www.apcprop.com/files/PER3_9x6.dat",
    "source_version": "v2022-0915",
    "specs": {
        "diameter_in": 9.0,
        "pitch_in": 6.0,
        "variant": "",
        "blades": 2,
    },
    "polars": [
        {
            "rpm": 3000,
            "samples": [
                {
                    "J": 0.0,
                    "Ct": 0.1284,
                    "Cp": 0.0531,
                    "Pe": 0.0,
                    "PWR_W": 12.1,
                    "Torque_Nm": 0.020,
                    "Thrust_N": 1.743,
                },
                {
                    "J": 0.1091,
                    "Ct": 0.1166,
                    "Cp": 0.0514,
                    "Pe": 0.2472,
                    "PWR_W": 11.7,
                    "Torque_Nm": 0.019,
                    "Thrust_N": 1.582,
                },
                {
                    "J": 0.2727,
                    "Ct": 0.0930,
                    "Cp": 0.0499,
                    "Pe": 0.5072,
                    "PWR_W": 11.4,
                    "Torque_Nm": 0.019,
                    "Thrust_N": 1.262,
                },
                {
                    "J": 0.4363,
                    "Ct": 0.0645,
                    "Cp": 0.0458,
                    "Pe": 0.6145,
                    "PWR_W": 10.4,
                    "Torque_Nm": 0.017,
                    "Thrust_N": 0.876,
                },
                {
                    "J": 0.6000,
                    "Ct": 0.0341,
                    "Cp": 0.0393,
                    "Pe": 0.5193,
                    "PWR_W": 9.0,
                    "Torque_Nm": 0.015,
                    "Thrust_N": 0.463,
                },
            ],
        },
        {
            "rpm": 5000,
            "samples": [
                {
                    "J": 0.0,
                    "Ct": 0.1341,
                    "Cp": 0.0535,
                    "Pe": 0.0,
                    "PWR_W": 53.7,
                    "Torque_Nm": 0.055,
                    "Thrust_N": 4.860,
                },
                {
                    "J": 0.1453,
                    "Ct": 0.1155,
                    "Cp": 0.0510,
                    "Pe": 0.3390,
                    "PWR_W": 51.5,
                    "Torque_Nm": 0.052,
                    "Thrust_N": 4.168,
                },
                {
                    "J": 0.4360,
                    "Ct": 0.0687,
                    "Cp": 0.0456,
                    "Pe": 0.6577,
                    "PWR_W": 46.1,
                    "Torque_Nm": 0.047,
                    "Thrust_N": 2.481,
                },
                {
                    "J": 0.7267,
                    "Ct": 0.0164,
                    "Cp": 0.0519,
                    "Pe": 0.2301,
                    "PWR_W": 71.2,
                    "Torque_Nm": 0.064,
                    "Thrust_N": 0.593,
                },
            ],
        },
    ],
}

SECOND_PROP_RECORD = {
    "manufacturer": "APC",
    "name": "APC 12x6",
    "component_type": "propeller",
    "model_ref": "apc/12x6",
    "source_url": "https://www.apcprop.com/files/PER3_12x6.dat",
    "source_version": "v2022-0915",
    "specs": {
        "diameter_in": 12.0,
        "pitch_in": 6.0,
        "variant": "",
        "blades": 2,
    },
    "polars": [
        {
            "rpm": 3000,
            "samples": [
                {
                    "J": 0.0,
                    "Ct": 0.1136,
                    "Cp": 0.0552,
                    "Pe": 0.0,
                    "PWR_W": 35.3,
                    "Torque_Nm": 0.059,
                    "Thrust_N": 5.090,
                },
                {
                    "J": 0.2181,
                    "Ct": 0.0902,
                    "Cp": 0.0525,
                    "Pe": 0.3981,
                    "PWR_W": 33.5,
                    "Torque_Nm": 0.057,
                    "Thrust_N": 4.039,
                },
                {
                    "J": 0.4363,
                    "Ct": 0.0597,
                    "Cp": 0.0425,
                    "Pe": 0.6127,
                    "PWR_W": 27.3,
                    "Torque_Nm": 0.046,
                    "Thrust_N": 2.674,
                },
                {
                    "J": 0.6544,
                    "Ct": 0.0272,
                    "Cp": 0.0344,
                    "Pe": 0.5166,
                    "PWR_W": 22.2,
                    "Torque_Nm": 0.037,
                    "Thrust_N": 1.218,
                },
            ],
        },
    ],
}

INVALID_MISSING_POLARS = {
    "manufacturer": "APC",
    "name": "APC 7x4",
    "component_type": "propeller",
    "model_ref": "apc/7x4",
    "source_url": "https://www.apcprop.com/files/PER3_7x4.dat",
    "source_version": "v2022-0915",
    "specs": {"diameter_in": 7.0, "pitch_in": 4.0, "blades": 2},
    "polars": [],  # No polars — should produce a warning but still import
}

INVALID_MISSING_NAME = {
    "manufacturer": "APC",
    "name": "",
    "component_type": "propeller",
    "model_ref": "apc/bad",
    "source_version": "v1",
    "specs": {"diameter_in": 9.0, "pitch_in": 6.0, "blades": 2},
    "polars": [],
}


# ──────────────────────────────────────────────────────────────────────────────
# _validate_prop_record
# ──────────────────────────────────────────────────────────────────────────────


class TestValidatePropRecord:
    def test_valid_record_returns_none(self):
        assert _validate_prop_record(SAMPLE_POLAR_RECORD) is None

    def test_missing_name_returns_error(self):
        err = _validate_prop_record(INVALID_MISSING_NAME)
        assert err is not None

    def test_missing_manufacturer_returns_error(self):
        r = {**SAMPLE_POLAR_RECORD, "manufacturer": ""}
        err = _validate_prop_record(r)
        assert err is not None

    def test_wrong_component_type_returns_error(self):
        r = {**SAMPLE_POLAR_RECORD, "component_type": "brushless_motor"}
        err = _validate_prop_record(r)
        assert err is not None


# ──────────────────────────────────────────────────────────────────────────────
# Happy path
# ──────────────────────────────────────────────────────────────────────────────


class TestImportPropPolarsHappyPath:
    def test_single_prop_imported(self, session):
        result = import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        assert result.imported == 1
        assert result.errors == []

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        assert prop is not None
        assert prop.manufacturer == "APC"
        assert prop.diameter_in == pytest.approx(9.0)
        assert prop.pitch_in == pytest.approx(6.0)
        assert prop.blades == 2

    def test_samples_stored(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        samples = session.query(PropellerPolarSampleModel).filter_by(propeller_id=prop.id).all()
        # 5 samples at 3000rpm + 4 at 5000rpm = 9
        assert len(samples) == 9

    def test_sample_values_correct(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        static_samples = (
            session.query(PropellerPolarSampleModel)
            .filter_by(propeller_id=prop.id, rpm=3000)
            .order_by(PropellerPolarSampleModel.J)
            .first()
        )
        assert static_samples is not None
        assert static_samples.J == pytest.approx(0.0, abs=1e-6)
        assert static_samples.Ct == pytest.approx(0.1284, rel=1e-3)
        assert static_samples.Cp == pytest.approx(0.0531, rel=1e-3)
        assert static_samples.Pe == pytest.approx(0.0, abs=1e-4)
        assert static_samples.Thrust_N == pytest.approx(1.743, rel=1e-2)

    def test_two_props_imported(self, session):
        result = import_prop_polars(session, [SAMPLE_POLAR_RECORD, SECOND_PROP_RECORD])
        session.commit()

        assert result.imported == 2
        assert session.query(PropellerPolarModel).count() == 2

    def test_source_version_stored(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        assert prop.source_version == "v2022-0915"

    def test_source_url_stored(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        assert "apcprop.com" in prop.source_url


# ──────────────────────────────────────────────────────────────────────────────
# Idempotency
# ──────────────────────────────────────────────────────────────────────────────


class TestImportPropPolarsIdempotency:
    def test_run_twice_no_duplicates(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        result2 = import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        assert result2.imported == 0
        assert result2.skipped == 1
        assert session.query(PropellerPolarModel).count() == 1
        # Samples must not double-up
        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        samples = session.query(PropellerPolarSampleModel).filter_by(propeller_id=prop.id).count()
        assert samples == 9  # still the original count

    def test_run_three_times_stays_idempotent(self, session):
        for _ in range(3):
            import_prop_polars(session, [SAMPLE_POLAR_RECORD])
            session.commit()
        assert session.query(PropellerPolarModel).count() == 1

    def test_force_updates_existing_row(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        updated = {**SAMPLE_POLAR_RECORD, "source_version": "v2023-0101"}
        result = import_prop_polars(session, [updated], force=True)
        session.commit()

        assert result.updated == 1
        assert result.imported == 0
        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        assert prop.source_version == "v2023-0101"

    def test_force_replaces_samples(self, session):
        """Force-update must clear old samples and insert new ones."""
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        # Create a version with only 1 RPM block instead of 2
        one_block = {
            **SAMPLE_POLAR_RECORD,
            "polars": [SAMPLE_POLAR_RECORD["polars"][0]],  # only 3000rpm block
        }
        import_prop_polars(session, [one_block], force=True)
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        samples = session.query(PropellerPolarSampleModel).filter_by(propeller_id=prop.id).count()
        assert samples == 5  # only the 3000rpm block (5 samples)


# ──────────────────────────────────────────────────────────────────────────────
# Validation failures
# ──────────────────────────────────────────────────────────────────────────────


class TestImportPropPolarsValidation:
    def test_invalid_name_goes_to_errors(self, session):
        result = import_prop_polars(session, [INVALID_MISSING_NAME])
        assert len(result.errors) == 1
        assert result.imported == 0

    def test_valid_records_still_imported_when_some_invalid(self, session):
        result = import_prop_polars(session, [SAMPLE_POLAR_RECORD, INVALID_MISSING_NAME])
        session.commit()

        assert result.imported == 1
        assert len(result.errors) == 1

    def test_empty_polars_list_imports_header(self, session):
        """A record with no polars still imports the propeller metadata row."""
        result = import_prop_polars(session, [INVALID_MISSING_POLARS])
        session.commit()

        assert result.imported == 1
        prop = session.query(PropellerPolarModel).filter_by(name="APC 7x4").first()
        assert prop is not None
        # No samples
        count = session.query(PropellerPolarSampleModel).filter_by(propeller_id=prop.id).count()
        assert count == 0


# ──────────────────────────────────────────────────────────────────────────────
# ImportResult
# ──────────────────────────────────────────────────────────────────────────────


class TestImportResult:
    def test_str_format(self):
        r = ImportResult(imported=5, updated=1, skipped=3)
        s = str(r)
        assert "imported=5" in s
        assert "updated=1" in s
        assert "skipped=3" in s


class TestRecordsEqual:
    """Test the _records_equal logic via import_prop_polars without force."""

    def test_same_source_version_skipped(self, session):
        """Same source_version → skip (no write)."""
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        # Same version → skip
        result = import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        assert result.skipped == 1

    def test_different_source_url_triggers_update(self, session):
        """Different source_url → update even without force."""
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        changed_url = {**SAMPLE_POLAR_RECORD, "source_url": "https://other.example.com/"}
        result = import_prop_polars(session, [changed_url])
        session.commit()
        assert result.updated == 1

    def test_different_source_version_triggers_update(self, session):
        """Different source_version → update without force."""
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        changed_ver = {**SAMPLE_POLAR_RECORD, "source_version": "v2024-0101"}
        result = import_prop_polars(session, [changed_ver])
        session.commit()
        assert result.updated == 1


# ──────────────────────────────────────────────────────────────────────────────
# Variant field (gh-999)
# ──────────────────────────────────────────────────────────────────────────────

VARIANT_E_RECORD = {
    "manufacturer": "APC",
    "name": "APC 10x10E",
    "component_type": "propeller",
    "model_ref": "apc/10x10E",
    "source_url": "https://www.apcprop.com/files/PER3_10x10E.dat",
    "source_version": "v2022-0915",
    "specs": {
        "diameter_in": 10.0,
        "pitch_in": 10.0,
        "variant": "E",
        "blades": 2,
    },
    "polars": [
        {
            "rpm": 5000,
            "samples": [
                {
                    "J": 0.0,
                    "Ct": 0.1200,
                    "Cp": 0.0500,
                    "Pe": 0.0,
                    "PWR_W": 100.0,
                    "Torque_Nm": 0.100,
                    "Thrust_N": 5.0,
                },
            ],
        }
    ],
}

DECIMAL_DIA_RECORD = {
    "manufacturer": "APC",
    "name": "APC 10.5x4.5",
    "component_type": "propeller",
    "model_ref": "apc/10p5x4p5",
    "source_url": "https://www.apcprop.com/files/PER3_105x45.dat",
    "source_version": "v2022-0915",
    "specs": {
        "diameter_in": 10.5,
        "pitch_in": 4.5,
        "variant": "",
        "blades": 2,
    },
    "polars": [
        {
            "rpm": 3000,
            "samples": [
                {
                    "J": 0.0,
                    "Ct": 0.0740,
                    "Cp": 0.0388,
                    "Pe": 0.0,
                    "PWR_W": 0.297,
                    "Torque_Nm": 0.003,
                    "Thrust_N": 0.127,
                },
            ],
        }
    ],
}


class TestVariantField:
    """Variant field is stored and retrieved correctly."""

    def test_variant_stored_for_E_prop(self, session):
        import_prop_polars(session, [VARIANT_E_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 10x10E").first()
        assert prop is not None
        assert prop.variant == "E"

    def test_variant_empty_for_plain_prop(self, session):
        import_prop_polars(session, [SAMPLE_POLAR_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 9x6").first()
        assert prop.variant == ""

    def test_decimal_diameter_stored_correctly(self, session):
        import_prop_polars(session, [DECIMAL_DIA_RECORD])
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 10.5x4.5").first()
        assert prop is not None
        assert prop.diameter_in == pytest.approx(10.5)
        assert prop.pitch_in == pytest.approx(4.5)

    def test_variant_updated_on_force(self, session):
        """Variant is updated when a record is force-reimported."""
        import_prop_polars(session, [VARIANT_E_RECORD])
        session.commit()

        updated = {**VARIANT_E_RECORD, "specs": {**VARIANT_E_RECORD["specs"], "variant": "E-3"}}
        import_prop_polars(session, [updated], force=True)
        session.commit()

        prop = session.query(PropellerPolarModel).filter_by(name="APC 10x10E").first()
        assert prop.variant == "E-3"


# ──────────────────────────────────────────────────────────────────────────────
# load_snapshot (gh-999: reads .gz and plain .json)
# ──────────────────────────────────────────────────────────────────────────────


class TestLoadSnapshot:
    def test_load_gz_snapshot(self, tmp_path):
        """load_snapshot reads a gzip-compressed JSON file."""
        import gzip
        import json

        records = [SAMPLE_POLAR_RECORD]
        gz_path = tmp_path / "apc_props.json.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(records))

        loaded = load_snapshot(gz_path)
        assert len(loaded) == 1
        assert loaded[0]["name"] == "APC 9x6"

    def test_load_plain_json_snapshot(self, tmp_path):
        """load_snapshot reads a plain JSON file (backwards compat)."""
        import json

        records = [SAMPLE_POLAR_RECORD]
        json_path = tmp_path / "apc_props.json"
        json_path.write_text(json.dumps(records), encoding="utf-8")

        loaded = load_snapshot(json_path)
        assert len(loaded) == 1
        assert loaded[0]["name"] == "APC 9x6"

    def test_load_snapshot_preserves_variant(self, tmp_path):
        """load_snapshot round-trips the variant field correctly."""
        import gzip
        import json

        records = [VARIANT_E_RECORD]
        gz_path = tmp_path / "apc_props.json.gz"
        with gzip.open(gz_path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps(records))

        loaded = load_snapshot(gz_path)
        assert loaded[0]["specs"]["variant"] == "E"
