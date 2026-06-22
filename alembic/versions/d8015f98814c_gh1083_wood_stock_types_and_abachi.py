"""gh-1083: seed Höllein wood construction-stock component types + Abachi material

Adds four seeded, non-deletable component types for raw building stock:
  - veneer
  - strip
  - triangular_strip
  - grooved_strip

Each carries a required ``material`` enum that references a material component
(``Pine (structural)`` or ``Abachi``) holding the density. Mass is not baked
into the stock item — it derives downstream from the bbox dimensions × the
referenced material's density.

Also seeds the ``Abachi`` material component (density ≈ 390 kg/m³), referenced
by the Abachi veneer/grooved stock. (``Pine (structural)`` already exists from
gh-1008.)

The type/material definitions are intentionally duplicated here (rather than
imported from app code) so replaying this migration is not tied to the current
application code — matching the convention of 28a13fbeac90 and e2a35c6eac69.

Revision ID: d8015f98814c
Revises: b7d4e2a91c33
Create Date: 2026-06-22 20:45:00.000000
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8015f98814c"
down_revision: Union[str, None] = "b7d4e2a91c33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = datetime.now(timezone.utc).isoformat()

_MATERIAL_OPTIONS = ["Pine (structural)", "Abachi"]

_MATERIAL_PROP = {
    "name": "material",
    "label": "Material",
    "type": "enum",
    "options": _MATERIAL_OPTIONS,
    "required": True,
    "description": "Referenced material component carrying the density for mass estimation.",
}
_PRICE_PROP = {"name": "price_eur", "label": "Price", "type": "number", "unit": "EUR", "min": 0.0}
_SKU_PROP = {"name": "sku", "label": "SKU / Art.-No.", "type": "string"}
_SOURCE_PROP = {"name": "source_url", "label": "Source URL", "type": "string"}
_PACK_PROP = {
    "name": "pack_qty",
    "label": "Pack quantity",
    "type": "number",
    "min": 1,
    "description": "Units per pack (VE).",
}
_GROOVE_PROP = {
    "name": "groove_mm",
    "label": "Groove size",
    "type": "number",
    "unit": "mm",
    "min": 0.0,
}

_BASE = [_MATERIAL_PROP, _PRICE_PROP, _SKU_PROP, _SOURCE_PROP]

_WOOD_TYPES = [
    {
        "name": "veneer",
        "label": "Veneer",
        "description": "Sheet veneer stock (e.g. Abachi facing). bbox: height × width × length (mm).",
        "schema": list(_BASE),
    },
    {
        "name": "strip",
        "label": "Strip",
        "description": "Rectangular wood strip / Leiste. bbox: height × width × length (mm).",
        "schema": [*_BASE, _PACK_PROP],
    },
    {
        "name": "triangular_strip",
        "label": "Triangular Strip",
        "description": "Triangular wood strip / Dreikantleiste. bbox: leg × leg × length (mm).",
        "schema": [*_BASE, _PACK_PROP],
    },
    {
        "name": "grooved_strip",
        "label": "Grooved Strip",
        "description": "Grooved wood strip / Nutleiste. bbox: height × width × length (mm).",
        "schema": [*_BASE, _PACK_PROP, _GROOVE_PROP],
    },
]

_ABACHI = {
    "name": "Abachi",
    "component_type": "material",
    "manufacturer": None,
    "description": "Abachi (Obeche) — light construction veneer/strip wood. Density ≈ 390 kg/m³.",
    "mass_g": None,
    "bbox_x_mm": None,
    "bbox_y_mm": None,
    "bbox_z_mm": None,
    "model_ref": None,
    "specs": {"density_kg_m3": 390.0},
    "created_at": _NOW,
    "updated_at": _NOW,
}

_component_types = sa.table(
    "component_types",
    sa.column("name", sa.String),
    sa.column("label", sa.String),
    sa.column("description", sa.String),
    sa.column("schema", sa.JSON),
    sa.column("deletable", sa.Boolean),
    sa.column("created_at", sa.String),
    sa.column("updated_at", sa.String),
)

_components = sa.table(
    "components",
    sa.column("name", sa.String),
    sa.column("component_type", sa.String),
    sa.column("manufacturer", sa.String),
    sa.column("description", sa.String),
    sa.column("mass_g", sa.Float),
    sa.column("bbox_x_mm", sa.Float),
    sa.column("bbox_y_mm", sa.Float),
    sa.column("bbox_z_mm", sa.Float),
    sa.column("model_ref", sa.String),
    sa.column("specs", sa.JSON),
    sa.column("created_at", sa.String),
    sa.column("updated_at", sa.String),
)


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Seed wood component types (idempotent by name).
    for t in _WOOD_TYPES:
        existing = conn.execute(
            sa.text("SELECT id FROM component_types WHERE name = :n"), {"n": t["name"]}
        ).fetchone()
        if existing is None:
            conn.execute(
                _component_types.insert().values(
                    name=t["name"],
                    label=t["label"],
                    description=t["description"],
                    schema=t["schema"],
                    deletable=False,
                    created_at=_NOW,
                    updated_at=_NOW,
                )
            )

    # 2. Seed the Abachi material component (idempotent by name + type).
    existing = conn.execute(
        sa.text("SELECT id FROM components WHERE name = 'Abachi' AND component_type = 'material'")
    ).fetchone()
    if existing is None:
        conn.execute(_components.insert().values(**_ABACHI))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM components WHERE name = 'Abachi' AND component_type = 'material'")
    )
    for t in _WOOD_TYPES:
        conn.execute(sa.text("DELETE FROM component_types WHERE name = :n"), {"n": t["name"]})
