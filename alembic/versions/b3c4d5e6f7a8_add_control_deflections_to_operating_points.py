"""add control_deflections to operating_points

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-05-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add control_deflections column to operating_points."""
    op.add_column('operating_points', sa.Column('control_deflections', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove control_deflections column from operating_points."""
    op.drop_column('operating_points', 'control_deflections')
