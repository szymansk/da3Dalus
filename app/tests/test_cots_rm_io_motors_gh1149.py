"""Snapshot tests for data/cots/rm_io_motors.json (gh-1149).

Motors whose manufacturer publishes the winding resistance Rm and the no-load
current Io. All tests run against in-memory SQLite — no network, no real DB.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.component import ComponentModel
from app.services.cots_import import import_snapshot

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "cots" / "rm_io_motors.json"
MANUFACTURER_HOSTS = {
    "Scorpion": "scorpionsystem.com",
    "T-Motor": "store.tmotor.com",
}
CONVENTION_KEYS = {
    "rm_convention",
    "io_measured_at_v",
    "io_voltage_note",
    "source_quote",
    "plausibility_note",
}


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


@pytest.fixture()
def session() -> Session:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)()
    yield db
    db.close()


def test_snapshot_has_motors_from_both_manufacturers(records):
    by_maker = {m: [r for r in records if r["manufacturer"] == m] for m in MANUFACTURER_HOSTS}
    assert len(by_maker["Scorpion"]) >= 15
    assert len(by_maker["T-Motor"]) >= 15
    assert set(r["manufacturer"] for r in records) == set(MANUFACTURER_HOSTS)


def test_every_record_is_complete(records):
    for r in records:
        s = r["specs"]
        assert r["component_type"] == "brushless_motor"
        for key in ("kv_rpm_per_volt", "rm_ohm", "io_no_load_a"):
            assert s.get(key, 0) > 0, f"{r['name']}: {key}"
        assert r["mass_g"] > 0, r["name"]
        assert s.get("max_power_w") or s.get("max_continuous_power_w"), r["name"]
        assert s.get("max_current_a") or s.get("continuous_current_a"), r["name"]


def test_source_is_the_manufacturers_own_page(records):
    for r in records:
        host = urlparse(r["source_url"]).hostname
        assert host == MANUFACTURER_HOSTS[r["manufacturer"]], r["name"]
        assert r["specs"]["source_quote"], r["name"]
    forbidden = ("ecalc", "d-power")
    text = SNAPSHOT.read_text(encoding="utf-8").lower()
    assert not any(f in text for f in forbidden)


def test_convention_is_recorded_per_motor(records):
    for r in records:
        s = r["specs"]
        assert s["rm_convention"], r["name"]
        assert "io_measured_at_v" in s or s.get("io_voltage_note"), r["name"]


def test_resistance_outside_expected_class_range_is_declared(records):
    """ADR 0020: an Rm outside 10-300 mOhm is never taken silently."""
    for r in records:
        rm = r["specs"]["rm_ohm"]
        if not 0.010 <= rm <= 0.300:
            assert r["specs"].get("plausibility_note"), r["name"]


def test_names_are_unique(records):
    names = [(r["manufacturer"], r["name"]) for r in records]
    assert len(names) == len(set(names))


def test_import_is_idempotent_and_keeps_convention_fields(records, session):
    first = import_snapshot(session, records)
    session.commit()
    assert first.errors == []
    assert first.imported == len(records)
    again = import_snapshot(session, records)
    assert again.skipped == len(records)
    row = session.query(ComponentModel).filter_by(manufacturer="Scorpion").first()
    assert CONVENTION_KEYS & set(row.specs)
    assert row.specs["source_url"].startswith("https://scorpionsystem.com/")
