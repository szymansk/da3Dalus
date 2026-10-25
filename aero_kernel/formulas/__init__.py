"""The formula implementations of the canon (ARCHITECTURE ch. 8.12).

Importing this package registers every formula into the default registry and then freezes it.
One module per canon formula, named after its slug.
"""

from aero_kernel.formulas import (
    air_density_isa,
    airplane_configuration,
    airplane_geometry,
    aspect_ratio,
    cg_for_target_margin,
    dynamic_pressure,
    horizontal_tail_arm,
    mean_geometric_chord,
    minimum_drag_speed_from_polar,
    minimum_sink_speed_from_polar,
    neutral_point,
    roll_rate,
    speed_from_stall_margin,
    stall_break,
    stall_speed,
    static_margin,
    vertical_tail_arm,
    weight_from_mass,
    wing_loading,
)
from aero_kernel.registry import DEFAULT_REGISTRY

__all__ = [
    "air_density_isa",
    "airplane_configuration",
    "airplane_geometry",
    "aspect_ratio",
    "cg_for_target_margin",
    "dynamic_pressure",
    "horizontal_tail_arm",
    "mean_geometric_chord",
    "minimum_drag_speed_from_polar",
    "minimum_sink_speed_from_polar",
    "neutral_point",
    "roll_rate",
    "speed_from_stall_margin",
    "stall_break",
    "stall_speed",
    "static_margin",
    "vertical_tail_arm",
    "weight_from_mass",
    "wing_loading",
]

DEFAULT_REGISTRY.freeze()
