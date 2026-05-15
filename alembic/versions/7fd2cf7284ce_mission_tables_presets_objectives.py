"""mission tables: presets + objectives

Revision ID: 7fd2cf7284ce
Revises: edeb222a39a8
Create Date: 2026-05-15 21:58:19.572239

Phase 1 of the Mission Tab redesign (gh-546). Drops the legacy
placeholder ``mission_objectives`` table (introduced in revision
5b41e8c65a14), then creates the new ``mission_presets`` table seeded
with six presets, and the new ``mission_objectives`` table holding one
row per aeroplane (7 mission targets + field-performance inputs).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7fd2cf7284ce"
down_revision: Union[str, None] = "edeb222a39a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Drop legacy placeholder table (migration 5b41e8c65a14).
    # `if_exists=True` guards against partial DBs where the legacy
    # placeholder was never created (e.g. future migration chain refactors
    # that move the down_revision, or fresh DBs without the legacy index).
    op.drop_index(
        op.f("ix_mission_objectives_id"),
        table_name="mission_objectives",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_mission_objectives_aeroplane_id"),
        table_name="mission_objectives",
        if_exists=True,
    )
    op.drop_table("mission_objectives", if_exists=True)

    # 2. Create mission_presets.
    op.create_table(
        "mission_presets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False, server_default=""),
        sa.Column("target_polygon", sa.JSON(), nullable=False),
        sa.Column("axis_ranges", sa.JSON(), nullable=False),
        sa.Column("suggested_estimates", sa.JSON(), nullable=False),
    )

    # 3. Seed presets via bulk insert. Import locally to avoid model-load
    # order issues at module import time.
    from app.services.mission_preset_seed import SEED_PRESETS

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
                "id": p.id,
                "label": p.label,
                "description": p.description,
                "target_polygon": p.target_polygon,
                # JSON tuple -> list for storage
                "axis_ranges": {k: list(v) for k, v in p.axis_ranges.items()},
                "suggested_estimates": p.suggested_estimates.model_dump(),
            }
            for p in SEED_PRESETS
        ],
    )

    # 4. Create new mission_objectives (singular semantics: one row per aeroplane).
    op.create_table(
        "mission_objectives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "aeroplane_id",
            sa.Integer(),
            sa.ForeignKey("aeroplanes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "mission_type", sa.String(), nullable=False, server_default="trainer"
        ),
        sa.Column(
            "target_cruise_mps", sa.Float(), nullable=False, server_default="18.0"
        ),
        sa.Column(
            "target_stall_safety", sa.Float(), nullable=False, server_default="1.8"
        ),
        sa.Column(
            "target_maneuver_n", sa.Float(), nullable=False, server_default="3.0"
        ),
        sa.Column(
            "target_glide_ld", sa.Float(), nullable=False, server_default="12.0"
        ),
        sa.Column(
            "target_climb_energy", sa.Float(), nullable=False, server_default="22.0"
        ),
        sa.Column(
            "target_wing_loading_n_m2",
            sa.Float(),
            nullable=False,
            server_default="412.0",
        ),
        sa.Column(
            "target_field_length_m",
            sa.Float(),
            nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "available_runway_m",
            sa.Float(),
            nullable=False,
            server_default="50.0",
        ),
        sa.Column(
            "runway_type", sa.String(), nullable=False, server_default="grass"
        ),
        sa.Column("t_static_N", sa.Float(), nullable=False, server_default="18.0"),
        sa.Column(
            "takeoff_mode", sa.String(), nullable=False, server_default="runway"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse order: drop the new tables...
    op.drop_table("mission_objectives")
    op.drop_table("mission_presets")

    # ...then recreate the legacy mission_objectives placeholder
    # identical to revision 5b41e8c65a14.
    op.create_table(
        "mission_objectives",
        sa.Column("aeroplane_id", sa.Integer(), nullable=False),
        sa.Column("payload_kg", sa.Float(), nullable=True),
        sa.Column("target_flight_time_min", sa.Float(), nullable=True),
        sa.Column("maneuverability_class", sa.String(), nullable=True),
        sa.Column("size_envelope_length_mm", sa.Float(), nullable=True),
        sa.Column("size_envelope_width_mm", sa.Float(), nullable=True),
        sa.Column("size_envelope_height_mm", sa.Float(), nullable=True),
        sa.Column("engine_type", sa.String(), nullable=True),
        sa.Column("target_stall_speed_ms", sa.Float(), nullable=True),
        sa.Column("target_cruise_speed_ms", sa.Float(), nullable=True),
        sa.Column("target_top_speed_ms", sa.Float(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["aeroplane_id"], ["aeroplanes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_mission_objectives_aeroplane_id"),
        "mission_objectives",
        ["aeroplane_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_mission_objectives_id"),
        "mission_objectives",
        ["id"],
        unique=False,
    )
