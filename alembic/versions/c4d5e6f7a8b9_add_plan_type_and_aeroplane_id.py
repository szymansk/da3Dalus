"""Add plan_type and aeroplane_id to construction_plans

Revision ID: c4d5e6f7a8b9
Revises: b3e2f1a4c7d9
Create Date: 2026-04-18
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3e2f1a4c7d9"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    with op.batch_alter_table("construction_plans") as batch_op:
        batch_op.add_column(
            sa.Column("plan_type", sa.String(), nullable=False, server_default="template"),
        )
        batch_op.add_column(
            sa.Column("aeroplane_id", sa.String(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_construction_plans_aeroplane_id",
            "aeroplanes",
            ["aeroplane_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("construction_plans") as batch_op:
        batch_op.drop_constraint("fk_construction_plans_aeroplane_id", type_="foreignkey")
        batch_op.drop_column("aeroplane_id")
        batch_op.drop_column("plan_type")
