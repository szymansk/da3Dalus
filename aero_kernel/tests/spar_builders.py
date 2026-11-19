"""Builders for the spar capacity tests: small wings with spars, and test materials.

The material numbers are TEST VALUES, chosen so that hand calculation is easy. They are not
data of any real material.
"""

from typing import Any

from aero_kernel.components import Material
from aero_kernel.geometry import Wing

TEST_STRENGTH_PA = 100.0e6  # test value, not a real material

RECTANGULAR: dict[str, Any] = {"shape": "rectangular", "width": 0.02, "height": 0.003}
CAPPED: dict[str, Any] = {
    "shape": "capped",
    "width": 0.004,
    "height": 0.0147,
    "flange_thickness": 0.001,
}
TUBE: dict[str, Any] = {"shape": "tube", "outer_diameter": 0.016, "wall_thickness": 0.001}
ROD: dict[str, Any] = {"shape": "rod", "diameter": 0.01}


def material_with(strength: float | None = TEST_STRENGTH_PA) -> Material:
    """A material with the test strength, or without any strength."""
    return Material(name="Test material", bending_strength_pa=strength, source=None)


def spar(**fields: Any) -> dict[str, Any]:
    """One spar entry: a 3 mm x 20 mm pocket at 25 % chord, plus the given fields."""
    return {
        "spare_support_dimension_width": 0.003,
        "spare_support_dimension_height": 0.02,
        "spare_position_factor": 0.25,
    } | fields


def wing(*spar_lists: list[dict[str, Any]] | None, step: float = 0.5) -> Wing:
    """A straight wing, one segment per spar list, ribs ``step`` metres apart in y (chord 0.2 m)."""
    x_secs: list[dict[str, Any]] = []
    for index in range(len(spar_lists) + 1):
        x_sec: dict[str, Any] = {
            "xyz_le": [0.0, step * index, 0.0],
            "chord": 0.2,
            "twist": 0.0,
            "airfoil": "NACA 2412",
        }
        if index < len(spar_lists) and spar_lists[index] is not None:
            x_sec["spare_list"] = spar_lists[index]
        x_secs.append(x_sec)
    return Wing.model_validate({"name": "Main", "surface_type": "main_wing", "x_secs": x_secs})
