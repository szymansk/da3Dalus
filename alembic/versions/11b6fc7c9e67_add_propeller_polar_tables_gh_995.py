"""add propeller_polars and propeller_polar_samples tables (gh-995)

Revision ID: 11b6fc7c9e67
Revises: 1f320603c2cf
Create Date: 2026-06-16 06:02:02.813209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11b6fc7c9e67'
down_revision: Union[str, None] = '1f320603c2cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add propeller_polars and propeller_polar_samples tables (gh-995).

    Additive migration only — no existing tables are touched.
    """
    op.create_table(
        'propeller_polars',
        sa.Column('manufacturer', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('model_ref', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_version', sa.String(), nullable=True),
        sa.Column('diameter_in', sa.Float(), nullable=True),
        sa.Column('pitch_in', sa.Float(), nullable=True),
        sa.Column('blades', sa.Integer(), nullable=True),
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
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_propeller_polars_id', 'propeller_polars', ['id'], unique=False)
    op.create_index('ix_propeller_polars_manufacturer', 'propeller_polars', ['manufacturer'], unique=False)
    op.create_index('ix_propeller_polars_name', 'propeller_polars', ['name'], unique=False)

    op.create_table(
        'propeller_polar_samples',
        sa.Column('propeller_id', sa.Integer(), nullable=False),
        sa.Column('rpm', sa.Integer(), nullable=False),
        sa.Column('J', sa.Float(), nullable=False),
        sa.Column('Ct', sa.Float(), nullable=False),
        sa.Column('Cp', sa.Float(), nullable=False),
        sa.Column('Pe', sa.Float(), nullable=True),
        sa.Column('PWR_W', sa.Float(), nullable=True),
        sa.Column('Torque_Nm', sa.Float(), nullable=True),
        sa.Column('Thrust_N', sa.Float(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['propeller_id'], ['propeller_polars.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_propeller_polar_samples_id', 'propeller_polar_samples', ['id'], unique=False)
    op.create_index('ix_propeller_polar_samples_propeller_id', 'propeller_polar_samples', ['propeller_id'], unique=False)
    op.create_index('ix_propeller_polar_samples_rpm', 'propeller_polar_samples', ['rpm'], unique=False)


def downgrade() -> None:
    """Drop propeller polar tables (additive, safe to revert)."""
    op.drop_index('ix_propeller_polar_samples_rpm', table_name='propeller_polar_samples')
    op.drop_index('ix_propeller_polar_samples_propeller_id', table_name='propeller_polar_samples')
    op.drop_index('ix_propeller_polar_samples_id', table_name='propeller_polar_samples')
    op.drop_table('propeller_polar_samples')
    op.drop_index('ix_propeller_polars_name', table_name='propeller_polars')
    op.drop_index('ix_propeller_polars_manufacturer', table_name='propeller_polars')
    op.drop_index('ix_propeller_polars_id', table_name='propeller_polars')
    op.drop_table('propeller_polars')
