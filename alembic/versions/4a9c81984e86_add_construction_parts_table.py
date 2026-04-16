"""add_construction_parts_table

Revision ID: 4a9c81984e86
Revises: b456b2d255b9
Create Date: 2026-04-16 08:00:40.241639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a9c81984e86'
down_revision: Union[str, None] = 'b456b2d255b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create construction_parts table (gh#57-g4h)."""
    op.create_table(
        'construction_parts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('aeroplane_id', sa.String(), nullable=False, index=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('volume_mm3', sa.Float(), nullable=True),
        sa.Column('area_mm2', sa.Float(), nullable=True),
        sa.Column('bbox_x_mm', sa.Float(), nullable=True),
        sa.Column('bbox_y_mm', sa.Float(), nullable=True),
        sa.Column('bbox_z_mm', sa.Float(), nullable=True),
        sa.Column(
            'material_component_id',
            sa.Integer(),
            sa.ForeignKey('components.id'),
            nullable=True,
        ),
        sa.Column(
            'locked',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('0'),
        ),
        sa.Column('thumbnail_url', sa.String(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop construction_parts table."""
    op.drop_table('construction_parts')
