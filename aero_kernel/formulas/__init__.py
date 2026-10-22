"""The formula implementations of the canon (ARCHITECTURE ch. 8.12).

Importing this package registers every formula into the default registry and then freezes it.
One module per canon formula, named after its slug.
"""

from aero_kernel.formulas import air_density_isa, dynamic_pressure, weight_from_mass
from aero_kernel.registry import DEFAULT_REGISTRY

__all__ = ["air_density_isa", "dynamic_pressure", "weight_from_mass"]

DEFAULT_REGISTRY.freeze()
