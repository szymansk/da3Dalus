"""gh-1157: lower-half super-ellipse exponent on fuselage cross-sections

Adds the nullable ``fuselage_xsecs.n_lower``. NULL keeps every existing
section symmetric (the lower half uses ``n``), so no backfill is needed.

Revision ID: a1157f5e11a0
Revises: d8015f98814c
Create Date: 2026-10-05 08:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1157f5e11a0"
down_revision: Union[str, None] = "d8015f98814c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the lower-half exponent column."""
    op.add_column("fuselage_xsecs", sa.Column("n_lower", sa.Float(), nullable=True))


def downgrade() -> None:
    """Drop the lower-half exponent column."""
    with op.batch_alter_table("fuselage_xsecs") as batch_op:
        batch_op.drop_column("n_lower")
