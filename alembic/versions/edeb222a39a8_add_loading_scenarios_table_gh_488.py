"""add loading_scenarios table (gh-488)

Revision ID: edeb222a39a8
Revises: cdcac8fb40b5
Create Date: 2026-05-13 10:17:00.406132

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edeb222a39a8'
down_revision: Union[str, None] = 'cdcac8fb40b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add loading_scenarios table for CG envelope (gh-488)."""
    op.create_table(
        "loading_scenarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("aeroplane_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "aircraft_class", sa.String(), server_default="rc_trainer", nullable=False
        ),
        sa.Column(
            "component_overrides", sa.JSON(), server_default="{}", nullable=False
        ),
        sa.Column(
            "is_default", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["aeroplane_id"], ["aeroplanes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_loading_scenarios_aeroplane_id"),
        "loading_scenarios",
        ["aeroplane_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove loading_scenarios table."""
    op.drop_index(
        op.f("ix_loading_scenarios_aeroplane_id"), table_name="loading_scenarios"
    )
    op.drop_table("loading_scenarios")
