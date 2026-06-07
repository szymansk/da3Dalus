"""gh-903: versioning DB model — branches table, aeroplanes versioning columns, drop design_versions

Revision ID: 15f45e64a7c0
Revises: 16cbb884a838
Create Date: 2026-06-07 00:00:00.000000

Changes:
- Create ``branches`` table (id, root_id, head_id, name, is_main, created_by, created_at).
- Add versioning columns on ``aeroplanes``:
    branch_id, predecessor_id, root_id, is_immutable, version_label,
    version_note, created_by, provenance_message_id, preview_png.
- Add FK constraints linking the new columns to ``branches`` and ``aeroplanes``.
- Drop ``design_versions`` table (JSON-snapshot system retired).
- Backfill: for every existing aeroplane, create a ``main`` branch
  (root_id=self, head_id=self, is_main=true) and point the aeroplane's
  root_id and branch_id at it.

Downgrade:
- Re-create ``design_versions`` (empty — JSON snapshots were never back-migrated).
- Drop the new columns from ``aeroplanes``.
- Drop the ``branches`` table.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "15f45e64a7c0"
down_revision: Union[str, None] = "16cbb884a838"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add branches table, versioning columns on aeroplanes, drop design_versions, backfill."""

    # ── 1. Create branches table ──────────────────────────────────────────────
    # root_id and head_id reference aeroplanes.id. Use use_alter=True (deferred FKs)
    # because aeroplanes.branch_id → branches.id creates a circular dependency.
    # SQLite ignores FK deferral but the constraint is still DDL-correct.
    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("root_id", sa.Integer(), nullable=False),
        sa.Column("head_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_main", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["root_id"],
            ["aeroplanes.id"],
            name="fk_branches_root_id",
            use_alter=True,
        ),
        sa.ForeignKeyConstraint(
            ["head_id"],
            ["aeroplanes.id"],
            name="fk_branches_head_id",
            use_alter=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 2. Add versioning columns to aeroplanes ───────────────────────────────
    with op.batch_alter_table("aeroplanes") as batch_op:
        batch_op.add_column(
            sa.Column("branch_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("predecessor_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("root_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "is_immutable",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("version_label", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("version_note", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("created_by", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("provenance_message_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("preview_png", sa.Text(), nullable=True)
        )
        # FK: aeroplanes.branch_id → branches.id (use_alter for circular dep)
        batch_op.create_foreign_key(
            "fk_aeroplanes_branch_id",
            "branches",
            ["branch_id"],
            ["id"],
            use_alter=True,
        )
        # Self-referential FKs
        batch_op.create_foreign_key(
            "fk_aeroplanes_predecessor_id",
            "aeroplanes",
            ["predecessor_id"],
            ["id"],
            use_alter=True,
        )
        batch_op.create_foreign_key(
            "fk_aeroplanes_root_id",
            "aeroplanes",
            ["root_id"],
            ["id"],
            use_alter=True,
        )
        # FK: provenance_message_id → copilot_messages.id
        batch_op.create_foreign_key(
            "fk_aeroplanes_provenance_msg",
            "copilot_messages",
            ["provenance_message_id"],
            ["id"],
            use_alter=True,
        )

    # ── 3. Backfill — create a main branch for every existing aeroplane ───────
    # NOTE: We use INSERT … RETURNING id instead of result.lastrowid because
    # lastrowid is None on PostgreSQL, silently leaving branch_id NULL for all
    # pre-existing aircraft.  Both SQLite ≥3.35 and PostgreSQL support RETURNING.
    conn = op.get_bind()
    aeroplanes = conn.execute(sa.text("SELECT id FROM aeroplanes")).fetchall()
    for row in aeroplanes:
        aeroplane_id = row[0]
        # Insert main branch using RETURNING to get the new PK portably.
        result = conn.execute(
            sa.text(
                "INSERT INTO branches (root_id, head_id, name, is_main, created_by)"
                " VALUES (:rid, :hid, 'main', :is_main, 'human')"
                " RETURNING id"
            ),
            {"rid": aeroplane_id, "hid": aeroplane_id, "is_main": True},
        )
        branch_id = result.fetchone()[0]

        # Point the aeroplane's versioning columns at its new main branch
        conn.execute(
            sa.text(
                "UPDATE aeroplanes"
                " SET root_id = :rid, branch_id = :bid, is_immutable = 0"
                " WHERE id = :aid"
            ),
            {"rid": aeroplane_id, "bid": branch_id, "aid": aeroplane_id},
        )

    # ── 4. Partial unique index: one main branch per lineage root ─────────────
    # Both SQLite (≥3.8) and PostgreSQL support partial indexes.  This enforces
    # the invariant at the DB level so concurrent writes can't create two main
    # branches for the same root_id.
    op.create_index(
        "uq_branches_one_main_per_root",
        "branches",
        ["root_id"],
        unique=True,
        postgresql_where=sa.text("is_main = true"),
        sqlite_where=sa.text("is_main = 1"),
    )

    # ── 5. Drop design_versions (JSON snapshot system retired) ────────────────
    op.drop_table("design_versions")


def downgrade() -> None:
    """Reverse gh-903: restore design_versions, drop versioning columns and branches."""

    # ── 1. Re-create design_versions (empty — snapshots were never back-migrated)
    op.create_table(
        "design_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("aeroplane_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("parent_version_id", sa.Integer(), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["aeroplane_id"], ["aeroplanes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_design_versions_aeroplane_id"),
        "design_versions",
        ["aeroplane_id"],
        unique=False,
    )

    # ── 2. Drop versioning columns from aeroplanes ────────────────────────────
    with op.batch_alter_table("aeroplanes") as batch_op:
        # SQLite batch mode drops FKs implicitly via table recreation.
        # Explicit drop_constraint calls are a no-op for SQLite but needed
        # for PostgreSQL compatibility.
        batch_op.drop_constraint("fk_aeroplanes_branch_id", type_="foreignkey")
        batch_op.drop_constraint("fk_aeroplanes_predecessor_id", type_="foreignkey")
        batch_op.drop_constraint("fk_aeroplanes_root_id", type_="foreignkey")
        batch_op.drop_constraint("fk_aeroplanes_provenance_msg", type_="foreignkey")
        batch_op.drop_column("branch_id")
        batch_op.drop_column("predecessor_id")
        batch_op.drop_column("root_id")
        batch_op.drop_column("is_immutable")
        batch_op.drop_column("version_label")
        batch_op.drop_column("version_note")
        batch_op.drop_column("created_by")
        batch_op.drop_column("provenance_message_id")
        batch_op.drop_column("preview_png")

    # ── 3. Drop branches table (index dropped implicitly with the table) ──────
    # Drop the deferred FK constraints on branches before dropping the table.
    with op.batch_alter_table("branches") as batch_op:
        batch_op.drop_constraint("fk_branches_root_id", type_="foreignkey")
        batch_op.drop_constraint("fk_branches_head_id", type_="foreignkey")
        batch_op.drop_index("uq_branches_one_main_per_root")
    op.drop_table("branches")
