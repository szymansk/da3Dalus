"""add stability_results table

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-05-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'stability_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('aeroplane_id', sa.Integer(), nullable=False),
        sa.Column('solver', sa.String(), nullable=False),
        sa.Column('neutral_point_x', sa.Float(), nullable=True),
        sa.Column('mac', sa.Float(), nullable=True),
        sa.Column('cg_x_used', sa.Float(), nullable=True),
        sa.Column('static_margin_pct', sa.Float(), nullable=True),
        sa.Column('stability_class', sa.String(), nullable=True),
        sa.Column('cg_range_forward', sa.Float(), nullable=True),
        sa.Column('cg_range_aft', sa.Float(), nullable=True),
        sa.Column('Cma', sa.Float(), nullable=True),
        sa.Column('Cnb', sa.Float(), nullable=True),
        sa.Column('Clb', sa.Float(), nullable=True),
        sa.Column('trim_alpha_deg', sa.Float(), nullable=True),
        sa.Column('trim_elevator_deg', sa.Float(), nullable=True),
        sa.Column('is_statically_stable', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_directionally_stable', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_laterally_stable', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='CURRENT'),
        sa.Column('geometry_hash', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['aeroplane_id'], ['aeroplanes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aeroplane_id', 'solver', name='uq_stability_aeroplane_solver'),
    )
    op.create_index(
        op.f('ix_stability_results_aeroplane_id'),
        'stability_results',
        ['aeroplane_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_stability_results_aeroplane_id'), table_name='stability_results')
    op.drop_table('stability_results')
