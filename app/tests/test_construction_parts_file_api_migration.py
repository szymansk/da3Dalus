"""Migration test for file_path + file_format columns on construction_parts (gh#57-9uk)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_adds_file_columns(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("construction_parts")}
    assert "file_path" in columns
    assert "file_format" in columns


def test_alembic_downgrade_removes_file_columns(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")
    # Target the parent of this migration explicitly — `-1` ambiguates once
    # the history contains merge points.
    command.downgrade(alembic_cfg, "4a9c81984e86")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("construction_parts")}
    assert "file_path" not in columns
    assert "file_format" not in columns
