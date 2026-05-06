"""add design_assumptions table

Revision ID: a1b2c3d4e5f6
Revises: b2ce6f00fe42
Create Date: 2026-05-06 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'b2ce6f00fe42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the design_assumptions table."""
    op.create_table(
        'design_assumptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('aeroplane_id', sa.Integer(), nullable=False),
        sa.Column('parameter_name', sa.String(), nullable=False),
        sa.Column('estimate_value', sa.Float(), nullable=False),
        sa.Column('calculated_value', sa.Float(), nullable=True),
        sa.Column('calculated_source', sa.String(), nullable=True),
        sa.Column('active_source', sa.String(), nullable=False, server_default='ESTIMATE'),
        sa.Column('divergence_pct', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['aeroplane_id'], ['aeroplanes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aeroplane_id', 'parameter_name', name='uq_assumption_aeroplane_param'),
    )
    op.create_index(op.f('ix_design_assumptions_aeroplane_id'), 'design_assumptions', ['aeroplane_id'], unique=False)


def downgrade() -> None:
    """Drop the design_assumptions table."""
    op.drop_index(op.f('ix_design_assumptions_aeroplane_id'), table_name='design_assumptions')
    op.drop_table('design_assumptions')
