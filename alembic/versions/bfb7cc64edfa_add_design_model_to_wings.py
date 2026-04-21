"""add design_model to wings

Revision ID: bfb7cc64edfa
Revises: c4d5e6f7a8b9
Create Date: 2026-04-21 13:20:13.475990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bfb7cc64edfa'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add design_model discriminator column to wings table."""
    op.add_column(
        'wings',
        sa.Column('design_model', sa.String(), nullable=False, server_default='wc'),
    )


def downgrade() -> None:
    """Remove design_model column from wings table."""
    op.drop_column('wings', 'design_model')
