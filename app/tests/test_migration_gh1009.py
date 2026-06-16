"""Tests for the gh-1009 Alembic migration: ESC schema enrichment + spec data migration.

Strategy: exercise the pure-function helpers (_snap_voltage, _parse_bec_output,
_migrate_esc_specs) directly, and test upgrade()/downgrade() by manipulating an
in-memory SQLite database directly (no Alembic runner needed — the migration is
a single Python file with plain SQLAlchemy calls via op.get_bind()).
"""

from __future__ import annotations

import importlib
import json
import re

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────────────────────────────────────
# Locate the migration module dynamically (revision ID is auto-generated)
# ──────────────────────────────────────────────────────────────────────────────


def _load_migration():
    """Import the gh-1009 migration module.

    We find it by searching alembic/versions/ for a file whose name contains
    'gh1009' or 'gh_1009' or whose down_revision is '1f320603c2cf'.
    """
    from pathlib import Path

    versions_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
    candidates = list(versions_dir.glob("*gh*1009*.py")) + list(
        versions_dir.glob("*esc*enrich*.py")
    )

    if not candidates:
        # Fall back: scan all .py files for down_revision = "1f320603c2cf"
        for p in sorted(versions_dir.glob("*.py")):
            src = p.read_text()
            if "1f320603c2cf" in src and "esc" in src.lower():
                candidates.append(p)

    if not candidates:
        pytest.fail(
            "Could not locate the gh-1009 ESC migration file in alembic/versions/. Create it first."
        )

    # Pick the first match
    path = candidates[0]
    spec = importlib.util.spec_from_file_location("migration_gh1009", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ──────────────────────────────────────────────────────────────────────────────
# Pre-gh1009 schema (10-field German-label set that 1f320603c2cf left in place)
# ──────────────────────────────────────────────────────────────────────────────

PRE_GH1009_SCHEMA = [
    {
        "name": "max_current_a",
        "label": "Max Strom (kurz)",
        "type": "number",
        "unit": "A",
        "required": True,
    },
    {"name": "cells", "label": "Zellen (S)", "type": "number"},
    {"name": "bec_voltage_v", "label": "BEC Spannung", "type": "number", "unit": "V"},
    {"name": "bec_current_a", "label": "BEC Strom", "type": "number", "unit": "A"},
    {
        "name": "protocol",
        "label": "Protokoll",
        "type": "enum",
        "options": ["pwm", "oneshot", "dshot150", "dshot300", "dshot600"],
    },
    {"name": "continuous_current_a", "label": "Dauerstrom", "type": "number", "unit": "A"},
    {"name": "cells_lipo_min", "label": "LiPo Zellen min", "type": "number"},
    {"name": "cells_lipo_max", "label": "LiPo Zellen max", "type": "number"},
    {"name": "bec_output", "label": "BEC Ausgang", "type": "string"},
    {"name": "art_no", "label": "Art.-Nr.", "type": "string"},
]


@pytest.fixture()
def migration():
    """The gh-1009 migration module."""
    return _load_migration()


# ──────────────────────────────────────────────────────────────────────────────
# In-memory engine factory
# ──────────────────────────────────────────────────────────────────────────────


def _make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE component_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    "schema" TEXT
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    specs TEXT
                )
                """
            )
        )
    return engine


def _seed_esc_type(conn, schema=None):
    """Insert the pre-gh1009 esc component_types row."""
    schema_json = json.dumps(schema if schema is not None else PRE_GH1009_SCHEMA)
    conn.execute(
        text("INSERT INTO component_types (name, label, \"schema\") VALUES ('esc', 'ESC', :s)"),
        {"s": schema_json},
    )


def _insert_component(conn, specs: dict) -> int:
    result = conn.execute(
        text("INSERT INTO components (name, component_type, specs) VALUES ('Test ESC', 'esc', :s)"),
        {"s": json.dumps(specs)},
    )
    return result.lastrowid


def _get_esc_schema(conn) -> list[dict]:
    row = conn.execute(text("SELECT \"schema\" FROM component_types WHERE name='esc'")).fetchone()
    assert row is not None, "esc row missing"
    return json.loads(row[0])


def _get_component_specs(conn, row_id: int) -> dict:
    row = conn.execute(
        text("SELECT specs FROM components WHERE id=:id"),
        {"id": row_id},
    ).fetchone()
    assert row is not None
    return json.loads(row[0])


# ──────────────────────────────────────────────────────────────────────────────
# Fake Alembic op.get_bind() shim
# ──────────────────────────────────────────────────────────────────────────────


class _FakeOp:
    """Minimal shim so migration functions can call op.get_bind()."""

    def __init__(self, conn):
        self._conn = conn

    def get_bind(self):
        return self._conn


# ──────────────────────────────────────────────────────────────────────────────
# Pure-function unit tests (no Alembic runner)
# ──────────────────────────────────────────────────────────────────────────────


class TestSnapVoltage:
    def test_exact_5v(self, migration):
        assert migration._snap_voltage(5.0) == "bec_voltage_5v"

    def test_exact_6v(self, migration):
        assert migration._snap_voltage(6.0) == "bec_voltage_6v"

    def test_within_tolerance(self, migration):
        assert migration._snap_voltage(5.05) == "bec_voltage_5v"

    def test_outside_all_bands_returns_none(self, migration):
        assert migration._snap_voltage(3.3) is None

    def test_7_4v(self, migration):
        assert migration._snap_voltage(7.4) == "bec_voltage_7_4v"

    def test_12v(self, migration):
        assert migration._snap_voltage(12.0) == "bec_voltage_12v"


class TestParseBecOutput:
    def test_slash_notation_5v_6v_4a(self, migration):
        result = migration._parse_bec_output("5V/6V 4A")
        assert result.get("bec_voltage_5v") is True
        assert result.get("bec_voltage_6v") is True
        assert result.get("bec_current_a") == 4

    def test_single_voltage_5v_8a(self, migration):
        result = migration._parse_bec_output("5V / 8A")
        assert result.get("bec_voltage_5v") is True
        assert "bec_voltage_6v" not in result
        assert result.get("bec_current_a") == 8

    def test_german_multi_voltage_string(self, migration):
        result = migration._parse_bec_output("5.0V, 5.5V, 6V einstellbar - 5A")
        assert result.get("bec_voltage_5v") is True
        assert result.get("bec_voltage_5_5v") is True
        assert result.get("bec_voltage_6v") is True
        assert result.get("bec_current_a") == 5

    def test_null_input_returns_empty(self, migration):
        result = migration._parse_bec_output(None)
        assert result == {}

    def test_no_voltage_tokens_returns_empty(self, migration):
        result = migration._parse_bec_output("OPTO")
        assert result == {}


class TestMigrateEscSpecs:
    def test_bec_output_slash_notation(self, migration):
        specs = {"bec_output": "5V/6V 4A", "continuous_current_a": 20.0, "max_current_a": 30.0}
        result = migration._migrate_esc_specs(specs)
        assert result.get("bec_voltage_5v") is True
        assert result.get("bec_voltage_6v") is True
        assert result.get("bec_current_a") == 4
        assert "bec_output" not in result

    def test_bec_voltage_v_scalar(self, migration):
        specs = {"bec_voltage_v": 6.0, "max_current_a": 20.0}
        result = migration._migrate_esc_specs(specs)
        assert result.get("bec_voltage_6v") is True
        assert "bec_voltage_v" not in result

    def test_cells_key_dropped(self, migration):
        specs = {"cells": 3, "max_current_a": 20.0}
        result = migration._migrate_esc_specs(specs)
        assert "cells" not in result

    def test_other_fields_preserved(self, migration):
        specs = {"continuous_current_a": 20.0, "art_no": "X1", "max_current_a": 30.0}
        result = migration._migrate_esc_specs(specs)
        assert result["continuous_current_a"] == 20.0
        assert result["art_no"] == "X1"

    def test_no_bec_fields_is_noop(self, migration):
        specs = {"continuous_current_a": 20.0, "max_current_a": 30.0}
        result = migration._migrate_esc_specs(specs)
        assert "bec_voltage_5v" not in result
        assert result["continuous_current_a"] == 20.0


# ──────────────────────────────────────────────────────────────────────────────
# Upgrade tests (using in-memory SQLite + fake op)
# ──────────────────────────────────────────────────────────────────────────────


class TestMigrationUp:
    def test_up_replaces_esc_schema_in_db(self, migration):
        """After upgrade(), component_types.schema for 'esc' has the 19 canonical fields."""
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            schema = _get_esc_schema(conn)
            names = [f["name"] for f in schema]
            assert "bec_voltage_5v" in names
            assert "cells_nixx_min" in names
            assert len(names) == 19

    def test_up_removes_cells_bec_voltage_v_bec_output_from_schema(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            schema = _get_esc_schema(conn)
            names = [f["name"] for f in schema]
            assert "cells" not in names
            assert "bec_voltage_v" not in names
            assert "bec_output" not in names

    def test_up_migrates_bec_output_slash_notation(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(
                conn,
                {"bec_output": "5V/6V 4A", "continuous_current_a": 20.0, "max_current_a": 30.0},
            )

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert specs.get("bec_voltage_5v") is True
            assert specs.get("bec_voltage_6v") is True
            assert specs.get("bec_current_a") == 4
            assert "bec_output" not in specs

    def test_up_migrates_bec_output_single_voltage(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(conn, {"bec_output": "5V / 8A", "max_current_a": 20.0})

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert specs.get("bec_voltage_5v") is True
            assert "bec_voltage_6v" not in specs
            assert specs.get("bec_current_a") == 8

    def test_up_migrates_bec_output_multi_voltage_german_string(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(
                conn,
                {"bec_output": "5.0V, 5.5V, 6V einstellbar - 5A", "max_current_a": 45.0},
            )

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert specs.get("bec_voltage_5v") is True
            assert specs.get("bec_voltage_5_5v") is True
            assert specs.get("bec_voltage_6v") is True
            assert specs.get("bec_current_a") == 5

    def test_up_migrates_bec_output_null(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(conn, {"bec_output": None, "max_current_a": 20.0})

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            # None bec_output → no bec_voltage_* keys added
            assert not any(k.startswith("bec_voltage_") for k in specs)

    def test_up_migrates_bec_voltage_v_scalar(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(conn, {"bec_voltage_v": 6.0, "max_current_a": 20.0})

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert specs.get("bec_voltage_6v") is True
            assert "bec_voltage_v" not in specs

    def test_up_drops_cells_key(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(conn, {"cells": 3, "max_current_a": 20.0})

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert "cells" not in specs

    def test_up_preserves_other_fields(self, migration):
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(
                conn, {"continuous_current_a": 20.0, "art_no": "X1", "max_current_a": 30.0}
            )

        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

            specs = _get_component_specs(conn, row_id)
            assert specs["continuous_current_a"] == 20.0
            assert specs["art_no"] == "X1"

    def test_up_nonexistent_esc_type_is_noop(self, migration):
        """upgrade() on a blank DB (no esc row) must complete without error."""
        engine = _make_engine()
        # Do not seed the esc row
        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind
        # No exception → pass


class TestMigrationDown:
    def test_down_restores_pre_gh1009_schema(self, migration):
        """After upgrade() + downgrade(), the esc schema_def matches the 10-field pre-gh1009 set."""
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)

        # Upgrade
        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

        # Downgrade
        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.downgrade()
            finally:
                real_op.get_bind = orig_get_bind

            schema = _get_esc_schema(conn)
            names = [f["name"] for f in schema]

        expected_names = {f["name"] for f in PRE_GH1009_SCHEMA}
        assert set(names) == expected_names, (
            f"Missing: {expected_names - set(names)}, Extra: {set(names) - expected_names}"
        )

    def test_down_does_not_touch_component_specs(self, migration):
        """Downgrade restores schema_def only; spec data migration is one-way (not reversed)."""
        engine = _make_engine()
        with engine.begin() as conn:
            _seed_esc_type(conn)
            row_id = _insert_component(conn, {"bec_output": "5V/6V 4A", "max_current_a": 30.0})

        # Upgrade
        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.upgrade()
            finally:
                real_op.get_bind = orig_get_bind

        # Downgrade
        with engine.begin() as conn:
            import alembic.op as real_op

            orig_get_bind = real_op.get_bind
            real_op.get_bind = lambda: conn
            try:
                migration.downgrade()
            finally:
                real_op.get_bind = orig_get_bind

            # Spec data is NOT reversed — bec_voltage_5v is still there
            specs = _get_component_specs(conn, row_id)
            # The spec data migration is intentionally one-way; bec_output is gone
            assert "bec_output" not in specs
