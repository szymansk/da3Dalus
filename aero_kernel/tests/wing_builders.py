"""The minimal main wing every test aircraft carries (ARCHITECTURE ch. 8.11: exactly one)."""

from typing import Any


def main_wing_document(name: str = "Main") -> dict[str, Any]:
    """A two-section wing of ``surface_type`` ``main_wing`` without any device.

    Args:
        name: The wing name.

    Returns:
        The wing as a document dict, ready to be a value of ``airplane.wings``.
    """
    return {
        "name": name,
        "symmetric": True,
        "surface_type": "main_wing",
        "x_secs": [
            {"xyz_le": [0.0, y, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca2412"}
            for y in (0.0, 0.5)
        ],
    }


def airplane_document(name: str = "t") -> dict[str, Any]:
    """An airplane document with the minimal main wing and nothing else."""
    return {"name": name, "wings": {"Main": main_wing_document()}}
