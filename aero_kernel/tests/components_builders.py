"""Builders for the component tests: the published reference parts and a complete document."""

import json
from pathlib import Path
from typing import Any

from aero_kernel.components import Components

POWERTRAIN = Path(__file__).parent.parent / "reference" / "powertrain" / "powertrain.json"

# Values no source publishes, for the tests that need a complete document. They are test values,
# not data of any real part (reference/powertrain/README.md).
TEST_EFFICIENCY_PCT = 80.0
TEST_PACK_MASS_G = 560.0


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
            "schema_version": 1,
            "motor": motor_fields,
            "battery": battery_fields,
            "propeller": data["propellers"][propeller_id]["fields"],
        }
    )


def complete_components() -> Components:
    """The T-Motor AT2814 KV900 with the Avistar pack and propeller, plus the two test values."""
    return components_of(
        "tmotor_at2814_kv900",
        "thunder_power_prolitex_4s_6000",
        "apc_13x8e",
        motor={"efficiency_pct": TEST_EFFICIENCY_PCT},
        battery={"mass_g": TEST_PACK_MASS_G},
    )
