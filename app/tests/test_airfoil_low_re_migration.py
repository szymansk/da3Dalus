"""Migration test for gh-821 airfoil low-Re tables.

Runs Alembic upgrade head on a TEMP SQLite (NOT the shared db/ symlink)
and asserts the new tables and constraints are created correctly.
"""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.fixture()
def migration_db(tmp_path):
    """Return (engine, alembic_cfg) on a fresh temp SQLite, upgraded to head."""
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    yield engine, alembic_cfg
    engine.dispose()


def test_upgrade_creates_airfoil_geometry_table(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    assert "airfoil_geometry" in inspector.get_table_names()


def test_upgrade_creates_airfoil_low_re_polar_table(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    assert "airfoil_low_re_polar" in inspector.get_table_names()


def test_airfoil_geometry_columns_present(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("airfoil_geometry")}
    required = {"id", "airfoil_name", "max_thickness_pct", "max_camber_pct",
                "camber_at_te", "family", "computed_at"}
    for col in required:
        assert col in col_names, f"missing column: {col}"


def test_airfoil_low_re_polar_columns_present(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    col_names = {c["name"] for c in inspector.get_columns("airfoil_low_re_polar")}
    required = {
        "id", "airfoil_name", "reynolds", "ld_max", "cl_max",
        "alpha_attached_lo", "alpha_attached_hi", "drag_bucket_width",
        "cd_min", "stall_gentleness", "cd0", "k", "cl0",
        "cl_valid_lo", "cl_valid_hi", "min_analysis_confidence",
        "neuralfoil_model_size", "n_crit", "computed_at",
    }
    for col in required:
        assert col in col_names, f"missing column: {col}"


def test_airfoil_geometry_unique_index_on_airfoil_name(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("airfoil_geometry")}
    # The unique index created via unique=True on airfoil_name column
    unique_indexes = [idx for idx in indexes.values() if idx.get("unique")]
    unique_columns = {col for idx in unique_indexes for col in idx["column_names"]}
    assert "airfoil_name" in unique_columns


def test_airfoil_low_re_polar_unique_constraint(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    uqs = inspector.get_unique_constraints("airfoil_low_re_polar")
    # Must have a unique constraint named uq_airfoil_low_re_polar
    names = {uq["name"] for uq in uqs}
    assert "uq_airfoil_low_re_polar" in names


def test_airfoil_geometry_fk_to_airfoils(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("airfoil_geometry")
    referred = {fk["referred_table"] for fk in fks}
    assert "airfoils" in referred


def test_airfoil_low_re_polar_fk_to_airfoils(migration_db):
    engine, _ = migration_db
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("airfoil_low_re_polar")
    referred = {fk["referred_table"] for fk in fks}
    assert "airfoils" in referred


def test_downgrade_removes_tables(migration_db):
    engine, alembic_cfg = migration_db
    # Downgrade past our migration
    command.downgrade(alembic_cfg, "c3a5992b6f25")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    assert "airfoil_geometry" not in tables
    assert "airfoil_low_re_polar" not in tables
