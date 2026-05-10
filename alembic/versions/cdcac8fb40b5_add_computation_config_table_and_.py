"""add computation config table and assumption context column

Revision ID: cdcac8fb40b5
Revises: 4705ef4e571b
Create Date: 2026-05-10 12:31:45.716338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdcac8fb40b5'
down_revision: Union[str, None] = '4705ef4e571b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Spurious drift artifacts removed — only real schema changes below.
    op.create_table('aircraft_computation_config',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('aeroplane_id', sa.Integer(), nullable=False),
    sa.Column('coarse_alpha_min_deg', sa.Float(), nullable=False),
    sa.Column('coarse_alpha_max_deg', sa.Float(), nullable=False),
    sa.Column('coarse_alpha_step_deg', sa.Float(), nullable=False),
    sa.Column('fine_alpha_margin_deg', sa.Float(), nullable=False),
    sa.Column('fine_alpha_step_deg', sa.Float(), nullable=False),
    sa.Column('fine_velocity_count', sa.Integer(), nullable=False),
    sa.Column('debounce_seconds', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['aeroplane_id'], ['aeroplanes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('aeroplane_id', name='uq_computation_config_aeroplane')
    )
    op.create_index(op.f('ix_aircraft_computation_config_aeroplane_id'), 'aircraft_computation_config', ['aeroplane_id'], unique=False)
    op.add_column('aeroplanes', sa.Column('assumption_computation_context', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('aeroplanes', 'assumption_computation_context')
    op.drop_index(op.f('ix_aircraft_computation_config_aeroplane_id'), table_name='aircraft_computation_config')
    op.drop_table('aircraft_computation_config')
