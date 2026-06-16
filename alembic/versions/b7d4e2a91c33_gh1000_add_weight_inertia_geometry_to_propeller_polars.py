"""gh-1000: add weight/inertia/geometry to propeller_polars

Revision ID: b7d4e2a91c33
Revises: e2a35c6eac69
Create Date: 2026-06-17 00:30:00.000000

Additive migration enriching propeller_polars with mass / inertia / blade
geometry sourced from APC PE0 performance files (and cross-checked against the
PROP-DATA xlsx). All columns are nullable — existing rows keep NULL until the
PE0 import backfills them.

Units are normalised at the service layer (PE0 reports kg and kg-m**2);
weight is stored in grams, inertia in kg-m**2.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d4e2a91c33"
down_revision: Union[str, None] = "e2a35c6eac69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add weight_g, inertia_kg_m2, geometry columns to propeller_polars."""
    op.add_column(
        "propeller_polars",
        sa.Column("weight_g", sa.Float(), nullable=True),
    )
    op.add_column(
        "propeller_polars",
        sa.Column("inertia_kg_m2", sa.Float(), nullable=True),
    )
    # Per-blade-station geometry (chord/pitch/thickness/sweep/rake/…) as JSON.
    op.add_column(
        "propeller_polars",
        sa.Column("geometry", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop the gh-1000 enrichment columns."""
    op.drop_column("propeller_polars", "geometry")
    op.drop_column("propeller_polars", "inertia_kg_m2")
    op.drop_column("propeller_polars", "weight_g")
