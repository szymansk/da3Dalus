"""gh-934 add wing_xsec_turbulators table

Revision ID: 6eca6229ba65
Revises: 15f45e64a7c0
Create Date: 2026-06-09 22:54:45.817319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eca6229ba65'
down_revision: Union[str, None] = '15f45e64a7c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add wing_xsec_turbulators table (gh-934 Slice 1)."""
    op.create_table(
        'wing_xsec_turbulators',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('wing_xsec_detail_id', sa.Integer(), nullable=False),
        sa.Column('form', sa.String(), nullable=True),
        sa.Column('height_mm', sa.Float(), nullable=True),
        sa.Column('position_root', sa.Float(), nullable=True),
        sa.Column('position_tip', sa.Float(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(
            ['wing_xsec_detail_id'], ['wing_xsec_details.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wing_xsec_detail_id'),
    )
    op.create_index(
        op.f('ix_wing_xsec_turbulators_id'), 'wing_xsec_turbulators', ['id'], unique=False
    )


def downgrade() -> None:
    """Drop wing_xsec_turbulators table."""
    op.drop_index(op.f('ix_wing_xsec_turbulators_id'), table_name='wing_xsec_turbulators')
    op.drop_table('wing_xsec_turbulators')
