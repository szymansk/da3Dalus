"""Migration test for gh-1000 propeller_polars enrichment columns.

Verifies the additive migration adds weight_g / inertia_kg_m2 / geometry on
upgrade and removes them on downgrade, against a real temp SQLite DB driven
through the full alembic chain.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENRICH_COLS = {"weight_g", "inertia_kg_m2", "geometry"}


@pytest.fixture()
def alembic_cfg():
    tmp = tempfile.mkdtemp()
    db = f"{tmp}/gh1000.db"
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db}")
    cfg.attributes["db_path"] = db
    return cfg


def _cols(db_path: str) -> set[str]:
    con = sqlite3.connect(db_path)
    try:
        return {r[1] for r in con.execute("PRAGMA table_info(propeller_polars)")}
    finally:
        con.close()


class TestMigrationGh1000:
    def test_upgrade_adds_enrichment_columns(self, alembic_cfg):
        command.upgrade(alembic_cfg, "head")
        cols = _cols(alembic_cfg.attributes["db_path"])
        assert ENRICH_COLS <= cols

    def test_downgrade_removes_enrichment_columns(self, alembic_cfg):
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "-1")
        cols = _cols(alembic_cfg.attributes["db_path"])
        assert not (ENRICH_COLS & cols)

    def test_upgrade_downgrade_upgrade_roundtrip(self, alembic_cfg):
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "-1")
        command.upgrade(alembic_cfg, "head")
        cols = _cols(alembic_cfg.attributes["db_path"])
        assert ENRICH_COLS <= cols
