"""add airfoils table

Revision ID: 09316cc77273
Revises: bfb7cc64edfa
Create Date: 2026-04-25 18:15:13.775406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09316cc77273'
down_revision: Union[str, None] = 'bfb7cc64edfa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "airfoils",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("coordinates", sa.JSON(), nullable=False),
        sa.Column("source_file", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("airfoils")
