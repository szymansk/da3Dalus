"""gh-1008: add structural fields to material type + seed Pine + Carbon Fiber

Extends the 'material' ComponentType schema additively with:
  - allowable_bending_stress_mpa (number, MPa) — for spar sizing
  - youngs_modulus_gpa (number, GPa, optional) — for future deflection

Both fields are optional so existing 3D-print material rows stay valid.

Seeds two structural materials as Component rows:
  - Pine (Kiefer, Güte A): density=500, σ_allow=39 MPa, E=11 GPa
  - Carbon Fiber: density=1600, σ_allow=500 MPa, E=120 GPa

Revision ID: a1b2c3d4e5f6
Revises: ee9fd32e8e90
Create Date: 2026-06-16 08:00:00.000000
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2a35c6eac69"
down_revision: Union[str, None] = "ee9fd32e8e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# New property definitions added to the 'material' schema
_NEW_PROPS = [
    {
        "name": "allowable_bending_stress_mpa",
        "label": "Allowable Bending Stress",
        "type": "number",
        "unit": "MPa",
        "required": False,
        "min": 0.0,
        "description": "σ_allow for spar sizing (MPa). Compression governs for wood.",
    },
    {
        "name": "youngs_modulus_gpa",
        "label": "Young's Modulus",
        "type": "number",
        "unit": "GPa",
        "required": False,
        "min": 0.0,
        "description": "E for future deflection checks (GPa).",
    },
]

_NEW_PROP_NAMES = {p["name"] for p in _NEW_PROPS}

# Structural material seeds
_NOW = datetime.now(timezone.utc).isoformat()

_STRUCTURAL_MATERIALS = [
    {
        "name": "Pine (structural)",
        "component_type": "material",
        "manufacturer": None,
        "description": "Kiefer Güte A — structural spar material. σ_allow = 39 MPa (compression).",
        "mass_g": None,
        "bbox_x_mm": None,
        "bbox_y_mm": None,
        "bbox_z_mm": None,
        "model_ref": None,
        "specs": json.dumps(
            {
                "density_kg_m3": 500.0,
                "allowable_bending_stress_mpa": 39.0,
                "youngs_modulus_gpa": 11.0,
            }
        ),
        "created_at": _NOW,
        "updated_at": _NOW,
    },
    {
        "name": "Carbon Fiber (structural)",
        "component_type": "material",
        "manufacturer": None,
        "description": "Carbon fiber tube/spar — conservative σ_allow=500 MPa (buckling-aware).",
        "mass_g": None,
        "bbox_x_mm": None,
        "bbox_y_mm": None,
        "bbox_z_mm": None,
        "model_ref": None,
        "specs": json.dumps(
            {
                "density_kg_m3": 1600.0,
                "allowable_bending_stress_mpa": 500.0,
                "youngs_modulus_gpa": 120.0,
            }
        ),
        "created_at": _NOW,
        "updated_at": _NOW,
    },
]


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Extend the 'material' ComponentType schema additively
    row = conn.execute(
        sa.text("SELECT id, \"schema\" FROM component_types WHERE name = 'material'")
    ).fetchone()

    if row is not None:
        type_id, raw_schema = row[0], row[1]
        # schema_def may be stored as JSON string or already parsed list
        if isinstance(raw_schema, str):
            try:
                current_schema = json.loads(raw_schema)
            except json.JSONDecodeError:
                current_schema = []
        elif isinstance(raw_schema, list):
            current_schema = raw_schema
        else:
            current_schema = []

        existing_names = {p.get("name") for p in current_schema if isinstance(p, dict)}
        for prop in _NEW_PROPS:
            if prop["name"] not in existing_names:
                current_schema.append(prop)

        conn.execute(
            sa.text("UPDATE component_types SET \"schema\" = :schema WHERE id = :id"),
            {"schema": json.dumps(current_schema), "id": type_id},
        )

    # 2. Seed structural material components (idempotent by name)
    components_table = sa.table(
        "components",
        sa.column("name"),
        sa.column("component_type"),
        sa.column("manufacturer"),
        sa.column("description"),
        sa.column("mass_g"),
        sa.column("bbox_x_mm"),
        sa.column("bbox_y_mm"),
        sa.column("bbox_z_mm"),
        sa.column("model_ref"),
        sa.column("specs"),
        sa.column("created_at"),
        sa.column("updated_at"),
    )
    for mat in _STRUCTURAL_MATERIALS:
        existing = conn.execute(
            sa.text("SELECT id FROM components WHERE name = :name AND component_type = 'material'"),
            {"name": mat["name"]},
        ).fetchone()
        if existing is None:
            conn.execute(components_table.insert(), mat)


def downgrade() -> None:
    conn = op.get_bind()

    # Remove seeded components
    for mat in _STRUCTURAL_MATERIALS:
        conn.execute(
            sa.text("DELETE FROM components WHERE name = :name AND component_type = 'material'"),
            {"name": mat["name"]},
        )

    # Remove added props from material schema
    row = conn.execute(
        sa.text("SELECT id, \"schema\" FROM component_types WHERE name = 'material'")
    ).fetchone()
    if row is not None:
        type_id, raw_schema = row[0], row[1]
        if isinstance(raw_schema, str):
            try:
                current_schema = json.loads(raw_schema)
            except json.JSONDecodeError:
                current_schema = []
        else:
            current_schema = raw_schema or []

        pruned = [p for p in current_schema if p.get("name") not in _NEW_PROP_NAMES]
        conn.execute(
            sa.text("UPDATE component_types SET \"schema\" = :schema WHERE id = :id"),
            {"schema": json.dumps(pruned), "id": type_id},
        )
