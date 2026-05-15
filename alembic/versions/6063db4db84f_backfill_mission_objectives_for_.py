"""backfill mission_objectives for existing aeroplanes

Revision ID: 6063db4db84f
Revises: 7fd2cf7284ce
Create Date: 2026-05-15 23:53:51.672732

Phase 3 of the Mission Tab redesign (gh-548). After gh-546 introduced
the new ``mission_objectives`` table, existing aeroplanes had no row.
This migration backfills a default "trainer" objective for every
aeroplane that doesn't already have one. The insert is idempotent —
re-running upgrade() on a partially-backfilled database does no harm.

The defaults mirror ``_default_objective`` in
``app.services.mission_objective_service``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6063db4db84f"
down_revision: Union[str, None] = "7fd2cf7284ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DEFAULT_TRAINER = {
    "mission_type": "trainer",
    "target_cruise_mps": 18.0,
    "target_stall_safety": 1.8,
    "target_maneuver_n": 3.0,
    "target_glide_ld": 12.0,
    "target_climb_energy": 22.0,
    "target_wing_loading_n_m2": 412.0,
    "target_field_length_m": 50.0,
    "available_runway_m": 50.0,
    "runway_type": "grass",
    "t_static_N": 18.0,
    "takeoff_mode": "runway",
}


def upgrade() -> None:
    """Insert a default trainer MissionObjective for any aeroplane missing one.

    Idempotent: aeroplanes that already have a row (e.g. created via the
    PUT /mission-objectives endpoint between gh-546 landing and this
    migration running) are skipped.
    """
    conn = op.get_bind()
    missing_ids = [
        row[0]
        for row in conn.execute(
            sa.text(
                """
                SELECT a.id
                FROM aeroplanes a
                LEFT JOIN mission_objectives m ON m.aeroplane_id = a.id
                WHERE m.aeroplane_id IS NULL
                """
            )
        ).fetchall()
    ]
    if not missing_ids:
        return

    op.bulk_insert(
        sa.table(
            "mission_objectives",
            sa.column("aeroplane_id", sa.Integer),
            sa.column("mission_type", sa.String),
            sa.column("target_cruise_mps", sa.Float),
            sa.column("target_stall_safety", sa.Float),
            sa.column("target_maneuver_n", sa.Float),
            sa.column("target_glide_ld", sa.Float),
            sa.column("target_climb_energy", sa.Float),
            sa.column("target_wing_loading_n_m2", sa.Float),
            sa.column("target_field_length_m", sa.Float),
            sa.column("available_runway_m", sa.Float),
            sa.column("runway_type", sa.String),
            sa.column("t_static_N", sa.Float),
            sa.column("takeoff_mode", sa.String),
        ),
        [{"aeroplane_id": aid, **_DEFAULT_TRAINER} for aid in missing_ids],
    )


def downgrade() -> None:
    """Remove any MissionObjective rows whose values exactly match the
    backfill defaults — leave user-modified rows alone.

    The match-by-value heuristic is the safest reversal: we cannot tell
    which rows were created by the backfill vs. by the user, so we
    delete only rows whose every field still equals the trainer default.
    """
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM mission_objectives
            WHERE mission_type = :mission_type
              AND target_cruise_mps = :target_cruise_mps
              AND target_stall_safety = :target_stall_safety
              AND target_maneuver_n = :target_maneuver_n
              AND target_glide_ld = :target_glide_ld
              AND target_climb_energy = :target_climb_energy
              AND target_wing_loading_n_m2 = :target_wing_loading_n_m2
              AND target_field_length_m = :target_field_length_m
              AND available_runway_m = :available_runway_m
              AND runway_type = :runway_type
              AND t_static_N = :t_static_N
              AND takeoff_mode = :takeoff_mode
            """
        ),
        _DEFAULT_TRAINER,
    )
