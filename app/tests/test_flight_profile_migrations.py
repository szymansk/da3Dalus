from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect



def test_alembic_upgrade_head_creates_flight_profile_schema(tmp_path):
    db_path = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)

    assert "rc_flight_profiles" in inspector.get_table_names()

    aeroplane_columns = {col["name"] for col in inspector.get_columns("aeroplanes")}
    assert "flight_profile_id" in aeroplane_columns
