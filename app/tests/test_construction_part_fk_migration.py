"""Migration test for construction_part_id FK on component_tree (gh#57-u4d)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_adds_construction_part_id_column(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)

    columns = {col["name"]: col for col in inspector.get_columns("component_tree")}
    assert "construction_part_id" in columns

    # FK to construction_parts must be present
    fks = inspector.get_foreign_keys("component_tree")
    target_tables = {fk["referred_table"] for fk in fks}
    assert "construction_parts" in target_tables


def test_alembic_downgrade_removes_construction_part_id_column(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "-1")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("component_tree")}
    assert "construction_part_id" not in columns
