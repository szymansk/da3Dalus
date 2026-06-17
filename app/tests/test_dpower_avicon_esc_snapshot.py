"""Tests for gh-1009: dpower.json AVICON ESC snapshot conforms to the canonical ESC schema.

Verifies:
- Every AVICON ESC entry in data/cots/dpower.json has cells_nixx_min/max keys present.
- Every AVICON ESC entry has bec_voltage_5v and bec_current_a (BEC-capable AVICON models).
- None of the removed keys (bec_output, bec_voltage_v, legacy cells) appear in any ESC specs.
- Re-import of the full dpower.json snapshot is idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.services.cots_import import import_snapshot


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DPOWER_PATH = _REPO_ROOT / "data" / "cots" / "dpower.json"

REMOVED_KEYS = {"bec_output", "bec_voltage_v", "cells"}


def _load_dpower() -> list[dict]:
    return json.loads(_DPOWER_PATH.read_text(encoding="utf-8"))


def _avicon_escs(records: list[dict]) -> list[dict]:
    """Return all ESC records whose name starts with 'AVICON'."""
    return [
        r for r in records if r.get("component_type") == "esc" and r["name"].startswith("AVICON")
    ]


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
# Snapshot-level field compliance tests (no DB required)
# ──────────────────────────────────────────────────────────────────────────────


class TestDpowerAviconEscSnapshot:
    """Snapshot-level assertions on data/cots/dpower.json."""

    def setup_method(self):
        self.records = _load_dpower()
        self.avicon_escs = _avicon_escs(self.records)

    def test_avicon_escs_found(self):
        """There must be at least 7 AVICON ESC entries in dpower.json."""
        assert len(self.avicon_escs) >= 7, (
            f"Expected >=7 AVICON ESC records, found {len(self.avicon_escs)}"
        )

    def test_every_avicon_esc_has_cells_nixx_min(self):
        """Every AVICON ESC record must have cells_nixx_min in its specs."""
        missing = [r["name"] for r in self.avicon_escs if "cells_nixx_min" not in r["specs"]]
        assert not missing, f"AVICON ESC entries missing cells_nixx_min: {missing}"

    def test_every_avicon_esc_has_cells_nixx_max(self):
        """Every AVICON ESC record must have cells_nixx_max in its specs."""
        missing = [r["name"] for r in self.avicon_escs if "cells_nixx_max" not in r["specs"]]
        assert not missing, f"AVICON ESC entries missing cells_nixx_max: {missing}"

    def test_every_avicon_esc_has_bec_current_a(self):
        """Every AVICON ESC record must have bec_current_a in its specs."""
        missing = [r["name"] for r in self.avicon_escs if "bec_current_a" not in r["specs"]]
        assert not missing, f"AVICON ESC entries missing bec_current_a: {missing}"

    def test_every_avicon_esc_bec_voltage_5v_is_true(self):
        """Every AVICON ESC must have bec_voltage_5v=True (AVICON BEC supports 5V)."""
        non_compliant = [
            r["name"] for r in self.avicon_escs if r["specs"].get("bec_voltage_5v") is not True
        ]
        assert not non_compliant, f"AVICON ESC entries without bec_voltage_5v=True: {non_compliant}"

    def test_no_esc_entry_has_removed_keys(self):
        """No ESC spec in dpower.json may contain bec_output, bec_voltage_v, or cells."""
        all_escs = [r for r in self.records if r.get("component_type") == "esc"]
        violators = {}
        for r in all_escs:
            found = REMOVED_KEYS & set(r["specs"].keys())
            if found:
                violators[r["name"]] = sorted(found)
        assert not violators, f"ESC entries still contain removed keys: {violators}"

    def test_avicon_standard_series_cells_nixx_range(self):
        """AVICON standard series (not PRO) must have cells_nixx_min=5, cells_nixx_max=12."""
        standard = [r for r in self.avicon_escs if "PRO" not in r["name"]]
        wrong = [
            r["name"]
            for r in standard
            if r["specs"].get("cells_nixx_min") != 5 or r["specs"].get("cells_nixx_max") != 12
        ]
        assert not wrong, f"AVICON standard ESC entries with wrong NiXX range: {wrong}"


# ──────────────────────────────────────────────────────────────────────────────
# Import + idempotency tests
# ──────────────────────────────────────────────────────────────────────────────


class TestDpowerSnapshotImport:
    """Import tests against in-memory SQLite."""

    def _load(self) -> list[dict]:
        return _load_dpower()

    def test_dpower_snapshot_imports_all_avicon_escs_with_new_fields(self, session):
        """Import full dpower.json — every AVICON ESC row in the DB must:
        - have bec_voltage_5v=True and bec_current_a present;
        - have cells_nixx_min/max stored for standard AVICON (non-PRO) entries
          where the snapshot carries non-null values;
        - not contain any removed legacy keys (bec_output, bec_voltage_v, cells).

        Note: the import service strips null values from specs, so cells_nixx_*
        null placeholders (used on AVICON PRO HV where NiXX support is unknown)
        are intentionally absent from the DB row.
        """
        records = self._load()
        result = import_snapshot(session, records)
        session.commit()

        assert not result.errors, f"Import errors: {result.errors}"

        avicon_records = [
            r
            for r in records
            if r.get("component_type") == "esc" and r["name"].startswith("AVICON")
        ]
        assert len(avicon_records) >= 7

        for rec in avicon_records:
            name = rec["name"]
            row = session.query(ComponentModel).filter_by(name=name).first()
            assert row is not None, f"{name} not found in DB"
            specs = row.specs

            # BEC fields must be present for all AVICON ESCs
            assert specs.get("bec_voltage_5v") is True, f"{name}: bec_voltage_5v not True"
            assert "bec_current_a" in specs, f"{name}: bec_current_a missing"

            # NiXX cells: only check when the snapshot has a non-null value
            if rec["specs"].get("cells_nixx_min") is not None:
                assert "cells_nixx_min" in specs, f"{name}: cells_nixx_min missing from DB"
                assert "cells_nixx_max" in specs, f"{name}: cells_nixx_max missing from DB"
                assert specs["cells_nixx_min"] == rec["specs"]["cells_nixx_min"], (
                    f"{name}: cells_nixx_min value mismatch"
                )
                assert specs["cells_nixx_max"] == rec["specs"]["cells_nixx_max"], (
                    f"{name}: cells_nixx_max value mismatch"
                )

            # Removed keys must be absent from DB
            for bad_key in REMOVED_KEYS:
                assert bad_key not in specs, f"{name}: removed key '{bad_key}' still present"

    def test_dpower_snapshot_reimport_is_idempotent(self, session):
        """Importing dpower.json twice must produce no new rows on the second run."""
        records = self._load()

        result1 = import_snapshot(session, records)
        session.commit()
        total_after_first = session.query(ComponentModel).count()

        result2 = import_snapshot(session, records)
        session.commit()
        total_after_second = session.query(ComponentModel).count()

        assert total_after_first == total_after_second, (
            "Row count changed on second import — not idempotent"
        )
        assert result2.imported == 0, (
            f"Second import should have imported=0, got {result2.imported}"
        )
        assert result2.errors == [], f"Second import errors: {result2.errors}"
