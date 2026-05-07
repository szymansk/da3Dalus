"""add flight_envelopes table

Revision ID: a4f26dfb6c22
Revises: c5d6e7f8a9b0
Create Date: 2026-05-07 20:16:45.597815

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4f26dfb6c22"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "flight_envelopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aeroplane_id", sa.Integer(), nullable=False),
        sa.Column("vn_curve_json", sa.JSON(), nullable=False),
        sa.Column("kpis_json", sa.JSON(), nullable=False),
        sa.Column("markers_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_snapshot", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["aeroplane_id"], ["aeroplanes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_flight_envelopes_aeroplane_id"), "flight_envelopes", ["aeroplane_id"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_flight_envelopes_aeroplane_id"), table_name="flight_envelopes")
    op.drop_table("flight_envelopes")
