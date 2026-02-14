from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_operating_point_generation_migration_columns_exist(tmp_path):
    db_path = tmp_path / "op_migration_test.db"
    db_url = f"sqlite:///{db_path}"

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")

    inspector = inspect(create_engine(db_url))

    op_columns = {col["name"] for col in inspector.get_columns("operating_points")}
    assert "aircraft_id" in op_columns
    assert "config" in op_columns
    assert "status" in op_columns
    assert "warnings" in op_columns
    assert "controls" in op_columns

    opset_columns = {col["name"] for col in inspector.get_columns("operating_pointsets")}
    assert "aircraft_id" in opset_columns
    assert "source_flight_profile_id" in opset_columns
