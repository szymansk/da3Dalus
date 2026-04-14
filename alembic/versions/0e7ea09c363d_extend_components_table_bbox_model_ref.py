"""extend_components_table_bbox_model_ref

Revision ID: 0e7ea09c363d
Revises: 04b8c856eab9
Create Date: 2026-04-14 23:06:53.789992

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e7ea09c363d'
down_revision: Union[str, None] = '04b8c856eab9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add bbox and model_ref columns to components table."""
    op.add_column('components', sa.Column('bbox_x_mm', sa.Float(), nullable=True))
    op.add_column('components', sa.Column('bbox_y_mm', sa.Float(), nullable=True))
    op.add_column('components', sa.Column('bbox_z_mm', sa.Float(), nullable=True))
    op.add_column('components', sa.Column('model_ref', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove bbox and model_ref columns from components table."""
    op.drop_column('components', 'model_ref')
    op.drop_column('components', 'bbox_z_mm')
    op.drop_column('components', 'bbox_y_mm')
    op.drop_column('components', 'bbox_x_mm')
