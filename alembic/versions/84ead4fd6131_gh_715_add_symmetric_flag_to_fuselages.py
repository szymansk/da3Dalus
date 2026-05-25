"""gh-715: add symmetric flag to fuselages

Revision ID: 84ead4fd6131
Revises: a85f8972a5df
Create Date: 2026-05-25 12:16:22.690981

Adds a single ``symmetric`` boolean column to ``fuselages``. When True,
downstream consumers (ASB converter, CAD builder, viewer) mirror the
fuselage about the XZ plane — used for paired sub-fuselages like
landing-gear struts where OpenVSP stores only one side.

Default ``False`` so existing rows (main fuselages, which sit on the
symmetry plane themselves) keep their current behaviour. The
``server_default`` makes the column writable on existing rows during
the ALTER without a USING clause on SQLite.

The autogen also reported drift on ``airfoils``, ``rc_flight_profiles``,
and ``wing_xsec_details`` from earlier model edits that never produced
their own migrations — those are tracked separately and intentionally
**not** included here so the gh-715 diff stays focused.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '84ead4fd6131'
down_revision: Union[str, None] = 'a85f8972a5df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'fuselages',
        sa.Column('symmetric', sa.Boolean(), server_default='0', nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fuselages', 'symmetric')
