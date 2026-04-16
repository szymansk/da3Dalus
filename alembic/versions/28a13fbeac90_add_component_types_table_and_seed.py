"""add_component_types_table_and_seed

Revision ID: 28a13fbeac90
Revises: 1bc333d5b078
Create Date: 2026-04-16 21:56:35

Creates the component_types registry (gh#83) and seeds the nine previously
hardcoded types with reasonable property schemas so the existing 9-type
workflow keeps working.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "28a13fbeac90"
down_revision: Union[str, None] = "1bc333d5b078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# --------------------------------------------------------------------------- #
# Seed data — property schemas for the 9 original types
# --------------------------------------------------------------------------- #

SEED_TYPES = [
    {
        "name": "material",
        "label": "Material (3D-Druck)",
        "description": "3D-print material with density and print type",
        "schema": [
            {"name": "density_kg_m3", "label": "Dichte", "type": "number",
             "unit": "kg/m³", "required": True, "min": 100, "max": 20000},
            {"name": "print_resolution_mm", "label": "Druckauflösung", "type": "number",
             "unit": "mm", "min": 0.05, "max": 2.0, "default": 0.4},
            {"name": "print_type", "label": "Drucktyp", "type": "enum",
             "options": ["volume", "surface"], "default": "volume"},
        ],
    },
    {
        "name": "servo",
        "label": "Servo",
        "description": None,
        "schema": [
            {"name": "torque_kg_cm", "label": "Drehmoment", "type": "number", "unit": "kg·cm"},
            {"name": "speed_s_per_60deg", "label": "Geschwindigkeit", "type": "number", "unit": "s/60°"},
            {"name": "voltage_v", "label": "Spannung", "type": "number", "unit": "V"},
            {"name": "connector", "label": "Anschluss", "type": "enum",
             "options": ["jr", "futaba", "universal"]},
        ],
    },
    {
        "name": "brushless_motor",
        "label": "Brushless Motor",
        "description": None,
        "schema": [
            {"name": "kv_rpm_per_volt", "label": "KV", "type": "number", "unit": "RPM/V",
             "required": True},
            {"name": "max_current_a", "label": "Max Strom", "type": "number", "unit": "A"},
            {"name": "shaft_diameter_mm", "label": "Wellen-Ø", "type": "number", "unit": "mm"},
        ],
    },
    {
        "name": "battery",
        "label": "Battery",
        "description": None,
        "schema": [
            {"name": "capacity_mah", "label": "Kapazität", "type": "number", "unit": "mAh",
             "required": True, "min": 0},
            {"name": "cells", "label": "Zellen (S)", "type": "number", "required": True, "min": 1},
            {"name": "c_rate", "label": "C-Rate", "type": "number"},
            {"name": "voltage_v", "label": "Spannung", "type": "number", "unit": "V"},
        ],
    },
    {
        "name": "esc",
        "label": "ESC",
        "description": None,
        "schema": [
            {"name": "max_current_a", "label": "Max Strom", "type": "number", "unit": "A",
             "required": True},
            {"name": "cells", "label": "Zellen (S)", "type": "number"},
            {"name": "bec_voltage_v", "label": "BEC Spannung", "type": "number", "unit": "V"},
            {"name": "bec_current_a", "label": "BEC Strom", "type": "number", "unit": "A"},
            {"name": "protocol", "label": "Protokoll", "type": "enum",
             "options": ["pwm", "oneshot", "dshot150", "dshot300", "dshot600"]},
        ],
    },
    {
        "name": "propeller",
        "label": "Propeller",
        "description": None,
        "schema": [
            {"name": "diameter_in", "label": "Durchmesser", "type": "number", "unit": "inch",
             "required": True},
            {"name": "pitch_in", "label": "Steigung", "type": "number", "unit": "inch",
             "required": True},
            {"name": "blades", "label": "Blätter", "type": "number", "required": True, "min": 2},
            {"name": "material", "label": "Material", "type": "string"},
        ],
    },
    {
        "name": "receiver",
        "label": "Receiver",
        "description": None,
        "schema": [
            {"name": "channels", "label": "Kanäle", "type": "number"},
            {"name": "protocol", "label": "Protokoll", "type": "string"},
        ],
    },
    {
        "name": "flight_controller",
        "label": "Flight Controller",
        "description": None,
        "schema": [
            {"name": "firmware", "label": "Firmware", "type": "string"},
            {"name": "mcu", "label": "MCU", "type": "string"},
        ],
    },
    {
        "name": "generic",
        "label": "Generic",
        "description": "Free-form type with no structured schema",
        "schema": [],
    },
]


def upgrade() -> None:
    """Create component_types table + seed the 9 default types."""
    op.create_table(
        "component_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("schema", sa.JSON(), nullable=False),
        sa.Column("deletable", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    import json
    component_types = sa.table(
        "component_types",
        sa.column("name", sa.String),
        sa.column("label", sa.String),
        sa.column("description", sa.String),
        sa.column("schema", sa.JSON),
        sa.column("deletable", sa.Boolean),
    )
    op.bulk_insert(
        component_types,
        [
            {
                "name": t["name"],
                "label": t["label"],
                "description": t["description"],
                # Some DB dialects persist JSON as string — dump explicitly for safety.
                "schema": json.dumps(t["schema"]),
                "deletable": False,
            }
            for t in SEED_TYPES
        ],
    )


def downgrade() -> None:
    op.drop_table("component_types")
