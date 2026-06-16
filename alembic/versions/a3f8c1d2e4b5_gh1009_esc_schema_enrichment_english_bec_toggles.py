"""gh1009 esc schema enrichment english bec toggles

Rewrites the 'esc' component_type schema from the 10-field German-label set
to the 19-field English canonical schema with boolean BEC voltage toggles,
NiXX/Li-Ion cell range fields, and removes legacy fields (cells, bec_voltage_v,
bec_output).

Also data-migrates existing component specs:
  - bec_output free-text → bec_voltage_* boolean toggles + bec_current_a
  - bec_voltage_v scalar → matching bec_voltage_* boolean toggle
  - cells → dropped (no replacement)

Downgrade restores the pre-gh1009 10-field schema_def only; spec data
migration is intentionally one-way (component specs are not restored).

Revision ID: a3f8c1d2e4b5
Revises: ee9fd32e8e90
Create Date: 2026-06-16
"""

from __future__ import annotations

import json
import logging
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "a3f8c1d2e4b5"
down_revision: Union[str, None] = "e2a35c6eac69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ──────────────────────────────────────────────────────────────────────────────
# BEC voltage helpers
# ──────────────────────────────────────────────────────────────────────────────

_BEC_VOLTAGE_MAP: dict[float, str] = {
    5.0: "bec_voltage_5v",
    5.5: "bec_voltage_5_5v",
    6.0: "bec_voltage_6v",
    6.5: "bec_voltage_6_5v",
    7.4: "bec_voltage_7_4v",
    8.4: "bec_voltage_8_4v",
    9.0: "bec_voltage_9v",
    12.0: "bec_voltage_12v",
}

_STD_VOLTAGES: list[float] = sorted(_BEC_VOLTAGE_MAP.keys())

_TOLERANCE = 0.1  # ±0.1 V snap tolerance


def _snap_voltage(v: float) -> str | None:
    """Snap v to the nearest standard BEC voltage (±0.1 V); return field name or None."""
    for std in _STD_VOLTAGES:
        if abs(v - std) <= _TOLERANCE:
            return _BEC_VOLTAGE_MAP[std]
    return None


def _parse_bec_output(raw: str | None) -> dict[str, bool | float]:
    """Parse free-text bec_output string → dict of bec_voltage_* + bec_current_a.

    Returns an empty dict if raw is None or unparseable.
    Defensive: logs a warning for unrecognised strings but never raises.
    """
    if not raw:
        return {}

    result: dict[str, bool | float] = {}

    # Extract all voltage tokens: e.g. "5V", "5.0V", "5.5V"
    voltage_matches = re.findall(r"(\d+\.?\d*)\s*[Vv]", raw)
    for vstr in voltage_matches:
        try:
            v = float(vstr)
        except ValueError:
            continue
        field = _snap_voltage(v)
        if field is not None:
            result[field] = True
        else:
            logger.warning(
                "gh-1009 migration: bec_output voltage %s V does not snap to any "
                "standard value (±0.1 V). Skipping. Raw string: %r",
                vstr,
                raw,
            )

    # Extract current token: e.g. "4A", "8A"
    current_match = re.search(r"(\d+)\s*[Aa]", raw)
    if current_match:
        result["bec_current_a"] = float(current_match.group(1))

    if not result:
        logger.warning(
            "gh-1009 migration: could not parse any voltage or current from "
            "bec_output=%r. Leaving entry unchanged.",
            raw,
        )

    return result


def _migrate_esc_specs(specs: dict) -> dict:
    """Transform a single ESC component's specs dict.

    Applies in-order:
    1. Parse bec_output (free string) → bec_voltage_* + bec_current_a.
    2. Parse bec_voltage_v (scalar) → matching bec_voltage_* toggle.
    3. Drop cells, bec_output, bec_voltage_v.

    Returns a new dict; the input is not mutated.
    """
    result = dict(specs)

    # 1. Parse bec_output
    bec_output = result.pop("bec_output", None)
    parsed = _parse_bec_output(bec_output)
    result.update(parsed)

    # 2. Parse bec_voltage_v scalar
    bec_v = result.pop("bec_voltage_v", None)
    if bec_v is not None:
        try:
            field = _snap_voltage(float(bec_v))
            if field is not None:
                result[field] = True
            else:
                logger.warning(
                    "gh-1009 migration: bec_voltage_v=%s does not snap to a standard "
                    "voltage (±0.1 V). Dropping.",
                    bec_v,
                )
        except (TypeError, ValueError):
            logger.warning(
                "gh-1009 migration: bec_voltage_v=%r is not numeric. Dropping.",
                bec_v,
            )

    # 3. Drop legacy cells key
    result.pop("cells", None)

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Canonical 19-field schema (upgrade target)
# ──────────────────────────────────────────────────────────────────────────────

_NEW_ESC_SCHEMA: list[dict] = [
    {"name": "continuous_current_a", "label": "Continuous Current", "type": "number", "unit": "A"},
    {
        "name": "max_current_a",
        "label": "Burst Current",
        "type": "number",
        "unit": "A",
        "required": True,
    },
    {"name": "cells_lipo_min", "label": "LiPo Cells Min", "type": "number", "unit": "S"},
    {"name": "cells_lipo_max", "label": "LiPo Cells Max", "type": "number", "unit": "S"},
    {"name": "cells_nixx_min", "label": "NiXX Cells Min", "type": "number", "unit": "cells"},
    {"name": "cells_nixx_max", "label": "NiXX Cells Max", "type": "number", "unit": "cells"},
    {"name": "cells_liion_min", "label": "Li-Ion/LiHV Cells Min", "type": "number", "unit": "S"},
    {"name": "cells_liion_max", "label": "Li-Ion/LiHV Cells Max", "type": "number", "unit": "S"},
    {"name": "bec_voltage_5v", "label": "BEC 5.0 V", "type": "boolean"},
    {"name": "bec_voltage_5_5v", "label": "BEC 5.5 V", "type": "boolean"},
    {"name": "bec_voltage_6v", "label": "BEC 6.0 V", "type": "boolean"},
    {"name": "bec_voltage_6_5v", "label": "BEC 6.5 V", "type": "boolean"},
    {"name": "bec_voltage_7_4v", "label": "BEC 7.4 V", "type": "boolean"},
    {"name": "bec_voltage_8_4v", "label": "BEC 8.4 V", "type": "boolean"},
    {"name": "bec_voltage_9v", "label": "BEC 9.0 V", "type": "boolean"},
    {"name": "bec_voltage_12v", "label": "BEC 12.0 V", "type": "boolean"},
    {"name": "bec_current_a", "label": "BEC Current", "type": "number", "unit": "A"},
    {
        "name": "protocol",
        "label": "Protocol",
        "type": "enum",
        "options": ["pwm", "oneshot", "dshot150", "dshot300", "dshot600"],
    },
    {"name": "art_no", "label": "Article No.", "type": "string"},
]

# ──────────────────────────────────────────────────────────────────────────────
# Pre-gh1009 10-field schema (downgrade target — the exact state left by
# 1f320603c2cf after its upgrade() ran)
# ──────────────────────────────────────────────────────────────────────────────

_OLD_ESC_SCHEMA: list[dict] = [
    {
        "name": "max_current_a",
        "label": "Max Strom (kurz)",
        "type": "number",
        "unit": "A",
        "required": True,
    },
    {"name": "cells", "label": "Zellen (S)", "type": "number"},
    {"name": "bec_voltage_v", "label": "BEC Spannung", "type": "number", "unit": "V"},
    {"name": "bec_current_a", "label": "BEC Strom", "type": "number", "unit": "A"},
    {
        "name": "protocol",
        "label": "Protokoll",
        "type": "enum",
        "options": ["pwm", "oneshot", "dshot150", "dshot300", "dshot600"],
    },
    {"name": "continuous_current_a", "label": "Dauerstrom", "type": "number", "unit": "A"},
    {"name": "cells_lipo_min", "label": "LiPo Zellen min", "type": "number"},
    {"name": "cells_lipo_max", "label": "LiPo Zellen max", "type": "number"},
    {"name": "bec_output", "label": "BEC Ausgang", "type": "string"},
    {"name": "art_no", "label": "Art.-Nr.", "type": "string"},
]


# ──────────────────────────────────────────────────────────────────────────────
# Upgrade / downgrade
# ──────────────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    """Rewrite the esc schema_def to the canonical 19-field set and migrate specs."""
    conn = op.get_bind()

    # 1. Update component_types schema row
    row = conn.execute(
        sa.text("SELECT id FROM component_types WHERE name = :n"),
        {"n": "esc"},
    ).fetchone()

    if row is None:
        # No esc row in this DB (e.g. blank test DB seeded after migration runs).
        return

    conn.execute(
        sa.text('UPDATE component_types SET "schema" = :s WHERE name = :n'),
        {"s": json.dumps(_NEW_ESC_SCHEMA), "n": "esc"},
    )

    # 2. Migrate existing component specs
    components = conn.execute(
        sa.text("SELECT id, specs FROM components WHERE component_type = :ct"),
        {"ct": "esc"},
    ).fetchall()

    for comp_id, specs_raw in components:
        if not specs_raw:
            continue
        try:
            specs = json.loads(specs_raw) if isinstance(specs_raw, str) else specs_raw
        except (json.JSONDecodeError, TypeError):
            logger.warning("gh-1009 migration: could not parse specs for component id=%s", comp_id)
            continue

        migrated = _migrate_esc_specs(specs)

        conn.execute(
            sa.text("UPDATE components SET specs = :s WHERE id = :id"),
            {"s": json.dumps(migrated), "id": comp_id},
        )


def downgrade() -> None:
    """Restore the pre-gh1009 10-field ESC schema_def.

    Note: component spec data migration is intentionally one-way — existing
    specs already migrated (bec_output → bec_voltage_* toggles) are NOT
    reversed. Only the schema_def row is restored.
    """
    conn = op.get_bind()

    row = conn.execute(
        sa.text("SELECT id FROM component_types WHERE name = :n"),
        {"n": "esc"},
    ).fetchone()

    if row is None:
        return

    conn.execute(
        sa.text('UPDATE component_types SET "schema" = :s WHERE name = :n'),
        {"s": json.dumps(_OLD_ESC_SCHEMA), "n": "esc"},
    )
