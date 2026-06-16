"""add variant column to propeller_polars (gh-999)

Revision ID: ee9fd32e8e90
Revises: 11b6fc7c9e67
Create Date: 2026-06-16 07:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ee9fd32e8e90"
down_revision: Union[str, None] = "11b6fc7c9e67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add variant column to propeller_polars (gh-999).

    Additive migration — existing rows receive an empty string default.
    This captures the APC propeller variant suffix (e.g. 'E' for electric,
    'M-JK' for marine, '' for standard props).
    """
    op.add_column(
        "propeller_polars",
        sa.Column(
            "variant",
            sa.String(),
            nullable=True,
            server_default="",
        ),
    )


def downgrade() -> None:
    """Remove variant column from propeller_polars."""
    op.drop_column("propeller_polars", "variant")
