"""add wing xsec detail tables for full wing configuration

Revision ID: 4b4f6929f284
Revises: 1f3b9c42e3aa
Create Date: 2026-02-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4b4f6929f284"
down_revision: Union[str, None] = "1f3b9c42e3aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_minimal_ted_from_control_surface() -> None:
    connection = op.get_bind()
    metadata = sa.MetaData()

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
        ).scalar()

        if detail_id is None:
            result = connection.execute(sa.insert(details).values(wing_xsec_id=wing_xsec_id))
            inserted = result.inserted_primary_key
            if inserted:
                detail_id = inserted[0]
            else:
                detail_id = connection.execute(
                    sa.select(details.c.id).where(details.c.wing_xsec_id == wing_xsec_id)
                ).scalar()

        existing_ted_id = connection.execute(
            sa.select(ted_table.c.id).where(ted_table.c.wing_xsec_detail_id == detail_id)
        ).scalar()

        if existing_ted_id is not None:
            continue

        deflection = abs(float(row["deflection"] or 0.0))
        connection.execute(
            sa.insert(ted_table).values(
                wing_xsec_detail_id=detail_id,
                name=row["name"],
                rel_chord_root=row["hinge_point"],
                rel_chord_tip=row["hinge_point"],
                positive_deflection_deg=deflection,
                negative_deflection_deg=deflection,
                symmetric=row["symmetric"],
            )
        )


def upgrade() -> None:
    op.create_table(
        "wing_xsec_details",
        sa.Column("wing_xsec_id", sa.Integer(), nullable=False),
        sa.Column("x_sec_type", sa.String(), nullable=True),
        sa.Column("tip_type", sa.String(), nullable=True),
        sa.Column("number_interpolation_points", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["wing_xsec_id"], ["wing_xsecs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wing_xsec_id"),
    )
    op.create_index(op.f("ix_wing_xsec_details_id"), "wing_xsec_details", ["id"], unique=False)

    op.create_table(
        "wing_xsec_spares",
        sa.Column("wing_xsec_detail_id", sa.Integer(), nullable=False),
        sa.Column("sort_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spare_support_dimension_width", sa.Float(), nullable=False),
        sa.Column("spare_support_dimension_height", sa.Float(), nullable=False),
        sa.Column("spare_position_factor", sa.Float(), nullable=True),
        sa.Column("spare_length", sa.Float(), nullable=True),
        sa.Column("spare_start", sa.Float(), nullable=True),
        sa.Column("spare_mode", sa.String(), nullable=True),
        sa.Column("spare_vector", sa.JSON(), nullable=True),
        sa.Column("spare_origin", sa.JSON(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["wing_xsec_detail_id"], ["wing_xsec_details.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wing_xsec_spares_id"), "wing_xsec_spares", ["id"], unique=False)

    op.create_table(
        "wing_xsec_trailing_edge_devices",
        sa.Column("wing_xsec_detail_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("rel_chord_root", sa.Float(), nullable=True),
        sa.Column("rel_chord_tip", sa.Float(), nullable=True),
        sa.Column("hinge_spacing", sa.Float(), nullable=True),
        sa.Column("side_spacing_root", sa.Float(), nullable=True),
        sa.Column("side_spacing_tip", sa.Float(), nullable=True),
        sa.Column("servo_placement", sa.String(), nullable=True),
        sa.Column("rel_chord_servo_position", sa.Float(), nullable=True),
        sa.Column("rel_length_servo_position", sa.Float(), nullable=True),
        sa.Column("positive_deflection_deg", sa.Float(), nullable=True),
        sa.Column("negative_deflection_deg", sa.Float(), nullable=True),
        sa.Column("trailing_edge_offset_factor", sa.Float(), nullable=True),
        sa.Column("hinge_type", sa.String(), nullable=True),
        sa.Column("symmetric", sa.Boolean(), nullable=True),
        sa.Column("servo_index", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["wing_xsec_detail_id"], ["wing_xsec_details.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("wing_xsec_detail_id"),
    )
    op.create_index(
        op.f("ix_wing_xsec_trailing_edge_devices_id"),
        "wing_xsec_trailing_edge_devices",
        ["id"],
        unique=False,
    )

    op.create_table(
        "wing_xsec_ted_servos",
        sa.Column("ted_id", sa.Integer(), nullable=False),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("leading_length", sa.Float(), nullable=True),
        sa.Column("latch_z", sa.Float(), nullable=True),
        sa.Column("latch_x", sa.Float(), nullable=True),
        sa.Column("latch_thickness", sa.Float(), nullable=True),
        sa.Column("latch_length", sa.Float(), nullable=True),
        sa.Column("cable_z", sa.Float(), nullable=True),
        sa.Column("screw_hole_lx", sa.Float(), nullable=True),
        sa.Column("screw_hole_d", sa.Float(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["ted_id"], ["wing_xsec_trailing_edge_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ted_id"),
    )
    op.create_index(op.f("ix_wing_xsec_ted_servos_id"), "wing_xsec_ted_servos", ["id"], unique=False)

    _backfill_minimal_ted_from_control_surface()



def downgrade() -> None:
    op.drop_index(op.f("ix_wing_xsec_ted_servos_id"), table_name="wing_xsec_ted_servos")
    op.drop_table("wing_xsec_ted_servos")

    op.drop_index(
        op.f("ix_wing_xsec_trailing_edge_devices_id"),
        table_name="wing_xsec_trailing_edge_devices",
    )
    op.drop_table("wing_xsec_trailing_edge_devices")

    op.drop_index(op.f("ix_wing_xsec_spares_id"), table_name="wing_xsec_spares")
    op.drop_table("wing_xsec_spares")

    op.drop_index(op.f("ix_wing_xsec_details_id"), table_name="wing_xsec_details")
    op.drop_table("wing_xsec_details")
