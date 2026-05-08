"""add role and label to ted

Revision ID: 6aa821735324
Revises: a4f26dfb6c22
Create Date: 2026-05-08 22:13:13.360153

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6aa821735324'
down_revision: Union[str, None] = 'a4f26dfb6c22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _infer_role(name: str | None) -> str:
    if not name:
        return "other"
    n = name.strip().lower()
    if "stabilator" in n:
        return "stabilator"
    if "elevon" in n:
        return "elevon"
    if "elevator" in n:
        return "elevator"
    if "aileron" in n:
        return "aileron"
    if "rudder" in n:
        return "rudder"
    if "flap" in n:
        return "flap"
    if "spoiler" in n:
        return "spoiler"
    return "other"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('wing_xsec_trailing_edge_devices', sa.Column('role', sa.String(), server_default='other', nullable=False))
    op.add_column('wing_xsec_trailing_edge_devices', sa.Column('label', sa.String(), nullable=True))

    # Backfill: infer role from existing name values; copy name → label
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM wing_xsec_trailing_edge_devices")).fetchall()
    for row in rows:
        role = _infer_role(row.name)
        conn.execute(
            sa.text(
                "UPDATE wing_xsec_trailing_edge_devices SET role = :role, label = :label WHERE id = :id"
            ),
            {"role": role, "label": row.name, "id": row.id},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('wing_xsec_trailing_edge_devices', 'label')
    op.drop_column('wing_xsec_trailing_edge_devices', 'role')
