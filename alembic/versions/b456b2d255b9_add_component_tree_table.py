"""add_component_tree_table

Revision ID: b456b2d255b9
Revises: 0e7ea09c363d
Create Date: 2026-04-14 23:13:57.506937

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b456b2d255b9'
down_revision: Union[str, None] = '0e7ea09c363d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create component_tree table."""
    op.create_table(
        'component_tree',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('aeroplane_id', sa.String(), nullable=False, index=True),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('component_tree.id'), nullable=True),
        sa.Column('sort_index', sa.Integer(), default=0),
        sa.Column('node_type', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('shape_key', sa.String(), nullable=True),
        sa.Column('shape_hash', sa.String(), nullable=True),
        sa.Column('volume_mm3', sa.Float(), nullable=True),
        sa.Column('area_mm2', sa.Float(), nullable=True),
        sa.Column('component_id', sa.Integer(), sa.ForeignKey('components.id'), nullable=True),
        sa.Column('quantity', sa.Integer(), default=1),
        sa.Column('pos_x', sa.Float(), default=0),
        sa.Column('pos_y', sa.Float(), default=0),
        sa.Column('pos_z', sa.Float(), default=0),
        sa.Column('rot_x', sa.Float(), default=0),
        sa.Column('rot_y', sa.Float(), default=0),
        sa.Column('rot_z', sa.Float(), default=0),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('components.id'), nullable=True),
        sa.Column('weight_override_g', sa.Float(), nullable=True),
        sa.Column('print_type', sa.String(), nullable=True),
        sa.Column('scale_factor', sa.Float(), default=1.0),
        sa.Column('synced_from', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop component_tree table."""
    op.drop_table('component_tree')
