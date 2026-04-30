"""add avl_geometry_files table

Revision ID: 87bb4e31e610
Revises: 09316cc77273
Create Date: 2026-04-30 21:58:28.225904

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87bb4e31e610'
down_revision: Union[str, None] = '09316cc77273'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'avl_geometry_files',
        sa.Column('aeroplane_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_dirty', sa.Boolean(), nullable=False),
        sa.Column('is_user_edited', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['aeroplane_id'], ['aeroplanes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aeroplane_id', name='uq_avl_geometry_files_aeroplane_id'),
    )
    op.create_index(
        op.f('ix_avl_geometry_files_aeroplane_id'),
        'avl_geometry_files',
        ['aeroplane_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_avl_geometry_files_id'),
        'avl_geometry_files',
        ['id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_avl_geometry_files_id'), table_name='avl_geometry_files')
    op.drop_index(
        op.f('ix_avl_geometry_files_aeroplane_id'), table_name='avl_geometry_files'
    )
    op.drop_table('avl_geometry_files')
