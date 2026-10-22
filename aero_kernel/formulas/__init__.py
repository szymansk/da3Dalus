"""The formula implementations of the canon (ARCHITECTURE ch. 8.12).

Importing this package registers every formula into the default registry and then freezes it.
One module per canon formula, named after its slug.
"""

from aero_kernel.formulas import (
    air_density_isa,
    airplane_geometry,
    aspect_ratio,
    dynamic_pressure,
    mean_geometric_chord,
    weight_from_mass,
    wing_loading,
)
from aero_kernel.registry import DEFAULT_REGISTRY

__all__ = [
    "air_density_isa",
    "airplane_geometry",
    "aspect_ratio",
    "dynamic_pressure",
    "mean_geometric_chord",
    "weight_from_mass",
    "wing_loading",
]

DEFAULT_REGISTRY.freeze()
