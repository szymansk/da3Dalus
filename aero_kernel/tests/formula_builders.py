"""Builders for the formula tests: ``x`` built from the model (Q11) and a stub ATM adapter."""

import math
from collections.abc import Mapping

from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Solvers, Value
from aero_kernel.errors import display_slug
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.opti import OptiAdapter

# The canon formulas that have an implementation (slugs, qualified); grows with each slice.
IMPLEMENTED = {
    "calc:weight-from-mass",
    "calc:air-density-isa",
    "calc:dynamic-pressure",
    "calc:mean-geometric-chord",
    "calc:aspect-ratio",
    "calc:wing-loading",
    "calc:airplane-geometry",
    "calc:airplane-configuration",
}


def inputs_from_model(
    model: CanonModel, formula_slug: str, by_quantity: Mapping[str, Value]
) -> dict[str, Value]:
    """Build the ``x`` of a formula from the model (Q11): the value of each bound quantity under
    the formula's parameter name.

    A renamed or added parameter changes the model's binding and so fails the test that uses it.

    Args:
        model: The canon model.
        formula_slug: Slug of the formula.
        by_quantity: Value per canon quantity slug (bare spelling).

    Returns:
        Value per parameter name of the formula's default application.

    Raises:
        AssertionError: If a bound quantity has no value or a value names no bound quantity.
    """
    formula = model.formula(formula_slug)
    assert formula is not None, formula_slug
    bound = formula.application("default").bind
    given = {display_slug(slug): value for slug, value in by_quantity.items()}
    wanted: dict[str, str] = {}
    for parameter, quantity in bound.items():
        assert isinstance(quantity, str), parameter  # these formulas bind quantities, no constants
        wanted[display_slug(quantity)] = parameter
    assert set(given) == set(wanted), (sorted(given), sorted(wanted))
    return {wanted[slug]: value for slug, value in given.items()}


class StubAtmosphere(AtmosphereAdapter):
    """An ATM adapter that answers from a table of altitude -> density, and nothing else."""

    def __init__(
        self, table: Mapping[float, float], versions: Mapping[str, str] | None = None
    ) -> None:
        """Create the stub.

        Args:
            table: Density in kg/m^3 per altitude in m; any other altitude is an error.
            versions: The tool versions the stub reports.
        """
        super().__init__(SolverRuntime())
        self.table = dict(table)
        self.versions = dict(versions or {"aerosandbox": "0.0-stub"})
        self.asked: list[float] = []

    def tool_versions(self) -> dict[str, str]:
        """Return the versions the stub was given."""
        return self.versions

    async def density(self, altitude_m: float) -> float:
        """Return the tabulated density; an altitude not in the table is a test error."""
        self.asked.append(altitude_m)
        return self.table[altitude_m]


def solvers_with(
    atmosphere: AtmosphereAdapter | None = None, opti: OptiAdapter | None = None
) -> Solvers:
    """Solvers with the given adapters; one left out is the real one on a fresh runtime."""
    return Solvers(
        atmosphere=atmosphere or AtmosphereAdapter(SolverRuntime()),
        opti=opti or OptiAdapter(SolverRuntime()),
    )


def context_with(atmosphere: AtmosphereAdapter, origin: str = "t") -> Context:
    """A formula context whose ATM adapter is the given one."""
    return Context(origin=origin, solvers=solvers_with(atmosphere=atmosphere))


def close(actual: float | None, expected: float, rel: float) -> bool:
    """Whether ``actual`` equals ``expected`` to the relative tolerance ``rel``."""
    return actual is not None and math.isclose(actual, expected, rel_tol=rel)
