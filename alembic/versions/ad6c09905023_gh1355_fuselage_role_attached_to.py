"""gh-1355: role and attached_to of a fuselage body

Adds ``fuselages.role`` (non-null, server default ``'fuselage'``: every existing body becomes a
fuselage, nothing is inferred from its name) and the nullable ``fuselages.attached_to`` (the name
of the body it sits on; NULL on every existing row).

Revision ID: ad6c09905023
Revises: db8de6bbb8dd
Create Date: 2026-11-05 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ad6c09905023"
down_revision: Union[str, None] = "db8de6bbb8dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the role and attached_to columns."""
    op.add_column(
        "fuselages",
        sa.Column("role", sa.String(), nullable=False, server_default="fuselage"),
    )
    op.add_column("fuselages", sa.Column("attached_to", sa.String(), nullable=True))


def downgrade() -> None:
    """Drop the role and attached_to columns."""
    with op.batch_alter_table("fuselages") as batch_op:
        batch_op.drop_column("attached_to")
        batch_op.drop_column("role")
