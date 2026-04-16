"""repair_double_encoded_component_types_schemas

Revision ID: 4b41e90d0adb
Revises: 28a13fbeac90
Create Date: 2026-04-16 22:49:58

One-shot fix for dev databases that applied 28a13fbeac90 before it was
corrected. The original seed called ``json.dumps(list)`` which SQLAlchemy's
JSON type then re-serialised, producing a double-encoded scalar in the
``schema`` column. This migration walks every row and, when the stored
value is a string, parses it back to a proper JSON list.

Idempotent: rows that already hold a list are left alone.
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b41e90d0adb"
down_revision: Union[str, None] = "28a13fbeac90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Normalise `component_types.schema` values from string → list."""
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, schema FROM component_types")
    ).fetchall()
    for row in rows:
        raw = row.schema
        if raw is None:
            continue
        # If the stored value is still a string, unwrap it (handles both
        # single- and double-encoded cases).
        if isinstance(raw, str):
            parsed = raw
            # Unwrap up to two layers of JSON encoding.
            for _ in range(2):
                try:
                    parsed = json.loads(parsed)
                except (TypeError, json.JSONDecodeError):
                    break
                if not isinstance(parsed, str):
                    break
            if isinstance(parsed, list):
                conn.execute(
                    sa.text(
                        "UPDATE component_types SET schema = :s WHERE id = :i"
                    ),
                    {"s": json.dumps(parsed), "i": row.id},
                )
            # else: leave the row alone — the service layer's
            # _normalize_schema() will still handle it gracefully.


def downgrade() -> None:
    """No-op: data repair is not reversible (and wouldn't be useful to reverse)."""
    pass
