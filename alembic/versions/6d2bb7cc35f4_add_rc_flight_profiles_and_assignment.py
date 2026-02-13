"""add rc flight profiles and aeroplane assignment

Revision ID: 6d2bb7cc35f4
Revises: 1294198940a9
Create Date: 2026-02-13 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6d2bb7cc35f4"
down_revision: Union[str, None] = "1294198940a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rc_flight_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("environment", sa.JSON(), nullable=False),
        sa.Column("goals", sa.JSON(), nullable=False),
        sa.Column("handling", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_rc_flight_profiles_name"),
    )
    with op.batch_alter_table("aeroplanes", schema=None) as batch_op:
        batch_op.add_column(sa.Column("flight_profile_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_aeroplanes_flight_profile_id", ["flight_profile_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_aeroplanes_flight_profile_id",
            "rc_flight_profiles",
            ["flight_profile_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("aeroplanes", schema=None) as batch_op:
        batch_op.drop_constraint("fk_aeroplanes_flight_profile_id", type_="foreignkey")
        batch_op.drop_index("ix_aeroplanes_flight_profile_id")
        batch_op.drop_column("flight_profile_id")

    op.drop_table("rc_flight_profiles")
