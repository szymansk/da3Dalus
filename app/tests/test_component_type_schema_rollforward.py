"""gh-1293: the additive schema roll-forward must persist, not only change the session's object.

``_patch_schema_fields`` appended to the list ``_normalize_schema`` returned, which is the very list
held by the JSON column: SQLAlchemy does not track an in-place mutation of a plain JSON value, so
nothing was written. The tests re-read in a FRESH session.
"""

from __future__ import annotations

import pytest

from app.models.component_type import ComponentTypeModel
from app.services.component_type_service import seed_default_types

pytestmark = pytest.mark.integration

NEW_BATTERY_FIELDS = {"chemistry", "cell_voltage_v"}


def _fields(session_factory, name: str) -> set:
    db = session_factory()
    try:
        row = db.query(ComponentTypeModel).filter(ComponentTypeModel.name == name).first()
        return {p["name"] for p in row.schema_def}
    finally:
        db.close()


def _strip_battery_fields(session_factory) -> None:
    """Store a list-valued legacy battery schema, as a DB seeded before #1292 holds it."""
    db = session_factory()
    try:
        row = db.query(ComponentTypeModel).filter(ComponentTypeModel.name == "battery").first()
        row.schema_def = [p for p in row.schema_def if p["name"] not in NEW_BATTERY_FIELDS]
        db.commit()
    finally:
        db.close()


def test_the_roll_forward_is_persisted_and_visible_in_a_fresh_session(client_and_db):
    _, session_factory = client_and_db
    _strip_battery_fields(session_factory)
    assert not NEW_BATTERY_FIELDS & _fields(session_factory, "battery")

    db = session_factory()
    try:
        seed_default_types(db)
        db.commit()
    finally:
        db.close()

    after = _fields(session_factory, "battery")
    assert NEW_BATTERY_FIELDS <= after
    assert {"capacity_mah", "cells", "c_rate", "voltage_v"} <= after


def test_the_roll_forward_is_idempotent_across_sessions(client_and_db):
    _, session_factory = client_and_db
    _strip_battery_fields(session_factory)
    for _ in range(2):
        db = session_factory()
        try:
            seed_default_types(db)
            db.commit()
        finally:
            db.close()
    db = session_factory()
    try:
        row = db.query(ComponentTypeModel).filter(ComponentTypeModel.name == "battery").first()
        names = [p["name"] for p in row.schema_def]
    finally:
        db.close()
    assert len(names) == len(set(names))
