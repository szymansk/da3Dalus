"""gh-772 add mix gains + differential_ratio to trailing edge devices

Revision ID: c3a5992b6f25
Revises: 3b58409a0f04
Create Date: 2026-05-30

Additive, nullable-with-default columns for mixed control-surface support
(elevon/flaperon/ruddervator mix gains + aileron differential ratio).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3a5992b6f25"
down_revision = "3b58409a0f04"
branch_labels = None
depends_on = None

_TABLE = "wing_xsec_trailing_edge_devices"
_COLUMNS = ("mix_gain_primary", "mix_gain_secondary", "differential_ratio")


def upgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in _COLUMNS:
            batch_op.add_column(
                sa.Column(col, sa.Float(), nullable=False, server_default="1.0")
            )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch_op:
        for col in _COLUMNS:
            batch_op.drop_column(col)
