"""add trim_enrichment to operating_points

Revision ID: 4705ef4e571b
Revises: 6aa821735324
Create Date: 2026-05-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4705ef4e571b"
down_revision: Union[str, None] = "6aa821735324"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trim_enrichment column to operating_points."""
    op.add_column("operating_points", sa.Column("trim_enrichment", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove trim_enrichment column from operating_points."""
    op.drop_column("operating_points", "trim_enrichment")
