"""extend brushless_motor and esc component_type schemas for D-Power fields (gh-986)

Adds new optional spec fields to the brushless_motor and esc component types:
  - brushless_motor: continuous_current_a, io_no_load_a, cells_lipo_min,
    cells_lipo_max, static_thrust_g, art_no, max_power_w, max_continuous_power_w
  - esc: continuous_current_a, cells_lipo_min, cells_lipo_max, bec_output, art_no

Additive only — existing component specs (a JSON column) remain valid because
unrecognised keys are preserved. The component_types.schema_def JSON column is
updated in-place via SQL UPDATE.

Revision ID: 1f320603c2cf
Revises: a1c9f3e7b210
Create Date: 2026-06-15
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1f320603c2cf"
down_revision: Union[str, None] = "a1c9f3e7b210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# New fields to add to brushless_motor schema_def
_BRUSHLESS_MOTOR_NEW_FIELDS = [
    {"name": "continuous_current_a", "label": "Dauerstrom", "type": "number", "unit": "A"},
    {"name": "io_no_load_a", "label": "Leerlaufstrom Io", "type": "number", "unit": "A"},
    {"name": "cells_lipo_min", "label": "LiPo Zellen min", "type": "number"},
    {"name": "cells_lipo_max", "label": "LiPo Zellen max", "type": "number"},
    {"name": "static_thrust_g", "label": "Statischer Schub", "type": "number", "unit": "g"},
    {"name": "art_no", "label": "Art.-Nr.", "type": "string"},
    {"name": "max_power_w", "label": "Max. Leistung", "type": "number", "unit": "W"},
    {"name": "max_continuous_power_w", "label": "Dauerleistung", "type": "number", "unit": "W"},
]

# New fields to add to esc schema_def
_ESC_NEW_FIELDS = [
    {"name": "continuous_current_a", "label": "Dauerstrom", "type": "number", "unit": "A"},
    {"name": "cells_lipo_min", "label": "LiPo Zellen min", "type": "number"},
    {"name": "cells_lipo_max", "label": "LiPo Zellen max", "type": "number"},
    {"name": "bec_output", "label": "BEC Ausgang", "type": "string"},
    {"name": "art_no", "label": "Art.-Nr.", "type": "string"},
]


def _extend_schema(existing_json: str | None, new_fields: list[dict]) -> str:
    """Append new_fields to existing schema_def JSON, skipping already-present names."""
    existing: list[dict] = json.loads(existing_json) if existing_json else []
    existing_names = {f["name"] for f in existing}
    for field in new_fields:
        if field["name"] not in existing_names:
            existing.append(field)
    return json.dumps(existing)


def upgrade() -> None:
    """Extend brushless_motor and esc schema_defs with D-Power fields."""
    conn = op.get_bind()

    for type_name, new_fields in [
        ("brushless_motor", _BRUSHLESS_MOTOR_NEW_FIELDS),
        ("esc", _ESC_NEW_FIELDS),
    ]:
        row = conn.execute(
            sa.text('SELECT "schema" FROM component_types WHERE name = :n'),
            {"n": type_name},
        ).fetchone()

        if row is None:
            # Type doesn't exist yet (e.g. blank test DB); will be seeded later.
            continue

        new_schema = _extend_schema(row[0], new_fields)
        conn.execute(
            sa.text('UPDATE component_types SET "schema" = :s WHERE name = :n'),
            {"s": new_schema, "n": type_name},
        )


def downgrade() -> None:
    """Remove the gh-986 fields from brushless_motor and esc schema_defs."""
    conn = op.get_bind()

    motor_remove = {f["name"] for f in _BRUSHLESS_MOTOR_NEW_FIELDS}
    esc_remove = {f["name"] for f in _ESC_NEW_FIELDS}

    for type_name, remove_names in [
        ("brushless_motor", motor_remove),
        ("esc", esc_remove),
    ]:
        row = conn.execute(
            sa.text('SELECT "schema" FROM component_types WHERE name = :n'),
            {"n": type_name},
        ).fetchone()

        if row is None:
            continue

        existing: list[dict] = json.loads(row[0]) if row[0] else []
        pruned = [f for f in existing if f["name"] not in remove_names]
        conn.execute(
            sa.text('UPDATE component_types SET "schema" = :s WHERE name = :n'),
            {"s": json.dumps(pruned), "n": type_name},
        )
