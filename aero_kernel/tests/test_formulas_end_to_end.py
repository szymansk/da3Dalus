"""Slice 1 end to end: weight, ISA density and dynamic pressure through the engine on the shipped
canon model, BRYAN (0.151 kg) and JAGUAR (0.160 kg, approx., maintainer 2026-10-14), against hand-computed values.

Fast tier: the engine seam ``evaluate`` with a stub ATM adapter. ``aero`` tier: the public
``compute()`` with the real adapter (AeroSandbox).

Operating point: altitude 500 m, flight speed 15 m/s; gravity is the canon default (9.80665).

Hand computation (all SI):
- W = m g: BRYAN 0.151 * 9.80665 = 1.48080415 N; JAGUAR 0.160 * 9.80665 = 1.569064 N.
- ISA troposphere (ISO 2533): T = 288.15 - 0.0065 * 500 = 284.9 K;
  p = 101325 * (284.9 / 288.15)^(9.80665 / (287.053 * 0.0065)) = 95460.84 Pa;
  rho = p / (287.053 * 284.9) = 1.167268 kg/m^3.
- q = 1/2 rho V^2 = 0.5 * 1.167268 * 15^2 = 131.3177 Pa (the same for both aircraft).
"""

import importlib.metadata

import pytest
from aero_kernel import compute
from aero_kernel.build import shipped_build
from aero_kernel.cache import cache_key
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory
from aero_kernel.runtime import SolverRuntime
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.solvers.atmosphere import AtmosphereAdapter
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import (
    STUB_SPEED_OF_SOUND,
    STUB_VISCOSITY,
    StubAtmosphere,
    close,
    solvers_with,
)
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

ALTITUDE_M = 500.0
SPEED_MS = 15.0
RHO_HAND = 1.167268
Q_HAND = 131.3177
MU_HAND = 1.773656e-05  # Sutherland: 1.458e-6 T^1.5 / (T + 110.4) at T = 284.9 K
A_HAND = 338.3678  # sqrt(1.4 * 287.05 * 284.9)
FLEET = [("BRYAN", 0.151, 1.48080415), ("JAGUAR", 0.160, 1.569064)]
SLUGS = ("weight", "air-density", "dynamic-pressure", "dynamic-viscosity", "speed-of-sound")


def aircraft_of(name: str, mass_kg: float) -> AircraftInput:
    """An aircraft with a mass, an altitude and a speed; gravity is left to the canon default."""
    return AircraftInput.model_validate(
        {
            "airplane": airplane_document(name),
            "values": {"aircraft-mass": mass_kg, "altitude": ALTITUDE_M, "flight-speed": SPEED_MS},
        }
    )


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


def check(
    result: ComputeResult,
    weight_n: float,
    rho: float,
    q: float,
    rel: float,
    air: tuple[float, float] = (MU_HAND, A_HAND),
) -> None:
    quantities = by_slug(result)
    assert all(r.status is QuantityStatus.OK for r in quantities.values()), result
    assert close(quantities["weight"].value, weight_n, 1e-12)
    assert quantities["weight"].unit == "N"
    assert close(quantities["air-density"].value, rho, rel)
    assert quantities["air-density"].unit == "kg/m^3"
    assert close(quantities["dynamic-pressure"].value, q, rel)
    assert quantities["dynamic-pressure"].unit == "Pa"
    assert close(quantities["dynamic-viscosity"].value, air[0], rel)
    assert quantities["dynamic-viscosity"].unit == "Pa*s"
    assert close(quantities["speed-of-sound"].value, air[1], rel)
    assert quantities["speed-of-sound"].unit == "m/s"
    assert quantities["air-density"].tool == "ATM"
    assert quantities["weight"].tool == "APP"
    assert [d.slug for d in result.provenance.defaults_used] == ["gravity"]
    assert result.provenance.defaults_used[0].value == 9.80665


@pytest.mark.parametrize(("name", "mass_kg", "weight_n"), FLEET)
async def test_the_fleet_through_the_engine_with_a_stub_atmosphere(
    name: str, mass_kg: float, weight_n: float
) -> None:
    stub = StubAtmosphere({ALTITUDE_M: RHO_HAND})
    solvers = solvers_with(atmosphere=stub)
    result = await evaluate(
        shipped_build(), aircraft_of(name, mass_kg), request(*SLUGS), solvers=solvers
    )
    stub_air = (STUB_VISCOSITY, STUB_SPEED_OF_SOUND)  # the stub answers sea-level mu and a
    check(result, weight_n, RHO_HAND, 0.5 * RHO_HAND * SPEED_MS**2, rel=1e-12, air=stub_air)
    assert close(Q_HAND, 0.5 * RHO_HAND * SPEED_MS**2, 1e-6)
    assert stub.asked == [ALTITUDE_M]


async def test_a_missing_altitude_fails_density_and_pressure_but_not_weight() -> None:
    no_altitude = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "values": {"aircraft-mass": 0.151, "flight-speed": 15.0},
        }
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({}))
    result = await evaluate(shipped_build(), no_altitude, request(*SLUGS), solvers=solvers)
    quantities = by_slug(result)
    assert quantities["weight"].status is QuantityStatus.OK
    assert quantities["air-density"].status is QuantityStatus.ERROR
    assert quantities["dynamic-pressure"].status is QuantityStatus.ERROR


async def test_everything_else_is_still_not_implemented() -> None:
    solvers = solvers_with(atmosphere=StubAtmosphere({}))
    result = await evaluate(
        shipped_build(), aircraft_of("BRYAN", 0.151), request("dive-speed"), solvers=solvers
    )
    (only,) = result.quantities
    assert only.status is QuantityStatus.ERROR
    assert only.error is not None
    assert only.error.category.value == "not_implemented"


@pytest.mark.aero
@pytest.mark.parametrize(("name", "mass_kg", "weight_n"), FLEET)
async def test_the_fleet_through_the_public_compute_with_the_real_atmosphere(
    name: str, mass_kg: float, weight_n: float
) -> None:
    """The real adapter reproduces the hand ISA to 0.05 % (AeroSandbox's documented 0.02 %)."""
    result = await compute(aircraft_of(name, mass_kg), request(*SLUGS))
    check(result, weight_n, RHO_HAND, Q_HAND, rel=5e-4)


async def test_the_provenance_names_the_tool_versions_of_the_tools_that_ran() -> None:
    solvers = solvers_with(
        atmosphere=StubAtmosphere({ALTITUDE_M: RHO_HAND}, {"aerosandbox": "7.7"})
    )
    for slugs in (("air-density",), ("dynamic-pressure",), SLUGS):
        result = await evaluate(
            shipped_build(), aircraft_of("BRYAN", 0.151), request(*slugs), solvers=solvers
        )
        assert result.provenance.tool_versions == {"aerosandbox": "7.7"}


async def test_a_request_of_pure_formulas_reports_no_tool_version() -> None:
    solvers = solvers_with(atmosphere=StubAtmosphere({}, {"aerosandbox": "7.7"}))
    result = await evaluate(
        shipped_build(), aircraft_of("BRYAN", 0.151), request("weight"), solvers=solvers
    )
    assert result.provenance.tool_versions == {}


async def test_a_formula_that_was_never_called_reports_no_tool_version() -> None:
    # altitude has a default (0 m), so the density formula would run; the caller supplies the
    # density itself and the atmosphere solver is never called
    given_density = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "values": {"aircraft-mass": 0.151, "flight-speed": 15.0, "air-density": 1.2},
        }
    )
    solvers = solvers_with(atmosphere=StubAtmosphere({}, {"aerosandbox": "7.7"}))
    result = await evaluate(
        shipped_build(), given_density, request("dynamic-pressure"), solvers=solvers
    )
    assert result.provenance.tool_versions == {}


async def test_the_cache_key_of_the_density_node_follows_the_tool_version() -> None:
    def key(version: str) -> str:
        solvers = solvers_with(atmosphere=StubAtmosphere({}, {"aerosandbox": version}))
        return cache_key(
            formula="calc:air-density-isa",
            application="default",
            world=None,
            inputs={"h": ALTITUDE_M},
            build_digest="sha256:aa",
            tool_versions=solvers.tool_versions_of("ATM"),
            solver_settings=solvers.settings_of("ATM"),
        )

    first, again, other = key("4.2.9"), key("4.2.9"), key("4.3.0")
    assert first == again
    assert first != other


@pytest.mark.aero
async def test_the_real_provenance_names_the_installed_aerosandbox() -> None:
    result = await compute(aircraft_of("BRYAN", 0.151), request(*SLUGS))
    assert result.provenance.tool_versions == {
        "aerosandbox": importlib.metadata.version("aerosandbox")
    }


async def test_q10_a_missing_aerosandbox_fails_density_and_pressure_as_tool_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter's own availability check says aerosandbox is missing (Q10)."""
    adapter = AtmosphereAdapter(SolverRuntime())
    monkeypatch.setattr(adapter, "_missing", lambda: ["aerosandbox"])
    result = await evaluate(
        shipped_build(),
        aircraft_of("BRYAN", 0.151),
        request("air-density", "dynamic-pressure"),
        solvers=solvers_with(atmosphere=adapter),
    )
    quantities = by_slug(result)
    density = quantities["air-density"].error
    assert density is not None
    assert density.category is ErrorCategory.TOOL_UNAVAILABLE
    pressure = quantities["dynamic-pressure"].error
    assert pressure is not None
    assert pressure.category is ErrorCategory.UPSTREAM_FAILED
    assert pressure.detail["causes"] == [{"quantity": "air-density", "code": "tool_unavailable"}]
    # installed but not importable: the tool could not run, so it reports no version (ch. 8.4)
    assert result.provenance.tool_versions == {}


async def test_q10_a_distribution_that_is_not_installed_reports_no_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        AtmosphereAdapter, "requirements", {"no-such-distribution": "no_such_module_xyz"}
    )
    result = await evaluate(
        shipped_build(),
        aircraft_of("BRYAN", 0.151),
        request("dynamic-pressure"),
        solvers=solvers_with(atmosphere=AtmosphereAdapter(SolverRuntime())),
    )
    (only,) = result.quantities
    assert only.error is not None
    assert only.error.category is ErrorCategory.UPSTREAM_FAILED
    assert result.provenance.tool_versions == {}
