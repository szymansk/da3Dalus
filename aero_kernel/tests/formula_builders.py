"""Builders for the formula tests: ``x`` built from the model (Q11) and a stub ATM adapter."""

import math
from collections.abc import Mapping, Sequence

from aero_kernel.build import shipped_build
from aero_kernel.canon.model import CanonModel
from aero_kernel.context import Context, Solvers, Value
from aero_kernel.errors import display_slug
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.geometry_properties import MainWingProperties, SurfaceProperties
from aero_kernel.rules import Rules
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.solvers.avl import AvlAdapter
from aero_kernel.solvers.geometry import GeometryAdapter
from aero_kernel.solvers.opti import OptiAdapter
from aero_kernel.tests.asb_fakes import (
    stand_in_fin_area,
    stand_in_main_wing_properties,
    stand_in_quarter_chord_x,
    stand_in_surface_of,
)
from pydantic import JsonValue

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
    "calc:stall-speed",
    "calc:stall-break",
    "calc:minimum-drag-speed-from-polar",
    "calc:minimum-sink-speed-from-polar",
    "calc:neutral-point",
    "calc:static-margin",
    "calc:speed-from-stall-margin",
    "calc:roll-rate",
    "calc:cg-for-target-margin",
    "calc:horizontal-tail-arm",
    "calc:vertical-tail-arm",
    "calc:vertical-tail-volume",
    "calc:spiral-parameter",
    "calc:static-margin-probe",
    "calc:lateral-static-stability-md",
    "calc:lateral-static-stability-app",
    "calc:lateral-static-stability-mp",
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


# Sea-level ISA viscosity and speed of sound, the stub's constants next to its table of densities.
STUB_VISCOSITY = 1.7894e-5
STUB_SPEED_OF_SOUND = 340.294


# What the OPT adapter reports as its settings (provenance, cache key).
OPT_SETTINGS: dict[str, JsonValue] = {
    "neuralfoil_model_size": "xlarge",
    "opt_alpha_min_deg": -15.0,
    "opt_alpha_max_deg": 25.0,
    "opt_alpha_step_deg": 0.25,
    "opt_bracket_cl": 1.0,
    "opt_v_min_ms": 1.0,
    "opt_v_max_mach": 0.6,
    "opt_max_iterations": 300,
    "opt_active_bound_fraction": 1e-6,
    "opt_effectiveness_exponent": 2.751428551177291,
    "opt_probe_tolerance": 1e-6,
    "opt_peak_tolerance": 1e-6,
    "opt_zero_span": 1e-15,
    "opt_alpha_margin_deg": 1e-9,
    "opt_hinge_floor": 1e-16,
    "opt_flap_rib_gap_m": 1e-6,
}


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

    async def state(self, altitude_m: float) -> AirState:
        """Return the tabulated density with fixed viscosity and speed of sound (sea-level ISA)."""
        self.asked.append(altitude_m)
        return AirState(
            density=self.table[altitude_m],
            dynamic_viscosity=STUB_VISCOSITY,
            speed_of_sound=STUB_SPEED_OF_SOUND,
        )


class StubGeometry(GeometryAdapter):
    """A GEO adapter that answers with fixed reference values, and records the airplane it was asked about."""

    def __init__(
        self,
        reference: MainWingProperties | None = None,
        versions: Mapping[str, str] | None = None,
        surfaces: Mapping[str, SurfaceProperties] | None = None,
    ) -> None:
        """Create the stub.

        Args:
            surfaces: Fixed planform values per wing key; any other wing gets the stand-in.
            reference: What every call returns; by default the stand-in values of the airplane asked about.
            versions: The tool versions the stub reports.
        """
        super().__init__(SolverRuntime())
        self.reference = reference
        self.surfaces = dict(surfaces or {})
        self.versions = dict(versions or {"aerosandbox": "0.0-stub"})
        self.asked: list[AirplaneGeometry] = []
        self.fin_keys: list[str] = []

    def tool_versions(self) -> dict[str, str]:
        """Return the versions the stub was given."""
        return self.versions

    async def main_wing_reference(self, airplane: AirplaneGeometry) -> MainWingProperties:
        """Return the fixed reference values."""
        self.asked.append(airplane)
        return self.reference or stand_in_main_wing_properties(airplane)

    async def surface_reference(self, airplane: AirplaneGeometry, key: str) -> SurfaceProperties:
        """Return the stand-in planform values of the wing, or the fixed ones given to the stub."""
        self.asked.append(airplane)
        return self.surfaces.get(key) or stand_in_surface_of(airplane, key)

    async def quarter_chord_mac_x(self, airplane: AirplaneGeometry, key: str) -> float:
        """Return the stand-in position of the wing's quarter-chord MAC."""
        self.asked.append(airplane)
        return stand_in_quarter_chord_x((airplane.wings or {})[key])

    async def fin_area(self, airplane: AirplaneGeometry, key: str) -> float:
        """Return the stand-in fin area of the wing (a V-tail's fin share)."""
        self.asked.append(airplane)
        self.fin_keys.append(key)
        return stand_in_fin_area((airplane.wings or {})[key])


def solvers_with(
    atmosphere: AtmosphereAdapter | None = None,
    opti: OptiAdapter | None = None,
    avl: AvlAdapter | None = None,
    geometry: GeometryAdapter | None = None,
) -> Solvers:
    """Solvers with the given adapters; one left out is the real one on a fresh runtime."""
    rules = Rules(shipped_build().model)
    return Solvers(
        atmosphere=atmosphere or AtmosphereAdapter(SolverRuntime()),
        opti=opti or OptiAdapter(SolverRuntime()),
        avl=avl or AvlAdapter(SolverRuntime(), rules),
        geometry=geometry or StubGeometry(),
        rules=rules,
    )


def context_with(
    atmosphere: AtmosphereAdapter,
    origin: str = "t",
    opti: OptiAdapter | None = None,
    geometry: GeometryAdapter | None = None,
) -> Context:
    """A formula context whose ATM (and, if given, OPT and GEO) adapter is the given one."""
    return Context(
        origin=origin, solvers=solvers_with(atmosphere=atmosphere, opti=opti, geometry=geometry)
    )


def close(actual: float | None, expected: float, rel: float) -> bool:
    """Whether ``actual`` equals ``expected`` to the relative tolerance ``rel``."""
    return actual is not None and math.isclose(actual, expected, rel_tol=rel)


def near(actual: float | None, expected: float, tol: float = 1e-9) -> bool:
    """Whether ``actual`` equals ``expected`` to the absolute tolerance ``tol``."""
    return actual is not None and abs(actual - expected) <= tol


def all_near(actual: Sequence[float], expected: Sequence[float], tol: float = 1e-9) -> bool:
    """Whether two sequences agree element by element to the absolute tolerance ``tol``."""
    return len(actual) == len(expected) and all(
        near(a, e, tol) for a, e in zip(actual, expected, strict=True)
    )
