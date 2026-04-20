"""add rotation_point_rel_chord and dihedral_as_rotation to wing_xsec_details

Revision ID: 4f5bf40c80a5
Revises: c4d5e6f7a8b9
Create Date: 2026-04-20 21:57:41.346704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4f5bf40c80a5'
down_revision: Union[str, None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add airfoil detail columns for loss-free WingConfig roundtrip (#159)."""
    op.add_column('wing_xsec_details', sa.Column('rotation_point_rel_chord', sa.Float(), nullable=True))
    op.add_column('wing_xsec_details', sa.Column('dihedral_as_rotation_in_degrees', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove airfoil detail columns."""
    op.drop_column('wing_xsec_details', 'dihedral_as_rotation_in_degrees')
    op.drop_column('wing_xsec_details', 'rotation_point_rel_chord')
