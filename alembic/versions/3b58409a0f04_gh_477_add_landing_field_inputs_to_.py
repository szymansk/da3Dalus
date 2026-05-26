"""gh-477 add landing field inputs to mission objectives

Revision ID: 3b58409a0f04
Revises: b5297a4b135a
Create Date: 2026-05-27 01:26:34.872233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3b58409a0f04'
down_revision: Union[str, None] = 'b5297a4b135a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the three optional landing-field inputs to mission_objectives.

    All three are nullable with no DB-layer default — the service layer
    fills in grass_short / 1.5 / None when the user has not set them.
    See gh-477 acceptance criteria.
    """
    with op.batch_alter_table("mission_objectives") as batch_op:
        batch_op.add_column(sa.Column("landing_surface", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("landing_safety_factor", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("available_field_length_m", sa.Float(), nullable=True))


def downgrade() -> None:
    """Drop the three columns added by the upgrade."""
    with op.batch_alter_table("mission_objectives") as batch_op:
        batch_op.drop_column("available_field_length_m")
        batch_op.drop_column("landing_safety_factor")
        batch_op.drop_column("landing_surface")
