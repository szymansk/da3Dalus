"""gh-1428: section and material of a spar

Adds ``wing_xsec_spares.section`` (JSON, tagged by ``shape``, every dimension in mm like the other
dimensional columns of the table, gh-402) and ``wing_xsec_spares.material`` (the name of a
``material`` component). Both are NULL on every existing row: nothing is inferred from the pocket.

Revision ID: 054bdccea9a7
Revises: ad6c09905023
Create Date: 2026-11-19 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "054bdccea9a7"
down_revision: Union[str, None] = "ad6c09905023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the section and material columns."""
    op.add_column("wing_xsec_spares", sa.Column("section", sa.JSON(), nullable=True))
    op.add_column("wing_xsec_spares", sa.Column("material", sa.String(), nullable=True))


def downgrade() -> None:
    """Drop the section and material columns."""
    with op.batch_alter_table("wing_xsec_spares") as batch_op:
        batch_op.drop_column("material")
        batch_op.drop_column("section")
