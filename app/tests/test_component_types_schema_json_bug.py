"""Regression test for the 2026-04-16 500-on-GET bug (gh#83 backend).

Cause: the Alembic seed migration passed `json.dumps(list)` to
bulk_insert on a JSON-typed column. SQLAlchemy's JSON type then
`json.dumps()`ed the already-dumped string — resulting in a
double-encoded JSON scalar (`'"[{...}]"'`). On read, `json.loads`
unwraps only the outer layer, handing Pydantic a STRING where it
expects a list. Pydantic rejects → HTTP 500.

Two tests:

1. Reproduce with a migration-shaped bad row (raw string in JSON
   column, double-encoded via SQLAlchemy JSON type). Endpoint must
   recover gracefully with 200 + parsed list.
2. Verify that the real Alembic migration upgrade → GET roundtrip
   returns a parsed list.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text


def _seed_double_encoded_row(session_factory) -> None:
    """Mimic what the Alembic bulk_insert with json.dumps() produced: a
    scalar JSON string value inside the JSON column (double encoded)."""
    bad_schema_double_encoded = json.dumps(
        json.dumps([{"name": "foo", "label": "Foo", "type": "number"}])
    )
    session = session_factory()
    try:
        session.execute(
            text(
                "INSERT INTO component_types "
                "(name, label, description, schema, deletable) "
                "VALUES (:name, :label, :description, :schema, :deletable)"
            ),
            {
                "name": "bad_legacy",
                "label": "Bad Legacy",
                "description": None,
                "schema": bad_schema_double_encoded,
                "deletable": False,
            },
        )
        session.commit()
    finally:
        session.close()


class TestJsonStringSchemaRecovery:

    def test_get_component_types_does_not_500_on_legacy_double_encoded_schema(
        self, client_and_db
    ):
        client, sf = client_and_db
        _seed_double_encoded_row(sf)
        res = client.get("/component-types")
        assert res.status_code == 200, (
            f"expected 200, got {res.status_code}: {res.text[:300]}"
        )
        body = res.json()
        bad = next((t for t in body if t["name"] == "bad_legacy"), None)
        assert bad is not None
        assert isinstance(bad["schema"], list)
        assert bad["schema"][0]["name"] == "foo"

    def test_get_single_component_type_also_handles_legacy_double_encoded(
        self, client_and_db
    ):
        client, sf = client_and_db
        _seed_double_encoded_row(sf)
        body = client.get("/component-types").json()
        bad = next(t for t in body if t["name"] == "bad_legacy")
        res = client.get(f"/component-types/{bad['id']}")
        assert res.status_code == 200
        assert isinstance(res.json()["schema"], list)


class TestAlembicMigrationPathProducesValidSchema:
    """End-to-end check: run the actual migration chain and hit the endpoint."""

    def test_upgrade_head_then_get_returns_parsed_list(self, tmp_path):
        """Bug repro: running the real migration produces double-encoded
        rows; the endpoint must still return 200 with proper lists.

        (Before the fix this test fails because the migration stores schema
        as a double-encoded string and ComponentTypeRead validation blows
        up with `Input should be a valid list`.)
        """
        db_path = tmp_path / "migrated.db"
        db_url = f"sqlite:///{db_path}"

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        command.upgrade(alembic_cfg, "head")

        # Spin up an app bound to this DB and hit the endpoint.
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, sessionmaker
        from app.db.session import get_db
        from app.main import create_app

        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)

        app = create_app()
        app.dependency_overrides[get_db] = lambda: SessionLocal()
        try:
            with TestClient(app) as client:
                res = client.get("/component-types")
                assert res.status_code == 200, (
                    f"expected 200, got {res.status_code}: {res.text[:500]}"
                )
                body = res.json()
                assert len(body) >= 9  # nine seed types
                material = next(t for t in body if t["name"] == "material")
                assert isinstance(material["schema"], list)
                density = next(p for p in material["schema"] if p["name"] == "density_kg_m3")
                assert density["type"] == "number"
                assert density["required"] is True
        finally:
            app.dependency_overrides.clear()
