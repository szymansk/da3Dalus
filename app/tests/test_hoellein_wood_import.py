"""Tests for the Höllein wood construction-stock import (gh-1083).

Covers:
- The four new seeded component types (veneer / strip / triangular_strip /
  grooved_strip) exist, are non-deletable, and expose a required ``material``
  enum that references a density-bearing material component.
- The Abachi material component is seeded with its density.
- The COTS importer accepts the new wood component types.
- The committed snapshot ``data/cots/hoellein_wood.json`` is well-formed:
  52 records, valid types, every ``material`` resolves to a seeded material
  component, dimensions carried in the bbox fields, and no baked-in mass
  (mass derives downstream from the referenced material's density).
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
from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import (
    seed_default_types,
    seed_structural_materials,
)
from app.services.cots_import import _validate_record, import_snapshot

pytestmark = pytest.mark.integration

WOOD_TYPES = {"veneer", "strip", "triangular_strip", "grooved_strip"}
MATERIAL_OPTIONS = {"Pine (structural)", "Abachi"}

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "cots" / "hoellein_wood.json"


@pytest.fixture()
def session() -> Session:
    """Fresh in-memory SQLite session per test (no real DB required)."""
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
# Seeded component types
# ──────────────────────────────────────────────────────────────────────────────


def test_wood_types_seeded_nondeletable(session):
    seed_default_types(session)
    session.commit()
    rows = {r.name: r for r in session.query(ComponentTypeModel).all()}
    for name in WOOD_TYPES:
        assert name in rows, f"missing seeded type {name}"
        assert rows[name].deletable is False


def test_wood_types_have_material_reference(session):
    seed_default_types(session)
    session.commit()
    for name in WOOD_TYPES:
        row = session.query(ComponentTypeModel).filter(ComponentTypeModel.name == name).first()
        props = {p["name"]: p for p in row.schema_def}
        assert "material" in props, f"{name} missing material field"
        mat = props["material"]
        assert mat["type"] == "enum"
        assert mat.get("required") is True
        assert MATERIAL_OPTIONS.issubset(set(mat["options"]))


def test_grooved_strip_has_groove_field(session):
    seed_default_types(session)
    session.commit()
    row = (
        session.query(ComponentTypeModel).filter(ComponentTypeModel.name == "grooved_strip").first()
    )
    names = {p["name"] for p in row.schema_def}
    assert "groove_mm" in names


def test_abachi_material_seeded_with_density(session):
    seed_structural_materials(session)
    session.commit()
    abachi = (
        session.query(ComponentModel)
        .filter(ComponentModel.name == "Abachi", ComponentModel.component_type == "material")
        .first()
    )
    assert abachi is not None
    assert abachi.specs["density_kg_m3"] == 390.0


# ──────────────────────────────────────────────────────────────────────────────
# Importer accepts the new wood types
# ──────────────────────────────────────────────────────────────────────────────


def test_importer_accepts_wood_record(session):
    record = {
        "manufacturer": "Höllein",
        "name": "Kiefernleiste 10x10x1000mm",
        "component_type": "strip",
        "mass_g": None,
        "bbox_x_mm": 10,
        "bbox_y_mm": 10,
        "bbox_z_mm": 1000,
        "model_ref": "hoellein/kiefernleiste-10x10x1000",
        "source_url": "https://hoelleinshop.com/x",
        "source_version": "hoellein 2026-06-22",
        "specs": {"material": "Pine (structural)", "price_eur": 1.8},
    }
    assert _validate_record(record) is None
    result = import_snapshot(session, [record])
    session.commit()
    assert result.imported == 1
    assert not result.errors
    row = session.query(ComponentModel).filter_by(name=record["name"]).first()
    assert row.component_type == "strip"
    assert row.bbox_z_mm == 1000
    assert row.specs["material"] == "Pine (structural)"
    assert row.mass_g is None


def test_importer_rejects_unknown_type(session):
    bad = {"manufacturer": "x", "name": "y", "component_type": "frobnicator", "specs": {}}
    assert _validate_record(bad) is not None


# ──────────────────────────────────────────────────────────────────────────────
# Committed snapshot integrity
# ──────────────────────────────────────────────────────────────────────────────


def _load_snapshot() -> list[dict]:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_snapshot_exists_and_has_52_records():
    assert SNAPSHOT.exists(), f"snapshot not found: {SNAPSHOT}"
    assert len(_load_snapshot()) == 52


def test_snapshot_records_well_formed():
    for rec in _load_snapshot():
        assert rec["component_type"] in WOOD_TYPES
        # The importer would accept every record.
        assert _validate_record(rec) is None
        # Dimensions live in the bbox fields, all positive.
        for f in ("bbox_x_mm", "bbox_y_mm", "bbox_z_mm"):
            assert isinstance(rec[f], (int, float)) and rec[f] > 0, f"{rec['name']}: bad {f}"
        # Mass is not baked in — it derives from the referenced material density.
        assert rec.get("mass_g") is None
        # Material reference resolves to a known material component.
        assert rec["specs"]["material"] in MATERIAL_OPTIONS


def test_snapshot_imports_end_to_end(session):
    seed_default_types(session)
    seed_structural_materials(session)
    session.commit()

    result = import_snapshot(session, _load_snapshot())
    session.commit()
    assert result.imported == 52
    assert not result.errors

    mats = {
        m.name
        for m in session.query(ComponentModel)
        .filter(ComponentModel.component_type == "material")
        .all()
    }
    woods = (
        session.query(ComponentModel)
        .filter(ComponentModel.component_type.in_(tuple(WOOD_TYPES)))
        .all()
    )
    assert len(woods) == 52
    for w in woods:
        assert w.specs["material"] in mats, f"{w.name}: dangling material {w.specs['material']}"
