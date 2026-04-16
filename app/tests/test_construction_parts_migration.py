"""Migration test for the construction_parts table (gh#57-g4h)."""
from __future__ import annotations

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_construction_parts_table(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)

    assert "construction_parts" in inspector.get_table_names()

    columns = {col["name"]: col for col in inspector.get_columns("construction_parts")}
    assert "id" in columns
    assert "aeroplane_id" in columns
    assert "name" in columns
    assert "volume_mm3" in columns
    assert "area_mm2" in columns
    assert "bbox_x_mm" in columns
    assert "bbox_y_mm" in columns
    assert "bbox_z_mm" in columns
    assert "material_component_id" in columns
    assert "locked" in columns
    assert "thumbnail_url" in columns
    assert "created_at" in columns
    assert "updated_at" in columns

    # aeroplane_id must be indexed for the per-aeroplane listing query
    indexed_cols: set[str] = set()
    for idx in inspector.get_indexes("construction_parts"):
        indexed_cols.update(idx["column_names"])
    assert "aeroplane_id" in indexed_cols

    # FK to components must be present so material_component_id is validated at the DB layer
    fks = inspector.get_foreign_keys("construction_parts")
    target_tables = {fk["referred_table"] for fk in fks}
    assert "components" in target_tables
