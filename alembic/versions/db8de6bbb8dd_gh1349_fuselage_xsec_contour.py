"""gh-1349: optional point contour on fuselage cross-sections

Adds the nullable JSON column ``fuselage_xsecs.contour``: the measured right half outline,
``[[y, z], ...]`` in metres relative to the section's ``xyz`` (geometry format 7.1b). NULL keeps
every existing section a super-ellipse, so no backfill is needed.

Revision ID: db8de6bbb8dd
Revises: d90a2284bf83
Create Date: 2026-11-04 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "db8de6bbb8dd"
down_revision: Union[str, None] = "d90a2284bf83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the contour column."""
    op.add_column("fuselage_xsecs", sa.Column("contour", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Drop the contour column."""
    with op.batch_alter_table("fuselage_xsecs") as batch_op:
        batch_op.drop_column("contour")
