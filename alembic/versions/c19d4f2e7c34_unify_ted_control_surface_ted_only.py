"""unify TED/control-surface persistence to TED-only

Revision ID: c19d4f2e7c34
Revises: 4b4f6929f284
Create Date: 2026-02-17 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c19d4f2e7c34"
down_revision: Union[str, None] = "4b4f6929f284"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(connection, table_name: str) -> bool:
    inspector = sa.inspect(connection)
    return table_name in inspector.get_table_names()


def _backfill_ted_from_control_surfaces() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()

    if not _has_table(connection, "control_surfaces"):
        return

    control_surfaces = sa.Table("control_surfaces", metadata, autoload_with=connection)
    details = sa.Table("wing_xsec_details", metadata, autoload_with=connection)
    ted_table = sa.Table("wing_xsec_trailing_edge_devices", metadata, autoload_with=connection)

    rows = connection.execute(
        sa.select(
            control_surfaces.c.wing_xsec_id,
            control_surfaces.c.name,
            control_surfaces.c.hinge_point,
            control_surfaces.c.symmetric,
            control_surfaces.c.deflection,
        )
    ).mappings().all()

    for row in rows:
        wing_xsec_id = row["wing_xsec_id"]
        if wing_xsec_id is None:
            continue

        detail_id = connection.execute(
            sa.select(details.c.id).where(details.c.wing_xsec_id == wing_xsec_id)
        ).scalar_one_or_none()

        if detail_id is None:
            result = connection.execute(sa.insert(details).values(wing_xsec_id=wing_xsec_id))
            inserted = result.inserted_primary_key
            detail_id = inserted[0] if inserted else None

        if detail_id is None:
            detail_id = connection.execute(
                sa.select(details.c.id).where(details.c.wing_xsec_id == wing_xsec_id)
            ).scalar_one_or_none()

        if detail_id is None:
            continue

        ted_row = connection.execute(
            sa.select(ted_table).where(ted_table.c.wing_xsec_detail_id == detail_id)
        ).mappings().first()

        cs_hinge = row["hinge_point"]
        cs_deflection = float(row["deflection"] or 0.0)

        if ted_row is None:
            connection.execute(
                sa.insert(ted_table).values(
                    wing_xsec_detail_id=detail_id,
                    name=row["name"],
                    rel_chord_root=cs_hinge,
                    rel_chord_tip=cs_hinge,
                    symmetric=row["symmetric"],
                    deflection_deg=cs_deflection,
                )
            )
            continue

        values = {}
        if ted_row.get("name") is None:
            values["name"] = row["name"]
        if ted_row.get("rel_chord_root") is None:
            values["rel_chord_root"] = cs_hinge
        if ted_row.get("rel_chord_tip") is None and cs_hinge is not None:
            values["rel_chord_tip"] = cs_hinge
        if ted_row.get("symmetric") is None:
            values["symmetric"] = row["symmetric"]
        if ted_row.get("deflection_deg") is None:
            values["deflection_deg"] = cs_deflection

        if values:
            connection.execute(
                ted_table.update().where(ted_table.c.id == ted_row["id"]).values(**values)
            )


def _backfill_control_surfaces_from_ted() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()

    if not _has_table(connection, "control_surfaces"):
        return

    control_surfaces = sa.Table("control_surfaces", metadata, autoload_with=connection)
    details = sa.Table("wing_xsec_details", metadata, autoload_with=connection)
    ted_table = sa.Table("wing_xsec_trailing_edge_devices", metadata, autoload_with=connection)

    ted_rows = connection.execute(
        sa.select(
            details.c.wing_xsec_id,
            ted_table.c.name,
            ted_table.c.rel_chord_root,
            ted_table.c.symmetric,
            ted_table.c.deflection_deg,
        ).select_from(
            ted_table.join(details, ted_table.c.wing_xsec_detail_id == details.c.id)
        )
    ).mappings().all()

    for row in ted_rows:
        wing_xsec_id = row["wing_xsec_id"]
        if wing_xsec_id is None:
            continue

        existing = connection.execute(
            sa.select(control_surfaces.c.id).where(control_surfaces.c.wing_xsec_id == wing_xsec_id)
        ).scalar_one_or_none()
        if existing is not None:
            continue

        connection.execute(
            sa.insert(control_surfaces).values(
                wing_xsec_id=wing_xsec_id,
                name=row["name"] or "Control Surface",
                hinge_point=0.8 if row["rel_chord_root"] is None else row["rel_chord_root"],
                symmetric=True if row["symmetric"] is None else row["symmetric"],
                deflection=0.0 if row["deflection_deg"] is None else row["deflection_deg"],
            )
        )


def upgrade() -> None:
    op.add_column(
        "wing_xsec_trailing_edge_devices",
        sa.Column("deflection_deg", sa.Float(), nullable=True),
    )

    _backfill_ted_from_control_surfaces()

    connection = op.get_bind()
    if _has_table(connection, "control_surfaces"):
        op.drop_table("control_surfaces")


def downgrade() -> None:
    op.create_table(
        "control_surfaces",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hinge_point", sa.Float(), nullable=True),
        sa.Column("symmetric", sa.Boolean(), nullable=True),
        sa.Column("deflection", sa.Float(), nullable=True),
        sa.Column("wing_xsec_id", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["wing_xsec_id"], ["wing_xsecs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_control_surfaces_id"), "control_surfaces", ["id"], unique=False)

    _backfill_control_surfaces_from_ted()

    with op.batch_alter_table("wing_xsec_trailing_edge_devices") as batch_op:
        batch_op.drop_column("deflection_deg")
