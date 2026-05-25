"""gh-729: add step_path to fuselages for OpenVSP-import STEP storage

Revision ID: 011adab08ca7
Revises: 84ead4fd6131
Create Date: 2026-05-25 20:13:19.538764

Adds a single ``step_path`` nullable column to ``fuselages``. Stores
the relative path (under ``settings.ARTIFACTS_BASE_DIR``) of the
per-geom STEP file exported at OpenVSP-import time.

Autogen also flagged drift on ``airfoils``, ``rc_flight_profiles``,
and ``wing_xsec_details`` from earlier model edits — those are
tracked separately and intentionally not included here so the
gh-729 diff stays focused.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '011adab08ca7'
down_revision: Union[str, None] = '84ead4fd6131'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('fuselages', sa.Column('step_path', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fuselages', 'step_path')
