"""Add construction_plans table

Revision ID: b3e2f1a4c7d9
Revises: a7f1c3d2e5b8
Create Date: 2026-04-17
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "b3e2f1a4c7d9"
down_revision: Union[str, None] = "a7f1c3d2e5b8"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "construction_plans",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("tree_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("construction_plans")
