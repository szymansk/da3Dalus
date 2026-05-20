"""seed slope_soarer mission preset

Revision ID: 294aeab71af5
Revises: 6063db4db84f
Create Date: 2026-05-20 09:00:00.000000

Adds the Slope Soarer mission preset (gh-582). RC-specific unpowered
high-wing-loading mission for slope/ridge soaring. Idempotent: skips
the insert if the preset id already exists (e.g. when the row was
already created at startup by ``seed_mission_presets``).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "294aeab71af5"
down_revision: Union[str, None] = "6063db4db84f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SLOPE_SOARER_ID = "slope_soarer"


def upgrade() -> None:
    """Insert the slope_soarer preset row if missing.

    The row is idempotent: re-running upgrade() on a DB that already
    has the row (typically because the app started and ran
    ``seed_mission_presets``) is a no-op.
    """
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT id FROM mission_presets WHERE id = :id"),
        {"id": _SLOPE_SOARER_ID},
    ).fetchone()
    if existing is not None:
        return

    from app.services.mission_preset_seed import SEED_PRESETS

    preset = next(p for p in SEED_PRESETS if p.id == _SLOPE_SOARER_ID)

    op.bulk_insert(
        sa.table(
            "mission_presets",
            sa.column("id", sa.String),
            sa.column("label", sa.String),
            sa.column("description", sa.String),
            sa.column("target_polygon", sa.JSON),
            sa.column("axis_ranges", sa.JSON),
            sa.column("suggested_estimates", sa.JSON),
        ),
        [
            {
                "id": preset.id,
                "label": preset.label,
                "description": preset.description,
                "target_polygon": preset.target_polygon,
                "axis_ranges": {k: list(v) for k, v in preset.axis_ranges.items()},
                "suggested_estimates": preset.suggested_estimates.model_dump(),
            }
        ],
    )


def downgrade() -> None:
    """Remove the slope_soarer preset row."""
    op.execute(
        sa.text("DELETE FROM mission_presets WHERE id = :id").bindparams(id=_SLOPE_SOARER_ID)
    )
