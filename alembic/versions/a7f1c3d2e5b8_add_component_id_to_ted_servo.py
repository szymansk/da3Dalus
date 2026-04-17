"""Add component_id FK to wing_xsec_ted_servos

Links a servo assignment back to its Component Library entry so the
frontend can display the servo name/manufacturer. Nullable because
servos created via API with raw dimensions have no library origin.

Revision ID: a7f1c3d2e5b8
Revises: 4b41e90d0adb
Create Date: 2026-04-17
"""
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7f1c3d2e5b8"
down_revision: Union[str, None] = "4b41e90d0adb"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    with op.batch_alter_table("wing_xsec_ted_servos") as batch_op:
        batch_op.add_column(sa.Column("component_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_ted_servo_component",
            "components",
            ["component_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("wing_xsec_ted_servos") as batch_op:
        batch_op.drop_constraint("fk_ted_servo_component", type_="foreignkey")
        batch_op.drop_column("component_id")
