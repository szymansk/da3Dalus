"""Builders for the component tests: the published reference parts and a complete document."""

import json
from pathlib import Path
from typing import Any

from aero_kernel.components import Components

POWERTRAIN = Path(__file__).parent.parent / "reference" / "powertrain" / "powertrain.json"

# Values no source publishes, for the tests that need a complete document. They are test values,
# not data of any real part (reference/powertrain/README.md).
TEST_EFFICIENCY_PCT = 80.0
TEST_MAX_POWER_W = 650.0
TEST_PACK_MASS_G = 560.0
TEST_C_RATE = 25.0
TEST_CELL_VOLTAGE_V = 3.7


def reference() -> dict[str, Any]:
    """The published powertrain data."""
    return json.loads(POWERTRAIN.read_text(encoding="utf-8"))


def components_of(
    motor_id: str,
    battery_id: str,
    propeller_id: str,
    **extra: dict[str, float],
) -> Components:
    """The component document of reference parts; ``extra`` adds fields per part (``motor=...``)."""
    data = reference()
    motor_fields = data["motors"][motor_id]["fields"] | extra.get("motor", {})
    battery_fields = data["batteries"][battery_id]["fields"] | extra.get("battery", {})
    return Components.model_validate(
        {
            "schema_version": 3,
            "motor": motor_fields,
            "battery": battery_fields,
            "propeller": data["propellers"][propeller_id]["fields"],
        }
    )


def complete_components() -> Components:
    """The T-Motor AT2814 KV900 with the Avistar pack and propeller, plus the test values nobody publishes."""
    return components_of(
        "tmotor_at2814_kv900",
        "thunder_power_prolitex_4s_6000",
        "apc_13x8e",
        motor={"efficiency_pct": TEST_EFFICIENCY_PCT, "max_power_w": TEST_MAX_POWER_W},
        battery={
            "mass_g": TEST_PACK_MASS_G,
            "c_rate": TEST_C_RATE,
            "cell_voltage_v": TEST_CELL_VOLTAGE_V,
        },
    )


PROPELLER_TABLE = Path(__file__).parent.parent / "reference" / "powertrain" / "apc_13x8e.json"


def apc_13x8e_table() -> dict[str, Any]:
    """The published APC 13x8E table (reference/powertrain/apc_13x8e.json) as a plain document."""
    return json.loads(PROPELLER_TABLE.read_text(encoding="utf-8"))["table"]


def complete_components_with_table() -> Components:
    """``complete_components`` with the APC 13x8E performance table pushed."""
    document = complete_components().model_dump()
    document["propeller"]["table"] = apc_13x8e_table()
    return Components.model_validate(document)
