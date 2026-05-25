"""gh-731: add solid_step_path to fuselages for sewed-Solid STEP storage

Revision ID: b5297a4b135a
Revises: 011adab08ca7
Create Date: 2026-05-25 21:00:00.000000

Adds a single ``solid_step_path`` nullable column to ``fuselages``.
Stores the relative path (under ``settings.ARTIFACTS_BASE_DIR``) of
the sewed/healed closed-Solid STEP file produced by
``openvsp_solid_sewing_service`` from the gh-729 Surface STEP at
OpenVSP-import time.

Companion to gh-729's ``step_path``: ``step_path`` is the raw
Surface-only VSP STEP; ``solid_step_path`` is the closed-Solid
healed version usable as input to the user's CAD-construction
pipeline (battery bay cuts, servo unions, carbon-tube bores).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b5297a4b135a"
down_revision: Union[str, None] = "011adab08ca7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("fuselages", sa.Column("solid_step_path", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("fuselages", "solid_step_path")
