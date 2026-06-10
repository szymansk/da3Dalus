"""gh-951: add explicit dihedral column to wing_xsecs

Revision ID: a1c9f3e7b210
Revises: 6eca6229ba65
Create Date: 2026-06-10 09:00:00.000000

Persists each rib's local-x rotation (dihedral, degrees) explicitly,
mirroring how ``twist`` is already stored. The terminal rib's rotation
is NOT encoded in the ASB ``xyz_le`` geometry (it moves no outboard
station), so without an explicit column it cannot be reconstructed on
read and is silently lost on the WingConfig round-trip (gh-951).

Nullable: existing rows predate the column and keep the geometry-derived
dihedral on read until they are next written.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c9f3e7b210'
down_revision: Union[str, None] = '6eca6229ba65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('wing_xsecs', sa.Column('dihedral', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('wing_xsecs', 'dihedral')
