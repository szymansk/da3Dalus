"""extend operating points for generated aircraft-specific sets

Revision ID: 1f3b9c42e3aa
Revises: 9b7e11e8de24
Create Date: 2026-02-13 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f3b9c42e3aa"
down_revision: Union[str, None] = "9b7e11e8de24"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("operating_points", schema=None) as batch_op:
        batch_op.add_column(sa.Column("aircraft_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("config", sa.String(), nullable=False, server_default="clean"))
        batch_op.add_column(sa.Column("status", sa.String(), nullable=False, server_default="NOT_TRIMMED"))
        batch_op.add_column(sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("controls", sa.JSON(), nullable=False, server_default="{}"))
        batch_op.create_index("ix_operating_points_aircraft_id", ["aircraft_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_operating_points_aircraft_id",
            "aeroplanes",
            ["aircraft_id"],
            ["id"],
        )

    with op.batch_alter_table("operating_pointsets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("aircraft_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_flight_profile_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_operating_pointsets_aircraft_id", ["aircraft_id"], unique=False)
        batch_op.create_index("ix_operating_pointsets_source_flight_profile_id", ["source_flight_profile_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_operating_pointsets_aircraft_id",
            "aeroplanes",
            ["aircraft_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_operating_pointsets_source_flight_profile_id",
            "rc_flight_profiles",
            ["source_flight_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("operating_pointsets", schema=None) as batch_op:
        batch_op.drop_constraint("fk_operating_pointsets_source_flight_profile_id", type_="foreignkey")
        batch_op.drop_constraint("fk_operating_pointsets_aircraft_id", type_="foreignkey")
        batch_op.drop_index("ix_operating_pointsets_source_flight_profile_id")
        batch_op.drop_index("ix_operating_pointsets_aircraft_id")
        batch_op.drop_column("source_flight_profile_id")
        batch_op.drop_column("aircraft_id")

    with op.batch_alter_table("operating_points", schema=None) as batch_op:
        batch_op.drop_constraint("fk_operating_points_aircraft_id", type_="foreignkey")
        batch_op.drop_index("ix_operating_points_aircraft_id")
        batch_op.drop_column("controls")
        batch_op.drop_column("warnings")
        batch_op.drop_column("status")
        batch_op.drop_column("config")
        batch_op.drop_column("aircraft_id")
