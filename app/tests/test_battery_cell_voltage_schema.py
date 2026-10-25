"""gh-1245 / gh-1290: battery chemistry and nominal cell voltage, motor efficiency as catalogue fields.

Covers:
- The seeded battery ComponentType carries ``chemistry`` (closed enumeration) and ``cell_voltage_v``.
- The seeded brushless_motor ComponentType carries ``efficiency_pct`` (percent).
- ``seed_default_types`` rolls the battery fields onto a legacy battery schema, additively.
- The committed battery snapshot states chemistry and cell voltage per battery, and the pack
  voltage is consistent with them (one authority, ADR 0022: voltage_v = cells * cell_voltage_v).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import seed_default_types

REPO_ROOT = Path(__file__).resolve().parents[2]
CHEMISTRIES = ["lipo", "lihv", "life", "li_ion", "nimh"]


def _type_fields(db, name: str) -> dict:
    row = db.query(ComponentTypeModel).filter(ComponentTypeModel.name == name).first()
    assert row is not None
    return {p["name"]: p for p in row.schema_def if isinstance(p, dict)}


@pytest.mark.integration
def test_battery_type_has_chemistry_and_cell_voltage(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        fields = _type_fields(db, "battery")
        assert fields["chemistry"]["type"] == "enum"
        assert fields["chemistry"]["options"] == CHEMISTRIES
        assert fields["cell_voltage_v"]["type"] == "number"
        assert fields["cell_voltage_v"]["unit"] == "V"
        assert fields["cell_voltage_v"]["min"] == 0
    finally:
        db.close()


@pytest.mark.integration
def test_motor_type_has_efficiency_pct(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        field = _type_fields(db, "brushless_motor")["efficiency_pct"]
        assert field["type"] == "number"
        assert field["unit"] == "%"
        assert (field["min"], field["max"]) == (0, 100)
    finally:
        db.close()


@pytest.mark.integration
def test_seeding_rolls_the_battery_fields_onto_a_legacy_schema(client_and_db):
    _, SessionLocal = client_and_db
    db = SessionLocal()
    try:
        row = db.query(ComponentTypeModel).filter(ComponentTypeModel.name == "battery").first()
        legacy = [p for p in row.schema_def if p["name"] not in ("chemistry", "cell_voltage_v")]
        row.schema_def = legacy
        db.flush()
        seed_default_types(db)
        db.commit()
        after = _type_fields(db, "battery")
        assert {"capacity_mah", "cells", "c_rate", "voltage_v"} <= set(after)
        assert {"chemistry", "cell_voltage_v"} <= set(after)
    finally:
        db.close()


def test_every_snapshot_battery_states_chemistry_and_a_consistent_pack_voltage():
    records = json.loads((REPO_ROOT / "data/cots/generic_batteries.json").read_text("utf-8"))
    assert records
    for record in records:
        specs = record["specs"]
        assert specs["chemistry"] in CHEMISTRIES, record["name"]
        assert specs["cell_voltage_v"] > 0, record["name"]
        assert math.isclose(
            specs["voltage_v"], specs["cells"] * specs["cell_voltage_v"], rel_tol=1e-9
        ), record["name"]
